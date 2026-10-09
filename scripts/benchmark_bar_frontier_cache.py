"""Paired full-frontier versus incremental-mask radar benchmark.

Run: .venv/Scripts/python scripts/benchmark_bar_frontier_cache.py
Uses the 20 configurations from the prior comparative audit, including held-out
labyrinth seeds 41, 73, and 911. The reference forces authoritative full wall
reconstruction; the optimized run uses the production incremental mask.
"""

import argparse
import csv
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app.services.bar_continuous as module
from app.services.bar_continuous import ContinuousPolicy, simulate_continuous
from audit_bar_radar_benchmark import ALL_CASES

FIELDS = ("case", "radius", "variant", "status", "success", "executed_distance",
          "astar_calls", "expanded_nodes", "returns", "equivalent_to_full",
          "full_reconstructions", "incremental_updates", "frontier_calls",
          "score_calls", "score_cache_hits", "mean_eligible_candidates",
          "frontier_total_ms", "frontier_mean_ms", "frontier_p95_ms",
          "update_total_ms", "update_mean_ms", "update_p95_ms",
          "ranking_ms", "wall_ms", "wall_mask_wkb_bytes")


def percentile(values, fraction):
    if not values:
        return 0.
    ordered = sorted(values)
    return ordered[max(0, int(fraction * len(ordered) + .999999) - 1)]


def run(world_factory, radius, novelty, reference):
    world = world_factory()
    original_frontier = module.possible_frontier
    original_extend = module.extend_wall_mask
    original_gain = ContinuousPolicy._frontier_gain
    original_select = ContinuousPolicy.select
    timings = {"frontier": [], "update": [], "full": 0, "score_calls": 0,
               "score_hits": 0, "eligible": [], "policy": None}

    def frontier(known_free, border, walls, wall_mask=None):
        mask = None if reference else wall_mask
        timings["full"] += mask is None
        before = perf_counter()
        result = original_frontier(known_free, border, walls, mask)
        timings["frontier"].append((perf_counter() - before) * 1000)
        return result

    def extend(mask, new_walls):
        if reference:
            return mask  # restore the original full-reconstruction cost model
        before = perf_counter()
        result = original_extend(mask, new_walls)
        timings["update"].append((perf_counter() - before) * 1000)
        return result

    def gain(policy, candidate):
        timings["score_calls"] += 1
        timings["score_hits"] += policy.candidate_key(candidate) in policy._frontier_scores
        return original_gain(policy, candidate)

    def select(policy):
        timings["policy"] = policy
        result = original_select(policy)
        timings["eligible"].append(policy.last_decision.get("eligible", 0))
        return result

    module.possible_frontier = frontier
    module.extend_wall_mask = extend
    ContinuousPolicy._frontier_gain = gain
    ContinuousPolicy.select = select
    begun = perf_counter()
    try:
        episode = simulate_continuous(world, radius, prefer_novelty=novelty,
                                      complete_frontier_route=True,
                                      radar_informed=True)
    finally:
        wall_ms = (perf_counter() - begun) * 1000
        module.possible_frontier = original_frontier
        module.extend_wall_mask = original_extend
        ContinuousPolicy._frontier_gain = original_gain
        ContinuousPolicy.select = original_select
    policy = timings["policy"]
    metrics = episode["metrics"]
    row = {
        "status": episode["status"], "success": episode["success"],
        "executed_distance": round(metrics["executed_distance"], 6),
        "astar_calls": metrics["replanning_count"],
        "expanded_nodes": metrics["astar_expanded_nodes"],
        "returns": len(episode["recoveries"]),
        "full_reconstructions": timings["full"],
        "incremental_updates": len(timings["update"]),
        "frontier_calls": len(timings["frontier"]),
        "score_calls": timings["score_calls"],
        "score_cache_hits": timings["score_hits"],
        "mean_eligible_candidates": round(statistics.mean(timings["eligible"]), 3),
        "frontier_total_ms": round(sum(timings["frontier"]), 3),
        "frontier_mean_ms": round(statistics.mean(timings["frontier"]), 3),
        "frontier_p95_ms": round(percentile(timings["frontier"], .95), 3),
        "update_total_ms": round(sum(timings["update"]), 3),
        "update_mean_ms": round(statistics.mean(timings["update"]), 3) if timings["update"] else 0,
        "update_p95_ms": round(percentile(timings["update"], .95), 3),
        "ranking_ms": metrics["ranking_time_ms"],
        "wall_ms": round(wall_ms, 3),
        "wall_mask_wkb_bytes": len(policy._wall_mask.wkb) if policy._wall_mask is not None else 0,
    }
    return episode, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", choices=ALL_CASES, default=list(ALL_CASES))
    parser.add_argument("--radii", nargs="+", type=float, default=[5, 7])
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "bar-frontier-cache-benchmark.csv")
    args = parser.parse_args()
    all_equal = True
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for name in args.cases:
            factory, novelty = ALL_CASES[name]
            for radius in args.radii:
                full, full_row = run(factory, radius, novelty, True)
                cached, cached_row = run(factory, radius, novelty, False)
                equal = (full["status"] == cached["status"] and
                         full["frames"] == cached["frames"] and
                         full["recoveries"] == cached["recoveries"] and
                         full["metrics"]["executed_distance"] ==
                         cached["metrics"]["executed_distance"])
                all_equal &= equal
                for variant, row in (("full", full_row), ("cached", cached_row)):
                    writer.writerow({"case": name, "radius": radius, "variant": variant,
                                     "equivalent_to_full": equal, **row})
                stream.flush()
                print(f"{name} r={radius:g} equivalent={equal} "
                      f"frontier={full_row['frontier_total_ms']:.0f}/"
                      f"{cached_row['frontier_total_ms']:.0f} ms wall="
                      f"{full_row['wall_ms']:.0f}/{cached_row['wall_ms']:.0f} ms",
                      flush=True)
    if not all_equal:
        raise AssertionError("a cached episode changed observable navigation behavior")
    print(args.output)


if __name__ == "__main__":
    main()
