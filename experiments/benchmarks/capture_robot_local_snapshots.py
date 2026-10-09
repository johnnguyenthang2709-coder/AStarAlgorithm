"""Freeze the authors' observed state before each local-path decision.

The original checkout is imported, never edited. Its planning function and
path-log method are wrapped only to copy the inputs/output of each call.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
OUT = HERE / "robot-local-benchmark"
PIN = "8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8"
CASES = (("_map_deadend.csv", (70, 90)), ("_map_bugtrap.csv", (160, 80)))


def plain(value):
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    return value


def capture(source, filename, goal):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    import Robot_run
    from Robot_base import Robot_base
    from Robot_class import Robot

    old_expand = Robot.expand_visited_path
    decisions = []

    def record(self, path):
        # Called after this iteration's sight is added and ASP is computed,
        # before the robot's next coordinate is assigned.
        index = len(decisions)
        graph = self.visibility_graph.graph
        edges = sorted({tuple(sorted((tuple(u), tuple(v))))
                        for u, neighbors in graph.items() for v in neighbors})
        sight_records = []
        for center, closed in self.visited_sights.closed_sights.items():
            sight_records.append({"center": plain(center),
                                  "closed_sights": plain(closed),
                                  "open_sights": plain(self.visited_sights.open_sights[center])})
        decision = {"source_map": filename, "decision_index_0based": index,
                    "source_iteration": index + 1, "start": plain(self.coordinate),
                    "target": plain(self.next_point), "sensor_radius": float(self.vision_range),
                    "source_robot_radius": float(self.radius),
                    "sights": sight_records, "source_graph_edges": plain(edges),
                    "source_graph_nodes": len({p for edge in edges for p in edge}),
                    "skeleton_path": plain(self.skeleton_path),
                    "asp_path": plain(path),
                    "saw_goal": bool(self.saw_goal), "reach_goal": bool(self.reach_goal),
                    "no_way_to_goal": bool(self.no_way_to_goal)}
        decisions.append(decision)
        old_expand(self, path)

    Robot.expand_visited_path = record
    previous_dir = Path.cwd()
    try:
        os.chdir(source)
        robot = Robot_run.robot_main(start=(0, 0), goal=goal, map_name=filename,
                                     num_iter=60, robot_vision=20, robot_radius=0.5,
                                     open_points_type=Robot_base.Open_points_type.Open_Arcs,
                                     picking_strategy=Robot_base.Picking_strategy.neighbor_first,
                                     experiment=True, save_image=False, save_log=False)
    finally:
        os.chdir(previous_dir)
        Robot.expand_visited_path = old_expand
    assert robot is not None and robot.reach_goal
    return decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-dir", type=Path,
                        default=HERE.parents[2] / "AStarAlgorithm-authors-benchmark")
    args = parser.parse_args()
    source = args.authors_dir.resolve()
    sha = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    if sha != PIN or status:
        raise ValueError(f"authors' checkout must be clean at {PIN}; got {sha}, status={status}")
    original = json.loads((HERE / "author-motion-audit" / "decision-trace.json").read_text())
    manifest = json.loads((HERE / "benchmark-manifest.json").read_text())
    map_hashes = {world["file"]: world["sha256"] for world in manifest["robot"]["worlds"]}
    snapshots = []
    for filename, goal in CASES:
        digest = hashlib.sha256((source / filename).read_bytes()).hexdigest()
        assert digest == map_hashes[filename]
        captured = capture(source, filename, goal)
        old = original["cases"][filename]["decisions"]
        assert len(captured) == len(old)
        for fresh, prior in zip(captured, old):
            assert fresh["start"] == prior["coordinate"]
            assert fresh["target"] == prior["selected_next_point"]
            assert fresh["skeleton_path"] == prior["skeleton_path"]
            assert fresh["asp_path"] == prior["asp_path"]
            fresh["map_sha256"] = digest
            fresh["snapshot_id"] = f"{filename.removesuffix('.csv')}-{fresh['decision_index_0based']:02d}"
            fresh["eligibility"] = ("eligible_nontrivial_skeleton" if len(fresh["skeleton_path"]) > 2
                                    else "excluded_direct_two_vertex_path")
        snapshots.extend(captured)
        print(f"{filename}: {len(captured)} decisions, "
              f"{sum(s['eligibility'].startswith('eligible') for s in captured)} eligible", flush=True)
    OUT.mkdir(exist_ok=True)
    snapshot_path = OUT / "robot-local-snapshots.json"
    snapshot_path.write_text(json.dumps({"authors_commit": PIN, "snapshots": snapshots}, indent=2) + "\n",
                             encoding="utf-8")
    print(f"Frozen snapshots: {snapshot_path}")


if __name__ == "__main__":
    main()
