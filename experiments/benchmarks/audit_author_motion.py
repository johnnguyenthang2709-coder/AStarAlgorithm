"""Read-only replay and independent geometry audit of two upstream source runs.

Only Python methods in this process are temporarily wrapped for observation.
The pinned authors' checkout and earlier benchmark artifacts are never written.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

os.environ["MPLBACKEND"] = "Agg"
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as PolygonPatch
from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
OUT = HERE / "author-motion-audit"
PIN = "8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8"
CASES = (("_map_deadend.csv", (70, 90)), ("_map_bugtrap.csv", (160, 80)))
EPS = 1e-8


def xy(point):
    return [float(point[0]), float(point[1])]


def parse_map(path):
    groups, vertices = [], []
    with path.open(newline="", encoding="utf-8") as stream:
        for line_number, row in enumerate(csv.reader(stream), 1):
            if row and row[0].lower() == "x":
                if vertices:
                    groups.append(vertices)
                vertices = []
            elif len(row) == 2:
                vertices.append({"row": line_number, "xy": [float(row[0]), float(row[1])]})
    if vertices:
        groups.append(vertices)
    return groups


def point_in_polygon_strict(point, vertices):
    """Independent even/odd ray cast, returning False on polygon boundary."""
    x, y = point
    inside = False
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        x1, y1 = a
        x2, y2 = b
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-10 and min(x1, x2)-EPS <= x <= max(x1, x2)+EPS and min(y1, y2)-EPS <= y <= max(y1, y2)+EPS:
            return False
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y-y1) * (x2-x1) / (y2-y1)
            if x_cross > x:
                inside = not inside
    return inside


def pure_interior_length(start, end, vertices):
    """Split at every polygon-edge intersection and test interval midpoints."""
    x0, y0 = start
    dx, dy = end[0]-x0, end[1]-y0
    length = math.hypot(dx, dy)
    if length < EPS:
        return 0.0
    parameters = [0.0, 1.0]
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        ex, ey = b[0]-a[0], b[1]-a[1]
        denominator = dx*ey - dy*ex
        if abs(denominator) < 1e-12:
            continue
        ax, ay = a[0]-x0, a[1]-y0
        t = (ax*ey-ay*ex)/denominator
        u = (ax*dy-ay*dx)/denominator
        if -EPS <= t <= 1+EPS and -EPS <= u <= 1+EPS:
            parameters.append(max(0.0, min(1.0, t)))
    parameters.sort()
    unique = []
    for value in parameters:
        if not unique or value-unique[-1] > 1e-9:
            unique.append(value)
    total = 0.0
    for a, b in zip(unique, unique[1:]):
        mid = (a+b)/2
        if point_in_polygon_strict((x0+mid*dx, y0+mid*dy), vertices):
            total += (b-a)*length
    return total


def boundary_crossings(line, source_vertices):
    values = []
    for a, b in zip(source_vertices, source_vertices[1:] + source_vertices[:1]):
        intersection = line.intersection(LineString((a["xy"], b["xy"])))
        if intersection.is_empty:
            continue
        if intersection.geom_type == "Point":
            values.append({"at": [intersection.x, intersection.y],
                           "csv_edge_rows": [a["row"], b["row"]],
                           "csv_edge_endpoints": [a["xy"], b["xy"]]})
    return values


def replay(source, filename, goal):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    import Robot_run
    from Robot_base import Robot_base
    from Robot_class import Robot
    from Obstacles import Obstacles
    from Robot_sight_lib import inside_visited_sights

    original_update = Robot.update_coordinate
    original_expand = Robot.expand_visited_path
    original_scan = Robot_run.scan_around
    updates, decisions, observations = [], [], []

    def update(self, coords):
        before = xy(self.coordinate)
        target = xy(coords)
        original_update(self, coords)
        updates.append({"iteration": len(updates)+1, "before": before, "after": xy(self.coordinate),
                        "source_next_coordinate": target})

    def expand(self, path):
        original_expand(self, path)
        visibility_checks = []
        for a, b in zip(path, path[1:]):
            for fraction in (.25, .5, .75):
                sample = (float(a[0])+(float(b[0])-float(a[0]))*fraction,
                          float(a[1])+(float(b[1])-float(a[1]))*fraction)
                visibility_checks.append({"point": list(sample),
                                          "source_inside_visited_sights": bool(
                                              inside_visited_sights(sample, self.vision_range,
                                                                    self.visited_sights))})
        decisions.append({"iteration": len(decisions)+1, "coordinate": xy(self.coordinate),
                          "selected_next_point": xy(self.next_point) if self.next_point is not None else None,
                          "skeleton_path": [xy(p) for p in self.skeleton_path],
                          "asp_path": [xy(p) for p in path],
                          "saw_goal": bool(self.saw_goal), "reach_goal": bool(self.reach_goal),
                          "no_way_to_goal": bool(self.no_way_to_goal),
                          "asp_interior_visibility_samples": visibility_checks,
                          "logged_cost_after": float(self.cost)})

    def scan(robot, obstacles, target):
        closed, opened = original_scan(robot, obstacles, target)
        observations.append({"iteration": len(observations)+1, "coordinate": xy(robot.coordinate),
                             "closed_sights": len(closed), "open_sights": len(opened),
                             "configuration_space_enabled": bool(obstacles.enable_config_space)})
        return closed, opened

    Robot.update_coordinate = update
    Robot.expand_visited_path = expand
    Robot_run.scan_around = scan
    previous_dir = Path.cwd()
    try:
        os.chdir(source)  # Original code opens its map by relative name.
        robot = Robot_run.robot_main(start=(0, 0), goal=goal, map_name=filename,
                                     num_iter=60, robot_vision=20, robot_radius=0.5,
                                     open_points_type=Robot_base.Open_points_type.Open_Arcs,
                                     picking_strategy=Robot_base.Picking_strategy.neighbor_first,
                                     experiment=True, save_image=False, save_log=False)
        assert robot is not None
        original_map = Obstacles()
        original_map.read_csv(filename)
        original_map.line_segments()
    finally:
        os.chdir(previous_dir)
        Robot.update_coordinate = original_update
        Robot.expand_visited_path = original_expand
        Robot_run.scan_around = original_scan
    assert len(updates) == len(decisions) == len(observations)
    for i in range(len(updates)-1):
        assert math.dist(decisions[i]["coordinate"], updates[i]["after"]) < 1e-8
        assert math.dist(decisions[i]["selected_next_point"], updates[i+1]["after"]) < 1e-8
    return robot, original_map, updates, decisions, observations


def figures(filename, goal, groups, updates, decisions, collisions):
    stem = filename.removesuffix(".csv").removeprefix("_map_")
    polygons = [Polygon([v["xy"] for v in group]) for group in groups]
    positions = [u["after"] for u in updates]
    legend = [Patch(facecolor="#bfc5c9", edgecolor="#353a3e", label="Ground-truth obstacle"),
              Line2D([0], [0], color="#137caa", lw=1.5, label="Source coordinate transitions"),
              Line2D([0], [0], color="#2d9859", lw=1.2, label="Computed ASP polylines"),
              Line2D([0], [0], color="#d32626", lw=2.5, label="Interior-crossing transition"),
              Patch(facecolor="#d9a328", edgecolor="none", alpha=.4,
                    label="Radius 0.5 swept footprint")]

    def base(ax):
        for polygon in polygons:
            ax.add_patch(PolygonPatch(list(polygon.exterior.coords), facecolor="#bfc5c9",
                                      edgecolor="#353a3e", lw=.7, alpha=.75, zorder=1))
        for d in decisions:
            path = d["asp_path"]
            if len(path) > 1:
                ax.plot([p[0] for p in path], [p[1] for p in path], color="#2d9859",
                        lw=.8, alpha=.35, zorder=2)
        ax.plot([p[0] for p in positions], [p[1] for p in positions], color="#137caa",
                lw=1.3, marker=".", markersize=3, alpha=.85, zorder=3)
        ax.scatter([0], [0], marker="o", s=55, color="#2551a4", zorder=7)
        ax.scatter([goal[0]], [goal[1]], marker="*", s=130, color="#de9719", zorder=7)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x (source world units)")
        ax.set_ylabel("y (source world units)")

    fig, ax = plt.subplots(figsize=(8, 7))
    base(ax)
    annotated_moves = set()
    for row in collisions:
        a, b = row["from"], row["to"]
        swept = LineString((a, b)).buffer(.5)
        ax.add_patch(PolygonPatch(list(swept.exterior.coords), facecolor="#d9a328",
                                  edgecolor="none", alpha=.2, zorder=4))
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#d32626", lw=2.5, zorder=5)
        midpoint = ((a[0]+b[0])/2, (a[1]+b[1])/2)
        move_id = row["move_index_0based"]
        if move_id not in annotated_moves:
            same = [r["collision_id"] for r in collisions if r["move_index_0based"] == move_id]
            ax.text(midpoint[0], midpoint[1], "/".join(same), fontsize=9,
                    color="#a31616", weight="bold", zorder=8)
            annotated_moves.add(move_id)
    ax.set_title(f"{stem}: ground-truth geometry and source transitions\n"
                 "Green ASP is computed/logged; red transitions cross obstacles")
    ax.legend(handles=legend, loc="best", frameon=True, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / f"{stem}-full.png", dpi=180)
    plt.close(fig)

    for row in collisions:
        fig, ax = plt.subplots(figsize=(7, 6))
        base(ax)
        a, b = row["from"], row["to"]
        swept = LineString((a, b)).buffer(.5)
        ax.add_patch(PolygonPatch(list(swept.exterior.coords), facecolor="#d9a328",
                                  edgecolor="none", alpha=.3, zorder=4))
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#d32626", lw=2.8, zorder=6)
        path = decisions[row["move_index_0based"]]["asp_path"]
        if len(path) > 1:
            ax.plot([p[0] for p in path], [p[1] for p in path], color="#08793f",
                    lw=1.5, zorder=5)
        crossing = row["boundary_crossings"]
        if crossing:
            ax.scatter([p["at"][0] for p in crossing], [p["at"][1] for p in crossing],
                       s=28, marker="x", color="#931b1b", zorder=8)
        interior = LineString((a, b)).intersection(polygons[row["polygon_index_1based"]-1])
        bounds = interior.bounds if not interior.is_empty else LineString((a, b)).bounds
        xmin, ymin, xmax, ymax = bounds
        margin = max(2.0, min(8.0, max(xmax-xmin, ymax-ymin)*.18))
        ax.set_xlim(xmin-margin, xmax+margin)
        ax.set_ylim(ymin-margin, ymax+margin)
        ax.set_title(f"{stem} {row['collision_id']}: source move {row['move_index_0based']}\n"
                     f"Polygon {row['polygon_index_1based']}; interior length {row['independent_interior_length']:.2f}")
        ax.legend(handles=legend, loc="best", frameon=True, fontsize=7)
        fig.tight_layout()
        fig.savefig(OUT / f"{stem}-{row['collision_id']}-zoom.png", dpi=180)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-dir", type=Path,
                        default=HERE.parents[2] / "AStarAlgorithm-authors-benchmark")
    args = parser.parse_args()
    source = args.authors_dir.resolve()
    sha = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    porcelain = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    if sha != PIN or porcelain:
        raise ValueError(f"authors' checkout must be clean at {PIN}; got {sha}, status={porcelain}")
    OUT.mkdir(exist_ok=True)
    prior = json.loads((HERE / "author-reproduction-raw.json").read_text(encoding="utf-8"))["runs"]
    manifest = json.loads((HERE / "benchmark-manifest.json").read_text(encoding="utf-8"))
    expected_hashes = {w["file"]: w["sha256"] for w in manifest["robot"]["worlds"]}
    all_collisions, decision_rows, summaries = [], [], {}
    raw = {"upstream_commit": sha, "method": "in-process read-only method wrappers", "cases": {}}
    for filename, goal in CASES:
        map_path = source / filename
        digest = hashlib.sha256(map_path.read_bytes()).hexdigest()
        assert digest == expected_hashes[filename]
        groups = parse_map(map_path)
        polygons = [Polygon([v["xy"] for v in group]) for group in groups]
        assert polygons and all(p.is_valid and p.area > 0 for p in polygons)
        robot, original_map, updates, decisions, observations = replay(source, filename, goal)
        assert len(original_map.obstacles) == len(groups)
        for original, group in zip(original_map.obstacles, groups):
            assert original[:-1] == [tuple(v["xy"]) for v in group]
        baseline = prior[filename]
        assert len(updates) == len(baseline["executed_positions"])
        assert len(decisions) == len(baseline["planned_asp_paths"])
        max_position_delta = max(math.dist(u["after"], p) for u, p in zip(updates, baseline["executed_positions"]))
        max_asp_delta = max((math.dist(a, b) for d, old in zip(decisions, baseline["planned_asp_paths"])
                             for a, b in zip(d["asp_path"], old)), default=0.0)
        assert all(len(d["asp_path"]) == len(old) for d, old in zip(decisions, baseline["planned_asp_paths"]))
        assert max_position_delta < 1e-7 and max_asp_delta < 1e-7
        case_collisions, planned_bad, planned_clearance, planned_segments = [], [], [], 0
        planned_boundary_touches, planned_min_clearance = set(), math.inf
        source_uncovered, geometric_uncovered, visibility_samples = [], [], 0
        path_endpoint_errors = []
        for i, decision in enumerate(decisions):
            path = decision["asp_path"]
            if path:
                if math.dist(path[0], decision["coordinate"]) > 1e-7:
                    path_endpoint_errors.append((i, "start"))
                if decision["selected_next_point"] is not None and math.dist(path[-1], decision["selected_next_point"]) > 1e-7:
                    path_endpoint_errors.append((i, "target"))
            for sample in decision["asp_interior_visibility_samples"]:
                visibility_samples += 1
                point = sample["point"]
                if not sample["source_inside_visited_sights"]:
                    source_uncovered.append({"decision": i, "point": point})
                visible_from_station = any(
                    math.dist(point, station["after"]) < 20-1e-7 and
                    not any(LineString((point, station["after"])).relate_pattern(polygon, "T********")
                            for polygon in polygons)
                    for station in updates[:i+1])
                if not visible_from_station:
                    geometric_uncovered.append({"decision": i, "point": point})
            for j, (a, b) in enumerate(zip(path, path[1:])):
                line = LineString((a, b))
                planned_segments += 1
                for k, (polygon, group) in enumerate(zip(polygons, groups), 1):
                    shapely_hit = line.relate_pattern(polygon, "T********")
                    pure_length = pure_interior_length(a, b, [v["xy"] for v in group])
                    if shapely_hit or pure_length > EPS:
                        planned_bad.append({"decision": i, "segment": j, "polygon": k,
                                            "shapely_interior": shapely_hit,
                                            "independent_interior_length": pure_length})
                    if line.distance(polygon) < .5-1e-7:
                        planned_clearance.append((i, j, k))
                    planned_min_clearance = min(planned_min_clearance, line.distance(polygon))
                    if line.intersects(polygon) and not shapely_hit:
                        planned_boundary_touches.add((i, j))
        for i, (before, after) in enumerate(zip(updates, updates[1:])):
            a, b = before["after"], after["after"]
            line = LineString((a, b))
            for k, (polygon, group) in enumerate(zip(polygons, groups), 1):
                shapely_hit = line.relate_pattern(polygon, "T********")
                pure_length = pure_interior_length(a, b, [v["xy"] for v in group])
                if shapely_hit or pure_length > EPS:
                    assert shapely_hit and pure_length > EPS
                    case_collisions.append({"collision_id": f"C{len(case_collisions)+1}",
                        "source_map": filename, "map_sha256": digest,
                        "move_index_0based": i, "source_iteration_from": i+1,
                        "source_iteration_to": i+2, "from": a, "to": b,
                        "polygon_index_1based": k,
                        "polygon_csv_rows": [group[0]["row"], group[-1]["row"]],
                        "shapely_de9im": line.relate(polygon),
                        "shapely_interior_crossing": shapely_hit,
                        "independent_interior_length": pure_length,
                        "minimum_polygon_distance": line.distance(polygon),
                        "boundary_crossings": boundary_crossings(line, group),
                        "original_boundary_collision_function": original_map.check_linesegment_collision((a, b)),
                        "corresponding_asp_segments": max(0, len(decisions[i]["asp_path"])-1),
                        "corresponding_asp_interior_collisions": sum(
                            item["decision"] == i for item in planned_bad)})
        observed_crossing_moves = sorted({r["move_index_0based"] for r in case_collisions})
        assert observed_crossing_moves == baseline["interior_collision_segment_indices"]
        actual_length = sum(math.dist(a["after"], b["after"]) for a, b in zip(updates, updates[1:]))
        planned_length = sum(math.dist(a, b) for d in decisions for a, b in zip(d["asp_path"], d["asp_path"][1:]))
        summaries[filename] = {"map_sha256": digest, "polygons": len(polygons),
            "polygon_vertices": [len(group) for group in groups],
            "all_polygons_valid": True, "source_goal_reached": bool(robot.reach_goal),
            "source_no_way": bool(robot.no_way_to_goal), "iterations": len(updates),
            "executed_nonzero_transitions": len(updates)-1,
            "source_next_coordinate_equals_selected_next_point": all(
                math.dist(d["selected_next_point"], u["after"]) < 1e-8
                for d, u in zip(decisions, updates[1:])),
            "executed_distance": actual_length, "planned_asp_length": planned_length,
            "crossing_transitions": len({r["move_index_0based"] for r in case_collisions}),
            "collision_polygon_records": len(case_collisions),
            "planned_asp_segments": planned_segments,
            "planned_asp_interior_collision_records": len(planned_bad),
            "planned_asp_radius_0_5_violation_records": len(planned_clearance),
            "planned_asp_boundary_touch_segments": len(planned_boundary_touches),
            "planned_asp_minimum_clearance": planned_min_clearance,
            "start_polygon_clearance": min(Point((0, 0)).distance(p) for p in polygons),
            "goal_polygon_clearance": min(Point(goal).distance(p) for p in polygons),
            "asp_interior_visibility_sample_count": visibility_samples,
            "source_visited_sights_uncovered_samples": len(source_uncovered),
            "geometric_line_of_sight_uncovered_samples": len(geometric_uncovered),
            "path_endpoint_errors": path_endpoint_errors,
            "maximum_replay_position_delta": max_position_delta,
            "maximum_replay_asp_vertex_delta": max_asp_delta}
        for i, decision in enumerate(decisions):
            move = updates[i+1]["after"] if i+1 < len(updates) else None
            decision_rows.append({"map": filename, "decision_index_0based": i,
                "source_iteration": i+1, "coordinate": json.dumps(decision["coordinate"]),
                "selected_next_point": json.dumps(decision["selected_next_point"]),
                "next_recorded_coordinate": json.dumps(move),
                "skeleton_vertices": len(decision["skeleton_path"]),
                "asp_vertices": len(decision["asp_path"]),
                "asp_length": sum(math.dist(a, b) for a, b in zip(decision["asp_path"], decision["asp_path"][1:])),
                "closed_sights": observations[i]["closed_sights"],
                "open_sights": observations[i]["open_sights"],
                "saw_goal": decision["saw_goal"], "reach_goal": decision["reach_goal"],
                "move_crosses_interior": any(r["move_index_0based"] == i for r in case_collisions),
                "asp_crosses_interior": any(r["decision"] == i for r in planned_bad)})
        raw["cases"][filename] = {"summary": summaries[filename], "updates": updates,
            "decisions": decisions, "observations": observations,
            "planned_interior_collisions": planned_bad,
            "planned_clearance_violations": planned_clearance,
            "source_visited_sights_uncovered_examples": source_uncovered[:20],
            "geometric_line_of_sight_uncovered_examples": geometric_uncovered[:20]}
        all_collisions.extend(case_collisions)
        figures(filename, goal, groups, updates, decisions, case_collisions)
        print(filename, json.dumps(summaries[filename]), flush=True)
    with (OUT / "decision-trace.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=decision_rows[0].keys())
        writer.writeheader()
        writer.writerows(decision_rows)
    (OUT / "decision-trace.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    (OUT / "collision-details.json").write_text(json.dumps(all_collisions, indent=2) + "\n", encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    print(f"Audit artifacts: {OUT}")


if __name__ == "__main__":
    main()
