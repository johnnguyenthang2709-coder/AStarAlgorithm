"""Recompute unchanged upstream ASP from frozen sights and time its core call."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter_ns

import numpy as np


HERE = Path(__file__).resolve().parent
OUT = HERE / "robot-local-benchmark"


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
    snapshot_bytes = (OUT / manifest["snapshot_file"]).read_bytes()
    assert hashlib.sha256(snapshot_bytes).hexdigest() == manifest["snapshot_sha256"]
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == manifest["authors_commit"]
    assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    sys.path.insert(0, str(source))
    from Robot_paths_lib import approximately_shortest_path
    from Sight import Sight

    snapshots = json.loads(snapshot_bytes)["snapshots"]
    results = []
    previous_dir = Path.cwd()
    try:
        os.chdir(source)
        for snap in snapshots:
            if snap["snapshot_id"] not in manifest["eligible_ids"]:
                continue
            sights = Sight()
            for record in snap["sights"]:
                sights.add_sight(tuple(record["center"]), np.asarray(record["closed_sights"]),
                                 np.asarray(record["open_sights"]))
            skeleton = [tuple(point) for point in snap["skeleton_path"]]
            samples, critical_samples, optimize_samples = [], [], []
            total = manifest["timing"]["warmup_calls"] + manifest["timing"]["measured_calls"]
            for repetition in range(total):
                start = perf_counter_ns()
                asp, critical, critical_s, optimize_s = approximately_shortest_path(
                    skeleton, sights, snap["sensor_radius"])
                wall_ms = (perf_counter_ns() - start) / 1e6
                assert len(asp) == len(snap["asp_path"])
                assert all(abs(float(a[k]) - b[k]) < 1e-7
                           for a, b in zip(asp, snap["asp_path"]) for k in (0, 1))
                if repetition >= manifest["timing"]["warmup_calls"]:
                    samples.append(wall_ms)
                    critical_samples.append(critical_s * 1000)
                    optimize_samples.append(optimize_s * 1000)
            results.append({"snapshot_id": snap["snapshot_id"],
                            "asp_path": snap["asp_path"],
                            "critical_line_count": len(critical),
                            "core_call_median_ms": statistics.median(samples),
                            "critical_construction_median_ms": statistics.median(critical_samples),
                            "optimization_median_ms": statistics.median(optimize_samples),
                            "core_call_samples_ms": samples})
            print(snap["snapshot_id"], f"ASP {statistics.median(samples):.3f} ms", flush=True)
    finally:
        os.chdir(previous_dir)
    assert {r["snapshot_id"] for r in results} == set(manifest["eligible_ids"])
    (OUT / "authors-asp-timing.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
