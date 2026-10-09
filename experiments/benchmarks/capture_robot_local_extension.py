"""Freeze prespecified held-out original-source decisions without outcome filtering."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from capture_robot_local_snapshots import HERE, PIN, capture


ROOT = HERE / "robot-local-benchmark"
OUT = HERE / "robot-local-extension"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-dir", type=Path,
                        default=HERE.parents[2] / "AStarAlgorithm-authors-benchmark")
    args = parser.parse_args()
    source = args.authors_dir.resolve()
    selections = [json.loads((ROOT / name).read_text()) for name in
                  ("robot-local-extension-selection.json", "robot-local-extension-selection-2.json")]
    assert all(selection["authors_commit"] == PIN for selection in selections)
    episodes = [episode for selection in selections for episode in selection["episodes"]]
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == PIN
    assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    snapshots, outcomes = [], []
    for episode in episodes:
        filename = episode["map"]
        digest = hashlib.sha256((source / filename).read_bytes()).hexdigest()
        assert digest == episode["map_sha256"]
        decisions, status = capture(source, filename, tuple(episode["goal"]),
                                    tuple(episode["start"]), episode["sensing_radius"],
                                    episode["source_robot_radius"], episode["iteration_cap"])
        for item in decisions:
            item["map_sha256"] = digest
            item["snapshot_id"] = f"{filename.removesuffix('.csv')}-{item['decision_index_0based']:02d}"
            item["eligibility"] = ("eligible_nontrivial_skeleton" if len(item["skeleton_path"]) > 2
                                   else "excluded_direct_or_empty_skeleton")
            item["source_episode_status"] = status
        snapshots.extend(decisions)
        outcomes.append({"map": filename, "decisions": len(decisions),
                         "eligible": sum(item["eligibility"].startswith("eligible") for item in decisions),
                         **status})
        print(outcomes[-1], flush=True)
    OUT.mkdir(exist_ok=True)
    content = (json.dumps({"authors_commit": PIN, "snapshots": snapshots}, indent=2) + "\n").encode()
    (OUT / "robot-local-snapshots.json").write_bytes(content)
    manifest = {
        "protocol_version": 1,
        "purpose": "Prespecified held-out frozen-state local paths, separate from initial six pairs",
        "source_baseline_commit": "954fcb680134ec031065c7b524c53e3327ff28bc",
        "authors_commit": PIN,
        "selection_files": ["../robot-local-benchmark/robot-local-extension-selection.json",
                            "../robot-local-benchmark/robot-local-extension-selection-2.json"],
        "snapshot_file": "robot-local-snapshots.json",
        "snapshot_sha256": hashlib.sha256(content).hexdigest(),
        "captured_decisions": len(snapshots),
        "eligible_decisions": sum(item["eligibility"].startswith("eligible") for item in snapshots),
        "eligible_ids": [item["snapshot_id"] for item in snapshots if item["eligibility"].startswith("eligible")],
        "excluded_decisions": sum(not item["eligibility"].startswith("eligible") for item in snapshots),
        "episode_outcomes": outcomes,
        "map_hashes": {episode["map"]: episode["map_sha256"] for episode in episodes},
        "eligibility_rule": selections[0]["eligibility_rule"],
        "collision_convention": {
            "primary": "Point-robot obstacle-interior excluding; obstacle-boundary contact permitted",
            "strict_secondary": "Obstacle boundary contact invalid",
            "radius_0_5": "Clearance diagnostic only, not a comparable finite-radius experiment",
            "world_boundary": "No global planner bound; links must be covered by the union of recorded local sights",
            "event_tolerance": 1e-9,
            "endpoint_tolerance": 1e-7},
        "our_graph_rule": "Scan-center vertices plus same start/target, sight-certified undirected Euclidean links",
        "timing": {"warmup_calls": 3, "measured_calls": 31, "statistic": "median"},
        "selection_policy": "Every eligible snapshot; retain failures and invalid paths",
        "no_ground_truth_in_planning": True}
    (OUT / "robot-local-benchmark-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Frozen held-out snapshots: {OUT}", flush=True)


if __name__ == "__main__":
    main()
