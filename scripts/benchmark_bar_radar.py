"""Controlled legacy/radar comparison; both modes use identical generated worlds.

Example: .venv/Scripts/python scripts/benchmark_bar_radar.py --cases lab23 indoor_apartment --radii 5 7
Wall time includes sensing, ranking, A* graph construction and frame serialization.
The local-probe columns refer only to the documented seed-23 audit anchor.
"""

import argparse
import csv
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import simulate_continuous
from app.services.bar_continuous_geometry import distance
from app.services.bar_indoor import APARTMENT, CHALLENGE, OFFICE, generate_indoor
from app.services.bar_labyrinth import BLIND_ALLEY, COMPLEX, EXPLORATION, LabyrinthConfig, generate_labyrinth

CASES = {
    "lab23": (lambda: generate_labyrinth(BLIND_ALLEY).world, True),
    "lab17": (lambda: generate_labyrinth(EXPLORATION).world, True),
    "lab_complex": (lambda: generate_labyrinth(COMPLEX).world, True),
    "lab2026": (lambda: generate_labyrinth(LabyrinthConfig(seed=2026)).world, True),
    "indoor_apartment": (lambda: generate_indoor(APARTMENT).world, False),
    "indoor_office": (lambda: generate_indoor(OFFICE).world, False),
    "indoor_challenge": (lambda: generate_indoor(CHALLENGE).world, False),
}
AUDIT_ANCHOR = (17.489416236334066, 15.822843066059457)


def measure(case: str, radius: float, radar: bool) -> dict:
    make_world, novelty = CASES[case]
    world = make_world()
    original_sense = world.sense
    sense_seconds = 0.0

    def timed_sense(origin, sensing_radius):
        nonlocal sense_seconds
        before = perf_counter()
        observation = original_sense(origin, sensing_radius)
        sense_seconds += perf_counter() - before
        return observation

    world.sense = timed_sense
    before = perf_counter()
    episode = simulate_continuous(world, radius, prefer_novelty=novelty,
                                  complete_frontier_route=True, radar_informed=radar)
    wall_seconds = perf_counter() - before
    frames, metrics, recoveries = episode["frames"], episode["metrics"], episode["recoveries"]
    probes = [frame for frame in frames if frame["event"] == "move" and frame["phase"] == "explore"
              and distance((frame["from"]["x"], frame["from"]["y"]), AUDIT_ANCHOR) < .01]
    return {
        "case": case, "radius": radius, "policy": "radar" if radar else "baseline",
        "status": episode["status"], "success": episode["success"],
        "executed_distance": round(metrics["executed_distance"], 6),
        "local_audit_probes": len(probes) if case == "lab23" and radius == 5 else "",
        "astar_calls": metrics["replanning_count"], "expanded_nodes": metrics["astar_expanded_nodes"],
        "recoveries": len(recoveries), "certified_returns": sum(r["invariant_verified"] for r in recoveries),
        "fallback_returns": sum(r["fallback"] for r in recoveries),
        "ranking_ms": metrics.get("ranking_time_ms", ""),
        "planning_ms": metrics["planning_time_ms"],
        "sensing_ms": round(sense_seconds * 1000, 3), "wall_ms": round(wall_seconds * 1000, 3),
        "frames": len(frames),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--radii", nargs="+", type=float, default=[5, 7])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stream = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=(
            "case", "radius", "policy", "status", "success", "executed_distance",
            "local_audit_probes", "astar_calls", "expanded_nodes", "recoveries",
            "certified_returns", "fallback_returns", "ranking_ms", "planning_ms",
            "sensing_ms", "wall_ms", "frames"))
        writer.writeheader()
        for case in args.cases:
            for radius in args.radii:
                for radar in (False, True):
                    row = measure(case, radius, radar)
                    writer.writerow(row)
                    stream.flush()
                    print(f"{case} r={radius:g} {row['policy']}: {row['status']}, "
                          f"distance={row['executed_distance']:.2f}, wall={row['wall_ms']:.0f} ms",
                          file=sys.stderr, flush=True)
    finally:
        if args.output:
            stream.close()


if __name__ == "__main__":
    main()
