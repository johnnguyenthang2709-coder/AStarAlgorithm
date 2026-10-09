"""Hash the finalized benchmark package, without modifying earlier baselines."""

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE.parents[2] / "AStarAlgorithm-authors-benchmark"
OUTPUT = HERE / "benchmark-final-manifest.json"

FILES = [
    "benchmark-manifest.json", "road-astar-dijkstra.csv", "road-validation.json",
    "road-edge-cases.csv", "exploration-ablation.csv", "frontier-cache.csv",
    "sensor-robustness.csv", "supporting-validation.json",
    "robot-authors-vs-astar.csv", "author-motion-validity-audit.md",
    "robot-local-benchmark/robot-local-benchmark-manifest.json",
    "robot-local-benchmark/robot-local-snapshots.json",
    "robot-local-benchmark/robot-local-asp-vs-astar.csv",
    "robot-local-extension/robot-local-benchmark-manifest.json",
    "robot-local-extension/robot-local-snapshots.json",
    "robot-local-extension/robot-local-asp-vs-astar.csv",
    "robot-local-final-extension-selection.json",
    "robot-local-final-extension/robot-local-benchmark-manifest.json",
    "robot-local-final-extension/robot-local-snapshots.json",
    "robot-local-final-extension/robot-local-asp-vs-astar.csv",
    "robot-local-final-extension/robot-local-geometry-validation.csv",
    "robot-local-final-extension/robot-local-validation-summary.json",
    "robot-local-final-extension/robot-local-timing-distributions.csv",
    "robot-local-final-extension/authors-asp-timing.json",
    "robot-local-final-extension/astar-plans.json",
    "robot-local-final-paired.csv", "robot-snapshot-eligibility-audit.csv",
    "robot-snapshot-eligibility-summary.json", "benchmark-final-summary.json",
    "FINAL-BENCHMARK-REPORT.md", "FINAL-BENCHMARK-SUMMARY.md",
    "benchmark-data-dictionary.md", "prepare_final_robot_extension.py",
    "capture_robot_local_final_extension.py", "validate_final_selection.py",
    "audit_robot_snapshot_eligibility.py", "finalize_academic_benchmark.py",
    "validate_final_benchmark.py", "write_final_manifest.py",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    current_branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    assert current_branch == "codex/academic-benchmark-final"
    authors_commit = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
    assert authors_commit == "8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8"
    assert not subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain"], text=True).strip()
    artifacts = FILES + [str(p.relative_to(HERE)).replace("\\", "/") for p in sorted((HERE/"final-figures").iterdir())]
    artifacts += [str(p.relative_to(HERE)).replace("\\", "/") for p in sorted((HERE/"tables").iterdir())]
    assert len([p for p in artifacts if p.startswith("final-figures/")]) == 14
    hashes = {name: sha(HERE/name) for name in sorted(artifacts)}
    baseline = json.loads((HERE/"benchmark-manifest.json").read_text())
    manifest = {
        "schema_version": 1,
        "branch": current_branch,
        "baseline_ancestry_commits": {
            "academic_benchmark": "da96440",
            "author_motion_audit": "0631f6c",
            "shared_state_local_benchmark": "ead37b1",
            "prospective_selection_frozen": "71c5204",
            "prospective_snapshots_frozen": "4aac5ef",
        },
        "authors_commit": authors_commit,
        "authors_checkout_clean": True,
        "paper_doi": "10.1016/j.robot.2025.105185",
        "paper_local_sha256": "8b9c99babedf9f2addc329c8bc26a1ca27448bdb6170139ded5607621f9c6b6b",
        "road_graph_sha256": baseline["road"]["graph_sha256"],
        "road_pairs": 180,
        "robot_initial_and_prior_heldout_snapshots": 118,
        "robot_initial_and_prior_heldout_eligible": 7,
        "robot_prospective_snapshots": 233,
        "robot_prospective_eligible": 14,
        "robot_total_snapshots": 351,
        "robot_total_local_pairs": 21,
        "robot_end_to_end_comparison": "blocked: unestablished compatible continuous-motion and footprint semantics",
        "collision_conventions": [
            "primary: point-center obstacle interior excluded, boundary contact allowed",
            "secondary: strict point-center interior and boundary excluded",
            "radius 0.5 clearance diagnostic only; not finite-radius motion validation",
        ],
        "figure_count": 14,
        "figure_sources": {
            "road-*": ["road-astar-dijkstra.csv", "data/road/graph.json", "unchanged C++ RoadEngine for mapped routes"],
            "robot-observed-paths.png": ["robot-local-final-extension/robot-local-snapshots.json",
                                         "robot-local-final-extension/P01-_map_deadend-07-observed.png"],
            "robot-* other": ["robot-local-final-paired.csv", "robot-snapshot-eligibility-audit.csv"],
            "support-*": ["exploration-ablation.csv", "frontier-cache.csv", "sensor-robustness.csv",
                          "docs/bar-indoor-radar-trace.csv"],
        },
        "artifact_sha256": hashes,
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{OUTPUT}: {len(hashes)} hashed artifacts")


if __name__ == "__main__":
    main()
