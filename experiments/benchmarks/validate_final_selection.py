"""Static validation of the committed prospective episode selection."""

import hashlib
import json
from pathlib import Path
import subprocess

from shapely.geometry import Point

from finish_robot_local_benchmark import load_map


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / "AStarAlgorithm-authors-benchmark"


def main():
    selection_path = HERE / "robot-local-final-extension-selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    assert len(selection["episodes"]) <= selection["episode_cap"] <= 12
    assert len({e["episode_id"] for e in selection["episodes"]}) == len(selection["episodes"])
    assert subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip() == selection["authors_commit"]
    assert not subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain"], text=True).strip()
    manifest = json.loads((HERE / "robot-local-final-extension/robot-local-benchmark-manifest.json").read_text())
    assert manifest["selection_sha256"] == hashlib.sha256(selection_path.read_bytes()).hexdigest()
    records = []
    for episode in selection["episodes"]:
        path = SOURCE / episode["map"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == episode["map_sha256"]
        polygons = load_map(path)
        start, goal = Point(episode["start"]), Point(episode["goal"])
        start_clearance = min(start.distance(poly) for poly in polygons)
        goal_clearance = min(goal.distance(poly) for poly in polygons)
        assert start_clearance >= episode["source_robot_radius"]
        assert goal_clearance >= episode["source_robot_radius"]
        records.append({"episode_id": episode["episode_id"], "map": episode["map"],
                        "polygons": len(polygons), "start_clearance": start_clearance,
                        "goal_clearance": goal_clearance})
    print(json.dumps({"episodes": len(records), "static_geometry_valid": True,
                      "endpoints_clear_radius_0_5": True, "records": records}, indent=2))


if __name__ == "__main__":
    main()
