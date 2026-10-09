"""Write the one prespecified final extension selection before source execution.

This reads source map bytes for hashes only. It never runs either planner or
examines any decision outcome. The resulting JSON is committed before capture.
"""

import hashlib
import json
from pathlib import Path

from capture_robot_local_snapshots import HERE, PIN


SOURCE = HERE.parents[2] / "AStarAlgorithm-authors-benchmark"
OUTPUT = HERE / "robot-local-final-extension-selection.json"

# Fixed before observing any of these source runs. Episode IDs avoid ambiguity
# where a map is reused with a different sensing radius or goal.
CASES = [
    ("P01", "_map_deadend.csv", (100, 100), 10),
    ("P02", "_map_deadend.csv", (100, 100), 30),
    ("P03", "_map_bugtrap.csv", (150, 150), 10),
    ("P04", "_map_bugtrap.csv", (150, 150), 30),
    ("P05", "_map_block.csv", (70, 90), 10),
    ("P06", "_map_blocks_1.csv", (100, 100), 20),
    ("P07", "_map_blocks.csv", (150, 150), 20),
    ("P08", "_map_forest.csv", (100, 100), 10),
    ("P09", "_map_forest_1.csv", (160, 80), 20),
    ("P10", "_map.csv", (70, 90), 20),
]


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"selection already frozen: {OUTPUT}")
    episodes = []
    for episode_id, filename, goal, radius in CASES:
        episodes.append({
            "episode_id": episode_id,
            "map": filename,
            "map_sha256": hashlib.sha256((SOURCE / filename).read_bytes()).hexdigest(),
            "start": [0, 0],
            "goal": list(goal),
            "sensing_radius": radius,
            "source_robot_radius": 0.5,
            "iteration_cap": 60,
        })
    selection = {
        "selection_version": 1,
        "purpose": "One prospective extension of original-source frozen local decisions",
        "authors_commit": PIN,
        "selection_basis": (
            "Original unmodified polygon CSV maps with independently checked valid "
            "polygons and free start/goal points; vary original maps, endpoint, "
            "and sensing radius. Selection is fixed before these source runs. "
            "Prior two-map and held-out results are acknowledged, not pooled "
            "into an unqualified prospective claim."
        ),
        "episodes": episodes,
        "episode_cap": 12,
        "captured_snapshot_cap": 300,
        "on_cap": "Stop capture at the first cap; report all earlier outcomes and truncation",
        "eligibility_rule": "Every captured original skeleton with more than two vertices",
        "selection_policy": "Compare every eligible snapshot; retain failures and invalid paths",
        "collision_convention": (
            "Point robot, obstacle interior excluded, boundary contact permitted "
            "in primary analysis; strict boundary exclusion secondary"
        ),
        "no_adaptive_replacement": True,
    }
    OUTPUT.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
