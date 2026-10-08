"""Reproduce deterministic continuous BAR metrics (independent of grid results)."""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import simulate_continuous
from app.services.bar_continuous_geometry import ContinuousWorld


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radii", nargs="+", type=float, default=[4., 6.])
    parser.add_argument("--scenarios", nargs="+", default=["irregular_u", "irregular_bugtrap"])
    parser.add_argument("--limit", type=int, default=250)
    args = parser.parse_args()
    print("scenario,radius,status,success,executed_distance,recoveries,max_retreat_ratio,"
          "astar_calls,expanded_nodes,turns,planning_ms,wall_s,frames,response_bytes,"
          "max_graph_nodes,max_graph_edges")
    for scenario in args.scenarios:
        world = ContinuousWorld.load(scenario)
        for radius in args.radii:
            started = perf_counter()
            episode = simulate_continuous(world, radius, args.limit)
            elapsed = perf_counter() - started
            metrics = episode["metrics"]
            ratios = [item["retreat_ratio"] for item in episode["recoveries"]
                      if item["retreat_ratio"] is not None]
            size = len(json.dumps(episode, separators=(",", ":")))
            print(f"{scenario},{radius:g},{episode['status']},{episode['success']},"
                  f"{metrics['executed_distance']:.3f},{len(episode['recoveries'])},"
                  f"{max(ratios) if ratios else 0:.6f},{metrics['replanning_count']},"
                  f"{metrics['astar_expanded_nodes']},{metrics['turn_count']},"
                  f"{metrics['planning_time_ms']:.3f},{elapsed:.3f},{len(episode['frames'])},"
                  f"{size},{metrics['max_graph_nodes']},{metrics['max_graph_edges']}")


if __name__ == "__main__":
    main()
