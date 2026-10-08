"""Inspect actual Maze 3 return frames against Dijkstra on the same known graph."""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import astar_core

from app.services.bar_continuous import path_length, simulate_continuous
from app.services.bar_labyrinth import BLIND_ALLEY, generate_labyrinth


def point(value):
    return value["x"], value["y"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius", type=float, default=5.)
    args = parser.parse_args()
    world = generate_labyrinth(BLIND_ALLEY).world
    episode = simulate_continuous(world, args.radius, prefer_novelty=True,
                                  include_graph=True, complete_frontier_route=True)
    frames = episode["frames"]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("return_number", "start_frame", "end_frame", "anchor_x", "anchor_y",
                     "entry_length", "executed_retreat_length", "astar_route_length",
                     "same_graph_dijkstra_cost", "fallback", "trigger", "certified",
                     "next_explore_x", "next_explore_y"))
    count = 0
    for index, frame in enumerate(frames):
        if frame["event"] != "recover_start":
            continue
        count += 1
        end_index = next(i for i in range(index + 1, len(frames))
                         if frames[i]["event"] == "recover_end")
        end = frames[end_index]
        points = [point(value) for value in frame["graph_points"]]
        result = astar_core.visibility_search(points, frame["graph_links"],
                                              points.index(point(frame["position"])),
                                              points.index(point(frame["anchor"])),
                                              "dijkstra")
        route = [point(value) for value in frame["path"]]
        if not all(world.collision_free(a, b) for a, b in zip(route, route[1:])):
            raise AssertionError("recorded return intersects a wall")
        next_target = next((point(later["target"]) for later in frames[end_index + 1:]
                            if later["event"] == "plan" and later.get("phase") == "explore"),
                           (None, None))
        writer.writerow((count, index, end_index, frame["anchor"]["x"],
                         frame["anchor"]["y"], f"{frame['entry_length']:.6f}",
                         f"{end['retreat_length']:.6f}", f"{path_length(route):.6f}",
                         f"{result['cost']:.6f}" if result["found"] else "unreachable",
                         frame["fallback"], frame["trigger"],
                         end["invariant_verified"], *next_target))
    if count != len(episode["recoveries"]):
        raise AssertionError("return frame count differs from recovery records")


if __name__ == "__main__":
    main()
