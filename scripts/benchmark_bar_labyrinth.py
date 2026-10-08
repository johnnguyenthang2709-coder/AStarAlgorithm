"""Reproduce old/new Maze 3 continuous runs without filtering difficult outcomes."""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import simulate_continuous
from app.services.bar_labyrinth import (
    BLIND_ALLEY, COMPLEX, EXPLORATION, LabyrinthConfig, generate_labyrinth,
)
from app.services.bar_maze import SHOWCASE, generate_maze


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radii", nargs="+", type=float, default=[5., 7.])
    parser.add_argument("--seeds", nargs="*", type=int, default=[])
    parser.add_argument("--limit", type=int, default=250)
    args = parser.parse_args()
    cases = [("old-room-showcase", SHOWCASE, generate_maze),
             ("exploration", EXPLORATION, generate_labyrinth),
             ("blind-alley", BLIND_ALLEY, generate_labyrinth),
             ("complex", COMPLEX, generate_labyrinth)]
    cases += [(f"seed-{seed}", LabyrinthConfig(seed=seed), generate_labyrinth)
              for seed in args.seeds]
    print("case,seed,size,radius,polygons,vertices,loops,dead_ends,status,goal_reached,"
          "executed_distance,recoveries,certified_recoveries,astar_returns,fallback_returns,"
          "astar_calls,expanded_nodes,turns,planning_ms,wall_s,frames,json_bytes,"
          "max_graph_nodes,max_graph_edges", flush=True)
    for name, config, generator in cases:
        layout = generator(config)
        polygons = layout.world.polygons
        vertices = sum(len(p.exterior.coords) - 1 + sum(len(ring.coords) - 1 for ring in p.interiors)
                       if hasattr(p, "exterior") else len(p) for p in polygons)
        for radius in args.radii:
            begun = perf_counter()
            episode = simulate_continuous(layout.world, radius, args.limit,
                                          prefer_novelty=True, complete_frontier_route=True)
            elapsed = perf_counter() - begun
            metrics = episode["metrics"]
            recoveries = episode["recoveries"]
            certified = sum(item["invariant_verified"] for item in recoveries)
            fallback = sum(item["fallback"] for item in recoveries)
            columns = (name, config.seed, config.size, f"{radius:g}", len(polygons), vertices,
                       layout.loop_count, len(layout.dead_ends), episode["status"],
                       episode["success"], f"{metrics['executed_distance']:.3f}",
                       len(recoveries), certified, len(recoveries)-fallback, fallback,
                       metrics["replanning_count"], metrics["astar_expanded_nodes"],
                       metrics["turn_count"], f"{metrics['planning_time_ms']:.3f}",
                       f"{elapsed:.3f}", len(episode["frames"]),
                       len(json.dumps(episode, separators=(',', ':'))),
                       metrics["max_graph_nodes"], metrics["max_graph_edges"])
            print(",".join(map(str, columns)), flush=True)


if __name__ == "__main__":
    main()
