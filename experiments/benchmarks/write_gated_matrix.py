"""Record every frozen robot slot as unexecuted after the collision gate fails."""

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ("config_id", "source_map", "map_sha256", "start_x", "start_y", "goal_x", "goal_y",
          "sensing_radius", "robot_radius", "method", "status", "goal_success",
          "actual_distance", "planning_time_ms", "reason")


def main():
    manifest = json.loads((HERE / "benchmark-manifest.json").read_text(encoding="utf-8"))
    rows = []
    for world in manifest["robot"]["worlds"]:
        for goal in world["goals"]:
            for radius in manifest["robot"]["radii"]:
                config_id = f"{world['file']}:{goal[0]},{goal[1]}:r{radius}"
                for method in ("upstream_bundle_asp", "our_continuous_astar"):
                    rows.append(dict(zip(FIELDS, (config_id, world["file"], world["sha256"],
                                                  *world["start"], *goal, radius, world["robot_radius"],
                                                  method, "not_run_validity_gate", "", "", "",
                                                  "upstream executed segments cross obstacle interiors in Stage 1 reproduction"))))
    assert len(rows) == 96
    with (HERE / "robot-authors-vs-astar.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print("48 configurations, 96 unexecuted method slots after validity gate")


if __name__ == "__main__":
    main()
