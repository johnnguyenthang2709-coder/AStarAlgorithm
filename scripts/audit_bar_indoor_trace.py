"""Emit a reproducible parent-return trace for the indoor apartment preset."""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import path_length, simulate_continuous
from app.services.bar_indoor import APARTMENT, generate_indoor


def main() -> None:
    episode = simulate_continuous(generate_indoor(APARTMENT).world, 5,
                                  prefer_novelty=False, complete_frontier_route=True,
                                  trace_hierarchy=True, radar_informed=True)
    frames = episode["frames"]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("frame", "branch", "parent", "trigger", "entry_length", "astar_route_length",
                     "executed_return_length", "fallback", "bound_verified", "next_sibling"))
    recovery_index = 0
    for index, frame in enumerate(frames):
        if frame["event"] != "recover_start":
            continue
        record = episode["recoveries"][recovery_index]
        recovery_index += 1
        end = next(i for i in range(index + 1, len(frames)) if frames[i]["event"] == "recover_end")
        sibling = next((item["branch_id"] for item in frames[end + 1:]
                        if item["event"] == "branch" and item["status"] == "active"
                        and item["parent_id"] == frame["parent_id"]), "")
        writer.writerow((index, frame["branch_id"], frame["parent_id"], frame["trigger"],
                         f"{frame['entry_length']:.6f}",
                         f"{path_length([(p['x'], p['y']) for p in frame['path']]):.6f}",
                         f"{record['retreat_length']:.6f}", frame["fallback"],
                         record["invariant_verified"], sibling))


if __name__ == "__main__":
    main()
