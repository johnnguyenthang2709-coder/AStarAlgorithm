"""Fixed BAR experiment matrix; run with PYTHONPATH=backend after building C++."""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_evaluation import evaluate
from app.services.bar_scenarios import load_scenario
from app.services.bar_service import BarController
import astar_core


def main() -> None:
    writer = csv.DictWriter(sys.stdout, lineterminator="\n", fieldnames=[
        "scenario", "radius", "success", "status", "executed_distance", "turn_count",
        "astar_expanded_nodes", "replanning_count", "planning_time_ms",
        "gate_entry_length", "gate_retreat_length", "gate_retreat_ratio", "gate_bound_verified",
        "gate_entries", "gate_exits", "bar_evaluation_status", "astar_retreat_count",
        "fallback_retreat_count", "full_map_shortest_distance", "online_excess_distance",
    ])
    writer.writeheader()
    for name in ("alley_reachable", "alley_turn", "alley_shortcut", "wide_mouth_alley", "open_route", "unreachable"):
        scenario = load_scenario(name)
        full_map = [[int(cell == "#") for cell in row] for row in scenario.rows]
        oracle = astar_core.grid_search(full_map, scenario.start, scenario.goal, 4, "astar", False)
        full_map_distance = oracle["cost"] if oracle["found"] else None
        for radius in (1, 2, 3):
            episode = BarController(scenario.rows, scenario.start, scenario.goal, radius).run()
            gate = evaluate(scenario, episode)
            writer.writerow({"scenario": name, "radius": radius, "success": episode["success"],
                             "status": episode["status"], **episode["metrics"], **gate,
                             "astar_retreat_count": len(episode["recoveries"]) - sum(
                                 recovery["fallback"] for recovery in episode["recoveries"]),
                             "fallback_retreat_count": sum(
                                 recovery["fallback"] for recovery in episode["recoveries"]),
                             "full_map_shortest_distance": full_map_distance,
                             "online_excess_distance": episode["metrics"]["executed_distance"] - full_map_distance
                             if full_map_distance is not None and episode["success"] else None})


if __name__ == "__main__":
    main()
