"""Export decision-level trace for the reproducible seed-23 radar run.

Example: .venv/Scripts/python scripts/audit_bar_radar_decisions.py --output docs/bar-radar-decisions.csv
The area and wall-fragment counts come from sensor observations after each
decision; distinct fragment count is not a blocked-area measurement.
"""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import path_length, simulate_continuous
from app.services.bar_labyrinth import BLIND_ALLEY, generate_labyrinth


def pair(point):
    return (point["x"], point["y"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius", type=float, default=5)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "bar-radar-decisions.csv")
    args = parser.parse_args()
    episode = simulate_continuous(generate_labyrinth(BLIND_ALLEY).world, args.radius,
                                  prefer_novelty=True, complete_frontier_route=True,
                                  radar_informed=True, trace_decisions=True)
    grouped = {}
    for frame_number, frame in enumerate(episode["frames"]):
        index = frame.get("decision_index", frame.get("decision", {}).get("index"))
        if index is not None:
            grouped.setdefault(index, []).append((frame_number, frame))
    columns = ("decision", "frames", "position", "action", "target", "reason",
               "active_branch", "parent_branch", "eligible_frontiers", "estimated_gain",
               "estimated_travel", "planned_length", "executed_distance",
               "new_free_area", "new_wall_fragments", "return_trigger", "fallback")
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for index, frames in sorted(grouped.items()):
            primary = next(((number, frame) for number, frame in frames
                            if frame["event"] in ("plan", "recover_start")), None)
            if primary is None:
                continue
            number, frame = primary
            decision = frame.get("decision", {})
            senses = [item for _, item in frames if item["event"] == "sense" and _ > number]
            moves = [item for _, item in frames if item["event"] == "move"]
            route = [pair(point) for point in frame.get("path", ())]
            writer.writerow({
                "decision": index, "frames": f"{number}-{frames[-1][0]}",
                "position": pair(frame["position"]),
                "action": frame.get("phase", "retreat"),
                "target": pair(frame.get("target", frame.get("anchor"))),
                "reason": decision.get("reason"),
                "active_branch": decision.get("active_branch"),
                "parent_branch": decision.get("parent_branch"),
                "eligible_frontiers": decision.get("eligible"),
                "estimated_gain": decision.get("estimated_gain"),
                "estimated_travel": decision.get("estimated_travel"),
                "planned_length": round(path_length(route), 6),
                "executed_distance": round(sum(item["distance"] for item in moves), 6),
                "new_free_area": round(sum(item["new_area"] for item in senses), 6),
                "new_wall_fragments": sum(item["new_wall_fragments"] for item in senses),
                "return_trigger": frame.get("trigger"), "fallback": frame.get("fallback"),
            })
    print(f"{episode['status']}: {len(grouped)-1} decisions; {args.output}")


if __name__ == "__main__":
    main()
