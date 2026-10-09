"""Paired read-only benchmark for the 28 published runs and prespecified seeds.

Run: .venv/Scripts/python scripts/audit_bar_radar_benchmark.py
Held-out seeds 41, 73, 911 use default LabyrinthConfig at radii 5 and 7.
Every generated case is reported, including unsuccessful terminations.
"""

import csv
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import ContinuousPolicy, simulate_continuous
from app.services.bar_continuous_geometry import distance
from app.services.bar_labyrinth import LabyrinthConfig, generate_labyrinth
from benchmark_bar_radar import CASES, AUDIT_ANCHOR

HELD_OUT = (41, 73, 911)
ALL_CASES = {**CASES, **{f"heldout_{seed}": (
    lambda seed=seed: generate_labyrinth(LabyrinthConfig(seed=seed)).world, True)
    for seed in HELD_OUT}}
FIELDS = ("case", "radius", "policy", "status", "success", "executed_distance",
          "audit_anchor_probes", "revisits", "exploration_distance", "retreat_distance",
          "goal_distance", "astar_calls", "expanded_nodes", "returns", "certified_returns",
          "fallback_returns", "planning_ms", "sensing_ms", "selection_ms", "wall_ms",
          "frames", "response_bytes")


def run(case, radius, radar):
    make_world, novelty = ALL_CASES[case]
    world = make_world()
    sense_original = world.sense
    select_original = ContinuousPolicy.select
    times = {"sense": 0.0, "select": 0.0}

    def timed_sense(origin, r):
        start = perf_counter()
        result = sense_original(origin, r)
        times["sense"] += perf_counter() - start
        return result

    def timed_select(policy):
        start = perf_counter()
        result = select_original(policy)
        times["select"] += perf_counter() - start
        return result

    world.sense = timed_sense
    ContinuousPolicy.select = timed_select
    start = perf_counter()
    try:
        episode = simulate_continuous(world, radius, prefer_novelty=novelty,
                                      complete_frontier_route=True, radar_informed=radar)
    finally:
        wall_ms = (perf_counter() - start) * 1000
        ContinuousPolicy.select = select_original
    moves = [frame for frame in episode["frames"] if frame["event"] == "move"]
    seen = [world.start]
    revisits = 0
    for frame in moves:
        destination = (frame["position"]["x"], frame["position"]["y"])
        revisits += any(distance(destination, old) < 1e-6 for old in seen)
        seen.append(destination)
    metrics = episode["metrics"]
    recoveries = episode["recoveries"]
    by_phase = {phase: sum(frame["distance"] for frame in moves if frame["phase"] == phase)
                for phase in ("explore", "retreat", "goal")}
    probes = sum(frame["phase"] == "explore" and
                 distance((frame["from"]["x"], frame["from"]["y"]), AUDIT_ANCHOR) < .01
                 for frame in moves)
    return dict(zip(FIELDS, (
        case, radius, "radar" if radar else "baseline", episode["status"], episode["success"],
        round(metrics["executed_distance"], 6),
        probes if case == "lab23" and radius == 5 else "", revisits,
        round(by_phase["explore"], 6), round(by_phase["retreat"], 6),
        round(by_phase["goal"], 6), metrics["replanning_count"],
        metrics["astar_expanded_nodes"], len(recoveries),
        sum(item["invariant_verified"] for item in recoveries),
        sum(item["fallback"] for item in recoveries), metrics["planning_time_ms"],
        round(times["sense"] * 1000, 3), round(times["select"] * 1000, 3),
        round(wall_ms, 3), len(episode["frames"]),
        len(json.dumps(episode, separators=(",", ":"))),
    )))


def main():
    output = ROOT / "docs" / "bar-radar-paired-audit.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for case in ALL_CASES:
            for radius in (5, 7):
                for radar in (False, True):
                    row = run(case, radius, radar)
                    writer.writerow(row)
                    stream.flush()
                    print(f"{case} r={radius} {row['policy']} {row['status']} "
                          f"distance={row['executed_distance']:.2f} wall_ms={row['wall_ms']:.0f}",
                          file=sys.stderr, flush=True)
    print(output)


if __name__ == "__main__":
    main()
