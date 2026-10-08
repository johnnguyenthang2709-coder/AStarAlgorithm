"""Reproducible continuous Maze 3 runs; never filter seeds by robot success."""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import simulate_continuous
from app.services.bar_maze import HARD, SHOWCASE, MazeConfig, generate_maze


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[17, 23])
    parser.add_argument("--radii", nargs="+", type=float, default=[5., 7.])
    parser.add_argument("--size", type=int, default=5)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--presets", action="store_true", help="also run showcase and harder fixed presets")
    args = parser.parse_args()
    cases = [(f"seed-{seed}", MazeConfig(seed=seed, size=args.size)) for seed in args.seeds]
    if args.presets:
        cases = [("showcase", SHOWCASE), ("hard", HARD)] + cases
    print("case,seed,size,radius,loops,dead_ends,status,goal_reached,executed_distance,"
          "recoveries,verified_recoveries,astar_calls,expanded_nodes,turns,planning_ms,"
          "wall_s,frames,json_bytes,max_graph_nodes,max_graph_edges", flush=True)
    for name, config in cases:
        layout = generate_maze(config)
        for radius in args.radii:
            begun = perf_counter()
            episode = simulate_continuous(layout.world, radius, args.limit,
                                          prefer_novelty=True, complete_frontier_route=True)
            elapsed = perf_counter() - begun
            metrics = episode["metrics"]
            verified = sum(item["invariant_verified"] for item in episode["recoveries"])
            print(f"{name},{config.seed},{config.size},{radius:g},{layout.loop_count},"
                  f"{len(layout.dead_ends)},{episode['status']},{episode['success']},"
                  f"{metrics['executed_distance']:.3f},{len(episode['recoveries'])},{verified},"
                  f"{metrics['replanning_count']},{metrics['astar_expanded_nodes']},"
                  f"{metrics['turn_count']},{metrics['planning_time_ms']:.3f},"
                  f"{elapsed:.3f},{len(episode['frames'])},"
                  f"{len(json.dumps(episode, separators=(',', ':')))},"
                  f"{metrics['max_graph_nodes']},{metrics['max_graph_edges']}", flush=True)


if __name__ == "__main__":
    main()
