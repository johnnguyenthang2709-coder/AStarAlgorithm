"""Run unchanged C++ visibility A* on links certified by frozen source sights."""

import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from time import perf_counter_ns


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import astar_core
from robot_local_geometry import segment_certified


OUT = HERE / "robot-local-benchmark"


def graph(snapshot):
    # Exactly the scan-center vertex choice of ContinuousPolicy.plan.
    points = list(dict.fromkeys(tuple(record["center"]) for record in snapshot["sights"]))
    for endpoint in (snapshot["start"], snapshot["target"]):
        if tuple(endpoint) not in points:
            points.append(tuple(endpoint))
    links, interval_count = [], 0
    for a in range(len(points)):
        for b in range(a + 1, len(points)):
            certified, intervals = segment_certified(
                points[a], points[b], snapshot["sights"], snapshot["sensor_radius"])
            interval_count += intervals
            if certified:
                links.append((a, b))
    return points, links, interval_count


def main():
    manifest = json.loads((OUT / "robot-local-benchmark-manifest.json").read_text())
    content = (OUT / manifest["snapshot_file"]).read_bytes()
    assert hashlib.sha256(content).hexdigest() == manifest["snapshot_sha256"]
    snapshots = json.loads(content)["snapshots"]
    results = []
    total = manifest["timing"]["warmup_calls"] + manifest["timing"]["measured_calls"]
    for snapshot in snapshots:
        if snapshot["snapshot_id"] not in manifest["eligible_ids"]:
            continue
        build_samples, core_samples = [], []
        for repetition in range(total):
            t0 = perf_counter_ns()
            points, links, interval_count = graph(snapshot)
            build_ms = (perf_counter_ns() - t0) / 1e6
            start = points.index(tuple(snapshot["start"]))
            target = points.index(tuple(snapshot["target"]))
            t0 = perf_counter_ns()
            result = astar_core.visibility_search(points, links, start, target, "astar")
            core_ms = (perf_counter_ns() - t0) / 1e6
            route = [points[index] for index in result["path"]]
            if result["found"]:
                assert route[0] == tuple(snapshot["start"])
                assert route[-1] == tuple(snapshot["target"])
                assert abs(sum(math.dist(a, b) for a, b in zip(route, route[1:]))
                           - result["cost"]) < 1e-6
            if repetition >= manifest["timing"]["warmup_calls"]:
                build_samples.append(build_ms)
                core_samples.append(core_ms)
        results.append({"snapshot_id": snapshot["snapshot_id"],
                        "found": result["found"], "path": route,
                        "cost": result["cost"], "graph_points": points,
                        "graph_links": links, "graph_nodes": len(points),
                        "graph_edges": len(links), "certification_intervals": interval_count,
                        "expanded_nodes": result["metrics"]["expanded_nodes"],
                        "build_median_ms": statistics.median(build_samples),
                        "core_call_median_ms": statistics.median(core_samples),
                        "build_samples_ms": build_samples,
                        "core_call_samples_ms": core_samples})
        print(snapshot["snapshot_id"], f"nodes={len(points)} links={len(links)} "
              f"found={result['found']} cost={result['cost']:.6f}", flush=True)
    assert {row["snapshot_id"] for row in results} == set(manifest["eligible_ids"])
    (OUT / "astar-plans.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
