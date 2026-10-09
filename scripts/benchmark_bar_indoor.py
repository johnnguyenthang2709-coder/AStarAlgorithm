"""Reproduce indoor continuous runs without filtering failure outcomes.

Example: .venv/Scripts/python.exe scripts/benchmark_bar_indoor.py --radii 5 7
The default matches the indoor API's radar-informed policy. --policy legacy
reproduces the historical indoor baseline without radar ranking.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import simulate_continuous
from app.services.bar_indoor import APARTMENT, OFFICE, CHALLENGE, IndoorConfig, generate_indoor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radii", nargs="+", type=float, default=[5., 7.])
    parser.add_argument("--seeds", nargs="*", type=int, default=[])
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--policy", choices=("radar", "legacy"), default="radar")
    args = parser.parse_args()
    cases = [APARTMENT, OFFICE, CHALLENGE]
    cases.extend(IndoorConfig(layout, seed) for layout in ("apartment", "office", "challenge")
                 for seed in args.seeds)
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("layout", "seed", "radius", "policy", "rooms", "doors", "furniture", "status", "success",
                     "executed_distance", "known_free_area", "observed_branches", "parent_returns",
                     "astar_returns", "fallback_returns", "verified_local_bounds", "astar_calls",
                     "formal_bar_certifications", "expanded_nodes", "turns", "planning_ms",
                     "wall_s", "frames", "json_bytes"))
    for config in cases:
        layout = generate_indoor(config)
        for radius in args.radii:
            begun = perf_counter()
            episode = simulate_continuous(layout.world, radius, args.limit,
                                          prefer_novelty=False, complete_frontier_route=True,
                                          trace_hierarchy=True,
                                          radar_informed=args.policy == "radar")
            elapsed = perf_counter() - begun
            metric, returns = episode["metrics"], episode["recoveries"]
            fallback = sum(item["fallback"] for item in returns)
            writer.writerow((config.layout, config.seed, f"{radius:g}", args.policy, len(layout.rooms),
                             len(layout.doors), len(layout.furniture), episode["status"],
                             episode["success"], f"{metric['executed_distance']:.3f}",
                             metric["observed_free_area"], metric["observed_branches"],
                             len(returns), len(returns)-fallback, fallback,
                             sum(item["invariant_verified"] for item in returns),
                             metric["replanning_count"], 0, metric["astar_expanded_nodes"],
                             metric["turn_count"], f"{metric['planning_time_ms']:.3f}",
                             f"{elapsed:.3f}", len(episode["frames"]),
                             len(json.dumps(episode, separators=(",", ":")))))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
