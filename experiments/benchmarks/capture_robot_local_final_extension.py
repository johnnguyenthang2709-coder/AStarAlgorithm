"""Capture the once-frozen prospective source episodes without planner filtering."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from capture_robot_local_snapshots import HERE, PIN, capture


SELECTION = HERE / "robot-local-final-extension-selection.json"
OUT = HERE / "robot-local-final-extension"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-dir", type=Path,
                        default=HERE.parents[2] / "AStarAlgorithm-authors-benchmark")
    parser.add_argument("--verify-only", action="store_true",
                        help="Replay the fixed source episodes and compare to committed snapshot hash")
    args = parser.parse_args()
    source = args.authors_dir.resolve()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    assert selection["authors_commit"] == PIN
    assert len(selection["episodes"]) <= selection["episode_cap"]
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == PIN
    assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    if OUT.exists() and not args.verify_only:
        raise FileExistsError(f"capture is immutable once written: {OUT}")
    snapshots, outcomes = [], []
    cap = selection["captured_snapshot_cap"]
    for episode in selection["episodes"]:
        filename = episode["map"]
        digest = hashlib.sha256((source / filename).read_bytes()).hexdigest()
        assert digest == episode["map_sha256"]
        error = None
        try:
            decisions, status = capture(source, filename, tuple(episode["goal"]),
                                        tuple(episode["start"]), episode["sensing_radius"],
                                        episode["source_robot_radius"], episode["iteration_cap"])
        except Exception as exc:
            # A source failure is an episode outcome. Never replace its map or
            # configuration after observing it.
            decisions, status, error = [], {"reach_goal": False, "no_way_to_goal": False}, repr(exc)
        remaining = cap - len(snapshots)
        retained = decisions[:remaining]
        for item in retained:
            item["map_sha256"] = digest
            item["episode_id"] = episode["episode_id"]
            item["snapshot_id"] = f"{episode['episode_id']}-{filename.removesuffix('.csv')}-{item['decision_index_0based']:02d}"
            item["eligibility"] = ("eligible_nontrivial_skeleton" if len(item["skeleton_path"]) > 2
                                   else "excluded_direct_or_empty_skeleton")
            item["source_episode_status"] = status
        snapshots.extend(retained)
        outcome = {"episode_id": episode["episode_id"], "map": filename,
                   "decisions_source": len(decisions), "decisions_retained": len(retained),
                   "eligible_retained": sum(item["eligibility"].startswith("eligible") for item in retained),
                   "truncated": len(retained) != len(decisions), "source_error": error, **status}
        outcomes.append(outcome)
        print(outcome, flush=True)
        if len(snapshots) >= cap:
            break
    content = (json.dumps({"authors_commit": PIN, "snapshots": snapshots}, indent=2) + "\n").encode()
    if args.verify_only:
        committed = json.loads((OUT / "robot-local-benchmark-manifest.json").read_text())
        assert hashlib.sha256(content).hexdigest() == committed["snapshot_sha256"]
        assert outcomes == committed["episode_outcomes"]
        print(f"Exact source replay verified: {len(snapshots)} frozen decisions", flush=True)
        return
    OUT.mkdir()
    (OUT / "robot-local-snapshots.json").write_bytes(content)
    manifest = {
        "protocol_version": 1,
        "purpose": "One frozen prospective extension; original-source local path states",
        "source_baseline_commit": "954fcb680134ec031065c7b524c53e3327ff28bc",
        "authors_commit": PIN,
        "selection_files": ["../robot-local-final-extension-selection.json"],
        "selection_sha256": hashlib.sha256(SELECTION.read_bytes()).hexdigest(),
        "snapshot_file": "robot-local-snapshots.json",
        "snapshot_sha256": hashlib.sha256(content).hexdigest(),
        "captured_decisions": len(snapshots),
        "eligible_decisions": sum(s["eligibility"].startswith("eligible") for s in snapshots),
        "eligible_ids": [s["snapshot_id"] for s in snapshots if s["eligibility"].startswith("eligible")],
        "excluded_decisions": sum(not s["eligibility"].startswith("eligible") for s in snapshots),
        "episode_outcomes": outcomes,
        "map_hashes": {e["map"]: e["map_sha256"] for e in selection["episodes"]},
        "eligibility_rule": selection["eligibility_rule"],
        "collision_convention": {
            "primary": "Point-robot obstacle-interior excluding; obstacle-boundary contact permitted",
            "strict_secondary": "Obstacle boundary contact invalid",
            "radius_0_5": "Clearance diagnostic only, not a comparable finite-radius experiment",
            "world_boundary": "No global planner bound; links must be covered by the union of recorded local sights",
            "event_tolerance": 1e-9,
            "endpoint_tolerance": 1e-7,
        },
        "our_graph_rule": "Scan-center vertices plus same start/target, sight-certified undirected Euclidean links",
        "timing": {"warmup_calls": 3, "measured_calls": 31, "statistic": "median"},
        "selection_policy": selection["selection_policy"],
        "no_ground_truth_in_planning": True,
    }
    (OUT / "robot-local-benchmark-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Frozen {len(snapshots)} prospective decisions in {OUT}", flush=True)


if __name__ == "__main__":
    main()
