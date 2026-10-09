"""Run the prespecified sensing-radius matrix without changing controller policy."""

import csv
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from app.services.bar_continuous import ContinuousPolicy, simulate_continuous
from app.services.bar_indoor import IndoorConfig, generate_indoor
from app.services.bar_labyrinth import LabyrinthConfig, generate_labyrinth

FIELDS = ("kind", "case", "radius", "status", "success", "executed_distance",
          "turn_count", "decisions", "observations", "astar_calls", "expanded_nodes", "planning_ms", "sensing_ms",
          "selection_ms", "ranking_ms", "wall_ms", "returns", "certified_returns",
          "fallback_returns", "frames", "response_bytes")


def make_world(case):
    if case["kind"] == "labyrinth":
        return generate_labyrinth(LabyrinthConfig(seed=case["seed"])).world
    return generate_indoor(IndoorConfig(case["layout"], case["seed"])).world


def run(case, radius, limit):
    world = make_world(case)
    sense = world.sense
    select = ContinuousPolicy.select
    timings = {"sense": 0.0, "selection": 0.0, "decisions": 0, "observations": 0}

    def timed_sense(origin, extent):
        begun = perf_counter()
        observation = sense(origin, extent)
        timings["sense"] += perf_counter() - begun
        timings["observations"] += 1
        return observation

    def timed_select(policy):
        begun = perf_counter()
        result = select(policy)
        timings["selection"] += perf_counter() - begun
        timings["decisions"] += 1
        return result

    world.sense = timed_sense
    ContinuousPolicy.select = timed_select
    begun = perf_counter()
    try:
        episode = simulate_continuous(world, radius, limit,
                                      prefer_novelty=case["kind"] == "labyrinth",
                                      complete_frontier_route=True,
                                      trace_hierarchy=case["kind"] == "indoor",
                                      radar_informed=True)
    finally:
        wall_ms = (perf_counter() - begun) * 1000
        ContinuousPolicy.select = select
        world.sense = sense
    metric = episode["metrics"]
    returns = episode["recoveries"]
    return dict(zip(FIELDS, (case["kind"], case.get("layout", f"seed_{case['seed']}"), radius,
                             episode["status"], episode["success"],
                             round(metric["executed_distance"], 6), metric["turn_count"],
                             timings["decisions"], timings["observations"],
                             metric["replanning_count"], metric["astar_expanded_nodes"],
                             metric["planning_time_ms"], round(timings["sense"] * 1000, 3),
                             round(timings["selection"] * 1000, 3),
                             metric.get("ranking_time_ms", 0), round(wall_ms, 3),
                             len(returns), sum(r["invariant_verified"] for r in returns),
                             sum(r["fallback"] for r in returns), len(episode["frames"]),
                             len(json.dumps(episode, separators=(",", ":"))))))


def main():
    manifest = json.loads((HERE / "benchmark-manifest.json").read_text(encoding="utf-8"))
    supporting = manifest["supporting"]
    path = HERE / "sensor-robustness.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for case in supporting["sensor_cases"]:
            for radius in supporting["radii"]:
                row = run(case, radius, supporting["decision_limit"])
                writer.writerow(row)
                stream.flush()
                print(f"{row['kind']} {row['case']} r={radius} {row['status']} "
                      f"distance={row['executed_distance']:.2f} wall_ms={row['wall_ms']:.0f}",
                      file=sys.stderr, flush=True)
    print(path)


if __name__ == "__main__":
    main()
