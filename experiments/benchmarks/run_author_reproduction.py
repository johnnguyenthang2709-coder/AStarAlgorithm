"""Source-only upstream smoke runs with separate executed and planned metrics.

No upstream source is copied or patched. The wrapper observes the existing
Robot.update_coordinate call, then invokes the original Robot_run.robot_main.
Use a Python environment with numpy, matplotlib, pandas, cv2, and shapely.
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
from time import perf_counter

from shapely.geometry import LineString, Polygon

HERE = Path(__file__).resolve().parent
CASES = (("_map_deadend.csv", (70, 90)), ("_map_bugtrap.csv", (160, 80)))


def polygons(path: Path) -> list[Polygon]:
    groups, vertices = [], []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if row and row[0].strip().lower() == "x":
                if vertices:
                    groups.append(Polygon(vertices))
                vertices = []
            elif len(row) == 2:
                vertices.append((float(row[0]), float(row[1])))
    if vertices:
        groups.append(Polygon(vertices))
    return groups


def heading_turns(positions):
    headings = [math.atan2(b[1] - a[1], b[0] - a[0])
                for a, b in zip(positions, positions[1:]) if math.dist(a, b) > 1e-9]
    return sum(abs(math.atan2(math.sin(b-a), math.cos(b-a))) > math.radians(15)
               for a, b in zip(headings, headings[1:]))


def run(source: Path, filename: str, goal: tuple[int, int]) -> tuple[dict, dict]:
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from Robot_base import Robot_base
    from Robot_class import Robot
    from Robot_math_lib import inside_line_segment
    from Robot_run import robot_main

    observed = []
    original = Robot.update_coordinate

    def record(self, coords):
        observed.append((float(coords[0]), float(coords[1])))
        return original(self, coords)

    Robot.update_coordinate = record
    started = perf_counter()
    try:
        robot = robot_main(start=(0, 0), goal=goal, map_name=filename,
                           num_iter=60, robot_vision=20, robot_radius=0.5,
                           open_points_type=Robot_base.Open_points_type.Open_Arcs,
                           picking_strategy=Robot_base.Picking_strategy.neighbor_first,
                           experiment=True, save_image=False, save_log=False)
    finally:
        Robot.update_coordinate = original
    elapsed = perf_counter() - started
    if robot is None:
        raise ValueError(f"upstream rejected start/goal for {filename}")
    shapes = polygons(source / filename)
    if not shapes or not all(shape.is_valid for shape in shapes):
        raise ValueError(f"upstream map has invalid polygons: {filename}")
    segments = [LineString((a, b)) for a, b in zip(observed, observed[1:])
                if math.dist(a, b) > 1e-9]
    interior = [i for i, line in enumerate(segments)
                if any(line.relate_pattern(shape, "T********") for shape in shapes)]
    clearance = [i for i, line in enumerate(segments)
                 if any(line.distance(shape) < 0.5 - 1e-7 for shape in shapes)]
    actual = sum(line.length for line in segments)
    planned = sum(math.dist(a, b) for path in robot.visited_paths
                  for a, b in zip(path, path[1:]))
    collinear_turns = sum(not inside_line_segment(observed[i],
                                                  (observed[i-1], observed[i+1]))
                          for i in range(1, len(observed)-1))
    status = "goal_reached" if robot.reach_goal else "no_way" if robot.no_way_to_goal else "step_limit"
    result = {"map": filename, "map_sha256": hashlib.sha256((source / filename).read_bytes()).hexdigest(),
              "start": [0, 0], "goal": list(goal), "vision_radius": 20, "robot_radius": 0.5,
              "limit": 60, "status": status, "executed_distance": actual,
              "logged_planned_asp_distance": planned,
              "upstream_robot_cost": robot.cost,
              "coordinate_updates": len(observed), "asp_paths": len(robot.visited_paths),
              "turns_collinearity": collinear_turns,
              "turns_heading_15deg": heading_turns(observed),
              "interior_collision_segments": len(interior),
              "clearance_violation_segments": len(clearance),
              "elapsed_s": elapsed, "geometry_valid": True,
              "comparison_valid": not interior and not clearance}
    raw = {"config": {"map": filename, "goal": list(goal), "vision_radius": 20,
                      "robot_radius": 0.5, "limit": 60},
           "executed_positions": observed,
           "planned_asp_paths": [[[float(x), float(y)] for x, y in path]
                                 for path in robot.visited_paths],
           "interior_collision_segment_indices": interior,
           "clearance_violation_segment_indices": clearance}
    return result, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-dir", type=Path,
                        default=HERE.parents[2] / "AStarAlgorithm-authors-benchmark")
    args = parser.parse_args()
    source = args.authors_dir.resolve()
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if commit != "8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8":
        raise ValueError(f"unexpected upstream commit: {commit}")
    os.environ["MPLBACKEND"] = "Agg"
    os.chdir(source)  # upstream opens maps relative to cwd
    records, raw = [], {}
    for filename, goal in CASES:
        result, detail = run(source, filename, goal)
        records.append(result)
        raw[filename] = detail
        print(f"{filename}: {result['status']}, actual={result['executed_distance']:.3f}, "
              f"ASP={result['logged_planned_asp_distance']:.3f}, "
              f"collision segments={result['interior_collision_segments']}", flush=True)
    output = HERE / "author-reproduction.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    raw_path = HERE / "author-reproduction-raw.json"
    raw_path.write_text(json.dumps({"upstream_commit": commit, "runs": raw}, indent=2) + "\n",
                        encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
