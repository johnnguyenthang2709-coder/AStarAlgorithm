"""Offline paired validation and figures; ground-truth maps enter only here.

Run after the separate unchanged ASP and C++ A* planning commands. Nothing in
this file feeds the full obstacle polygons back to either planner.
"""

import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path
import statistics
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch
from shapely.geometry import LineString, Polygon

from robot_local_geometry import point_visible, segment_certified, cross, subtract


HERE = Path(__file__).resolve().parent
OUT = HERE / "robot-local-benchmark"


def load_map(path):
    groups, vertices = [], []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if row and row[0].lower() == "x":
                if vertices:
                    groups.append(vertices)
                vertices = []
            elif len(row) == 2:
                vertices.append((float(row[0]), float(row[1])))
    if vertices:
        groups.append(vertices)
    polygons = [Polygon(group) for group in groups]
    assert polygons and all(poly.is_valid and poly.area > 0 for poly in polygons)
    return polygons


def length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def turns(path):
    headings = [math.atan2(b[1] - a[1], b[0] - a[0])
                for a, b in zip(path, path[1:]) if math.dist(a, b) > 1e-9]
    angles = [abs(math.atan2(math.sin(b - a), math.cos(b - a)))
              for a, b in zip(headings, headings[1:])]
    return sum(angle > 1e-6 for angle in angles), sum(angle > math.radians(15) for angle in angles)


def path_metrics(path, snap, polygons):
    if len(path) < 2:
        return {"found": False, "planned_length": None, "turns": None,
                "turns_over_15deg": None, "interior_collision_segments": None,
                "boundary_contact_records": None, "minimum_obstacle_clearance": None,
                "observed_space_certified": False, "endpoint_error": None,
                "interior_only_valid": False, "strict_boundary_valid": False,
                "radius_0_5_clearance_valid": False}
    segments = [LineString((a, b)) for a, b in zip(path, path[1:])]
    interior = sum(line.relate_pattern(poly, "T********") for line in segments for poly in polygons)
    boundary = sum(line.intersects(poly) and not line.relate_pattern(poly, "T********")
                   for line in segments for poly in polygons)
    clearance = min((line.distance(poly) for line in segments for poly in polygons), default=math.inf)
    certified = all(segment_certified(a, b, snap["sights"], snap["sensor_radius"])[0]
                    for a, b in zip(path, path[1:]))
    endpoint_error = max(math.dist(path[0], snap["start"]), math.dist(path[-1], snap["target"]))
    count, significant = turns(path)
    return {"found": True, "planned_length": length(path), "turns": count, "turns_over_15deg": significant,
            "interior_collision_segments": interior, "boundary_contact_records": boundary,
            "minimum_obstacle_clearance": clearance, "observed_space_certified": certified,
            "endpoint_error": endpoint_error,
            "interior_only_valid": interior == 0 and certified and endpoint_error < 1e-7,
            "strict_boundary_valid": interior == 0 and boundary == 0 and certified and endpoint_error < 1e-7,
            "radius_0_5_clearance_valid": clearance >= .5 - 1e-7}


def source_visibility(snap, point):
    # The imported function reads only frozen sight records; original source is unchanged.
    from Robot_sight_lib import inside_local_sights
    return any(inside_local_sights(point, sight["center"], snap["sensor_radius"],
                                   sight["closed_sights"]) for sight in snap["sights"])


def visibility_validation(snapshots, plans):
    rng = random.Random(5110)
    samples = mismatches = graph_link_samples = graph_link_mismatches = 0
    for snap in snapshots:
        centers = [sight["center"] for sight in snap["sights"]] + [snap["target"]]
        xs, ys = [point[0] for point in centers], [point[1] for point in centers]
        for _ in range(500):
            point = (rng.uniform(min(xs) - 20, max(xs) + 20),
                     rng.uniform(min(ys) - 20, max(ys) + 20))
            ours = any(point_visible(point, sight, snap["sensor_radius"])
                       for sight in snap["sights"])
            original = source_visibility(snap, point)
            samples += 1
            mismatches += ours != original
        plan = plans.get(snap["snapshot_id"])
        if plan:
            for i, j in plan["graph_links"]:
                a, b = plan["graph_points"][i], plan["graph_points"][j]
                assert segment_certified(a, b, snap["sights"], snap["sensor_radius"])[0]
                for step in range(1, 100):
                    t = step / 100
                    point = (a[0] * (1-t) + b[0] * t, a[1] * (1-t) + b[1] * t)
                    graph_link_samples += 1
                    graph_link_mismatches += not source_visibility(snap, point)
    return {"point_samples": samples, "source_derived_membership_mismatches": mismatches,
            "certified_graph_link_samples": graph_link_samples,
            "source_uncovered_graph_link_samples": graph_link_mismatches}


def sight_outline(sight, radius, rays=480):
    center = sight["center"]
    points = []
    for i in range(rays):
        angle = 2 * math.pi * i / rays
        direction = (math.cos(angle), math.sin(angle))
        nearest = radius
        for closed in sight["closed_sights"]:
            a, b = closed[:2]
            edge = subtract(b, a)
            denominator = cross(direction, edge)
            if abs(denominator) < 1e-12:
                continue
            offset = subtract(a, center)
            distance = cross(offset, edge) / denominator
            fraction = cross(offset, direction) / denominator
            if 0 <= distance <= nearest and -1e-9 <= fraction <= 1 + 1e-9:
                nearest = distance
        points.append((center[0] + nearest * direction[0],
                       center[1] + nearest * direction[1]))
    return points


def map_figure(snap, asp, astar, polygons, filename, ground_truth):
    fig, ax = plt.subplots(figsize=(9, 7.2))
    ax.set_facecolor("#f4f1e8")
    if ground_truth:
        for poly in polygons:
            ax.add_patch(PolygonPatch(list(poly.exterior.coords), facecolor="#b9bfc1",
                                      edgecolor="#465157", linewidth=.8, zorder=2))
    else:
        for sight in snap["sights"]:
            ax.add_patch(PolygonPatch(sight_outline(sight, snap["sensor_radius"]),
                                      facecolor="#75bdc5", edgecolor="none", alpha=.11, zorder=1))
        for sight in snap["sights"]:
            for closed in sight["closed_sights"]:
                ax.plot([closed[0][0], closed[1][0]], [closed[0][1], closed[1][1]],
                        color="#243f49", linewidth=1.2, zorder=3)
    ax.plot([p[0] for p in asp], [p[1] for p in asp], color="#c75b2f", linewidth=2,
            label="Authors' ASP", zorder=5)
    ax.plot([p[0] for p in astar], [p[1] for p in astar], color="#17699e", linewidth=2,
            label="Our C++ visibility A*", zorder=6)
    ax.scatter([snap["start"][0]], [snap["start"][1]], marker="o", s=55,
               color="#103947", label="Common start", zorder=7)
    ax.scatter([snap["target"][0]], [snap["target"][1]], marker="*", s=145,
               color="#e2a126", edgecolor="#50452c", linewidth=.4, label="Common target", zorder=7)
    ax.set_aspect("equal", adjustable="box")
    all_points = asp + astar
    x = [p[0] for p in all_points]
    y = [p[1] for p in all_points]
    ax.set_xlim(min(x) - 12, max(x) + 12)
    ax.set_ylim(min(y) - 12, max(y) + 12)
    ax.set_xlabel("World x")
    ax.set_ylabel("World y")
    kind = "Ground-truth validation only" if ground_truth else "Frozen observed sights only"
    ax.set_title(f"{snap['snapshot_id']} — {kind}")
    ax.legend(loc="best", fontsize=8, framealpha=.95)
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=180)
    plt.close(fig)


def paired_figures(rows):
    labels = [row["snapshot_id"].replace("_map_", "") for row in rows]
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for i, row in enumerate(rows):
        ax.plot([row["asp_length"], row["astar_length"]], [i, i], color="#adb8bb", lw=2)
    ax.scatter([row["asp_length"] for row in rows], y, color="#c75b2f", label="Authors' ASP", zorder=3)
    ax.scatter([row["astar_length"] for row in rows], y, color="#17699e", marker="s",
               label="Our A*", zorder=3)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Planned point-robot path length (world units)")
    ax.set_title("Paired local paths at identical frozen decisions")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "robot-local-paired-lengths.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.7), sharey=True)
    for ax, threshold, title in zip(axes, ("turns", "turns_over_15deg"),
                                    ("All nonzero heading changes", "Changes over 15°")):
        for i, row in enumerate(rows):
            ax.plot([row[f"asp_{threshold}"], row[f"astar_{threshold}"]], [i, i],
                    color="#adb8bb", lw=2)
        ax.scatter([row[f"asp_{threshold}"] for row in rows], y, color="#c75b2f")
        ax.scatter([row[f"astar_{threshold}"] for row in rows], y, color="#17699e", marker="s")
        ax.set_title(title)
        ax.set_xlabel("Turn count")
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT / "robot-local-paired-turns.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.scatter([row["asp_core_median_ms"] for row in rows], y, color="#c75b2f",
               label="ASP Python core")
    ax.scatter([row["astar_core_median_ms"] for row in rows], y, color="#17699e",
               marker="s", label="A* C++ call")
    ax.scatter([row["astar_build_median_ms"] for row in rows], y, color="#6e8c62",
               marker="^", label="A* observed-link build")
    ax.set_xscale("log")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Median wall time (ms; log scale, separate runtimes)")
    ax.set_title("Planning and observed-link construction")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "robot-local-paired-timing.png", dpi=180)
    plt.close(fig)


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def timing_distributions(snapshots, authors, astar):
    rows = []
    cases = [snap for snap in snapshots if snap["snapshot_id"] in authors]
    series = (
        ("authors_asp_python_core", "Authors' ASP core", "#c75b2f",
         lambda sid: authors[sid]["core_call_samples_ms"]),
        ("our_astar_link_build", "A* sight-link build", "#6e8c62",
         lambda sid: astar[sid]["build_samples_ms"]),
        ("our_astar_cpp_binding", "A* C++ binding call", "#17699e",
         lambda sid: astar[sid]["core_call_samples_ms"]),
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2), sharey=True)
    labels = [snap["snapshot_id"].replace("_map_", "") for snap in cases]
    for ax, (method, title, color, get_samples) in zip(axes, series):
        data = []
        for snap in cases:
            sid = snap["snapshot_id"]
            values = get_samples(sid)
            assert len(values) == 31 and all(value > 0 for value in values)
            data.append(values)
            rows.append({"snapshot_id": sid, "method": method, "samples": len(values),
                         "minimum_ms": min(values), "p25_ms": percentile(values, .25),
                         "median_ms": percentile(values, .5), "p75_ms": percentile(values, .75),
                         "maximum_ms": max(values)})
        boxes = ax.boxplot(data, vert=False, positions=range(len(data)), patch_artist=True,
                           showfliers=True, widths=.55)
        for box in boxes["boxes"]:
            box.set_facecolor(color)
            box.set_alpha(.55)
        ax.set_xscale("log")
        ax.set_yticks(range(len(labels)), labels)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel("Wall time (ms, log scale)")
        ax.grid(axis="x", color="#e5e8e8", linewidth=.5)
    fig.suptitle("31 warmed local-planning measurements per snapshot")
    fig.tight_layout()
    fig.savefig(OUT / "robot-local-timing-distributions.png", dpi=180)
    plt.close(fig)
    with (OUT / "robot-local-timing-distributions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-dir", type=Path,
                        default=HERE.parents[2] / "AStarAlgorithm-authors-benchmark")
    parser.add_argument("--dataset-dir", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.dataset_dir.resolve()
    source = args.authors_dir.resolve()
    manifest = json.loads((OUT / "robot-local-benchmark-manifest.json").read_text())
    content = (OUT / manifest["snapshot_file"]).read_bytes()
    assert hashlib.sha256(content).hexdigest() == manifest["snapshot_sha256"]
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == manifest["authors_commit"]
    assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    sys.path.insert(0, str(source))
    snapshots = json.loads(content)["snapshots"]
    authors = {row["snapshot_id"]: row for row in json.loads((OUT / "authors-asp-timing.json").read_text())}
    astar = {row["snapshot_id"]: row for row in json.loads((OUT / "astar-plans.json").read_text())}
    eligible = set(manifest["eligible_ids"])
    assert len(snapshots) == manifest["captured_decisions"]
    assert {s["snapshot_id"] for s in snapshots if len(s["skeleton_path"]) > 2} == eligible
    assert set(authors) == set(astar) == eligible
    visibility = visibility_validation(snapshots, astar)
    assert visibility["source_derived_membership_mismatches"] == 0
    assert visibility["source_uncovered_graph_link_samples"] == 0
    asp_segments = sum(max(0, len(snap["asp_path"]) - 1) for snap in snapshots)
    uncertified_asp_segments = sum(
        not segment_certified(a, b, snap["sights"], snap["sensor_radius"])[0]
        for snap in snapshots for a, b in zip(snap["asp_path"], snap["asp_path"][1:]))
    assert uncertified_asp_segments == 0
    if "map_hashes" in manifest:
        expected_hashes = manifest["map_hashes"]
    else:
        map_hashes = json.loads((HERE / "benchmark-manifest.json").read_text())["robot"]["worlds"]
        expected_hashes = {item["file"]: item["sha256"] for item in map_hashes}
    map_polygons = {}
    for filename in {snap["source_map"] for snap in snapshots}:
        path = source / filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hashes[filename]
        map_polygons[filename] = load_map(path)
    graph_edges_offline = graph_edge_interior_crossings = graph_edge_boundary_contacts = 0
    for snap in snapshots:
        plan = astar.get(snap["snapshot_id"])
        if plan is None:
            continue
        for i, j in plan["graph_links"]:
            line = LineString((plan["graph_points"][i], plan["graph_points"][j]))
            graph_edges_offline += 1
            for polygon in map_polygons[snap["source_map"]]:
                crosses = line.relate_pattern(polygon, "T********")
                graph_edge_interior_crossings += crosses
                graph_edge_boundary_contacts += line.intersects(polygon) and not crosses
    assert graph_edge_interior_crossings == 0
    pairs, geometry_rows = [], []
    for snap in snapshots:
        sid = snap["snapshot_id"]
        if sid not in eligible:
            geometry_rows.append({"snapshot_id": sid, "source_map": snap["source_map"],
                                  "method": "excluded", "status": snap["eligibility"],
                                  "point_interior_valid": "", "strict_boundary_valid": ""})
            continue
        assert authors[sid]["asp_path"] == snap["asp_path"]
        polygons = map_polygons[snap["source_map"]]
        asp_metrics = path_metrics(snap["asp_path"], snap, polygons)
        astar_metrics = path_metrics(astar[sid]["path"], snap, polygons)
        for method, metrics in (("authors_asp", asp_metrics), ("our_astar", astar_metrics)):
            geometry_rows.append({"snapshot_id": sid, "source_map": snap["source_map"],
                                  "method": method,
                                  "status": "planned" if metrics["found"] else "no_path", **metrics})
        row = {"snapshot_id": sid, "source_map": snap["source_map"],
               "decision_index_0based": snap["decision_index_0based"],
               "sensor_radius": snap["sensor_radius"],
               "start": json.dumps(snap["start"]), "target": json.dumps(snap["target"]),
               "source_graph_nodes": snap["source_graph_nodes"],
               "source_graph_edges": len(snap["source_graph_edges"]),
               "source_skeleton_vertices": len(snap["skeleton_path"]),
               "source_skeleton_length": length(snap["skeleton_path"]),
               "sight_count": len(snap["sights"]),
               "asp_found": asp_metrics["found"], "astar_found": astar_metrics["found"],
               "astar_graph_nodes": astar[sid]["graph_nodes"],
               "astar_graph_edges": astar[sid]["graph_edges"],
               "astar_expanded_nodes": astar[sid]["expanded_nodes"],
               "asp_core_median_ms": authors[sid]["core_call_median_ms"],
               "asp_critical_median_ms": authors[sid]["critical_construction_median_ms"],
               "asp_optimization_median_ms": authors[sid]["optimization_median_ms"],
               "astar_build_median_ms": astar[sid]["build_median_ms"],
               "astar_core_median_ms": astar[sid]["core_call_median_ms"]}
        for label, metrics in (("asp", asp_metrics), ("astar", astar_metrics)):
            row.update({f"{label}_{key}": value for key, value in metrics.items()})
        row["astar_minus_asp_length"] = (row["astar_planned_length"] - row["asp_planned_length"]
                                          if asp_metrics["found"] and astar_metrics["found"] else None)
        row["astar_minus_asp_turns"] = (row["astar_turns"] - row["asp_turns"]
                                         if asp_metrics["found"] and astar_metrics["found"] else None)
        row["asp_length"] = row["asp_planned_length"]
        row["astar_length"] = row["astar_planned_length"]
        pairs.append(row)
    with (OUT / "robot-local-asp-vs-astar.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=pairs[0].keys())
        writer.writeheader()
        writer.writerows(pairs)
    fieldnames = list(dict.fromkeys(key for row in geometry_rows for key in row))
    with (OUT / "robot-local-geometry-validation.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(geometry_rows)
    paired_figures([row for row in pairs if row["asp_found"] and row["astar_found"]])
    timing_distributions(snapshots, authors, astar)
    representative_ids = list(dict.fromkeys((pairs[0]["snapshot_id"], pairs[-1]["snapshot_id"])))
    for sid in representative_ids:
        snap = next(item for item in snapshots if item["snapshot_id"] == sid)
        stem = sid.removeprefix("_map_")
        map_figure(snap, snap["asp_path"], astar[sid]["path"],
                   map_polygons[snap["source_map"]], f"{stem}-observed.png", False)
        map_figure(snap, snap["asp_path"], astar[sid]["path"],
                   map_polygons[snap["source_map"]], f"{stem}-ground-truth-validation.png", True)
    summary = {"captured": len(snapshots), "eligible": len(pairs),
               "excluded": len(snapshots) - len(pairs),
               "completed_pairs": len(pairs), "geometry_equivalence": visibility,
               "original_asp_segments_sight_certified": asp_segments,
               "original_asp_segments_uncertified": uncertified_asp_segments,
               "graph_edges_ground_truth_checked": graph_edges_offline,
               "graph_edge_interior_crossings": graph_edge_interior_crossings,
               "graph_edge_boundary_contacts": graph_edge_boundary_contacts,
               "asp_interior_valid": sum(row["asp_interior_only_valid"] for row in pairs),
               "astar_interior_valid": sum(row["astar_interior_only_valid"] for row in pairs),
               "asp_strict_valid": sum(row["asp_strict_boundary_valid"] for row in pairs),
               "astar_strict_valid": sum(row["astar_strict_boundary_valid"] for row in pairs),
               "asp_shorter": sum(row["astar_minus_asp_length"] is not None and row["astar_minus_asp_length"] > 1e-7 for row in pairs),
               "astar_shorter": sum(row["astar_minus_asp_length"] is not None and row["astar_minus_asp_length"] < -1e-7 for row in pairs),
               "median_astar_minus_asp_length": statistics.median(row["astar_minus_asp_length"] for row in pairs if row["astar_minus_asp_length"] is not None),
               "median_asp_core_ms": statistics.median(row["asp_core_median_ms"] for row in pairs),
               "median_astar_core_ms": statistics.median(row["astar_core_median_ms"] for row in pairs),
               "median_astar_build_ms": statistics.median(row["astar_build_median_ms"] for row in pairs)}
    (OUT / "robot-local-validation-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
