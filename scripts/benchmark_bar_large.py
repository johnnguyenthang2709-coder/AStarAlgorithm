"""Measure the two larger BAR demos through the existing FastAPI endpoint."""

import csv
import sys
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app


def main() -> None:
    writer = csv.DictWriter(sys.stdout, lineterminator="\n", fieldnames=[
        "scenario", "radius", "rows", "cols", "frames", "response_bytes",
        "endpoint_ms", "goal_reached", "gate_status", "autonomous_recoveries",
        "executed_distance", "astar_calls", "expanded_nodes", "turns", "astar_planning_ms",
    ])
    writer.writeheader()
    with TestClient(create_app()) as client:
        for name in ("expedition_narrow", "expedition_wide"):
            for radius in (1, 2, 4):
                start = perf_counter()
                response = client.post("/api/bar/simulate", json={"scenario": name, "radius": radius})
                elapsed_ms = (perf_counter() - start) * 1000
                response.raise_for_status()
                episode = response.json()
                metrics = episode["metrics"]
                writer.writerow({
                    "scenario": name, "radius": radius,
                    "rows": episode["rows"], "cols": episode["cols"],
                    "frames": len(episode["frames"]), "response_bytes": len(response.content),
                    "endpoint_ms": round(elapsed_ms, 1), "goal_reached": episode["success"],
                    "gate_status": metrics["bar_evaluation_status"],
                    "autonomous_recoveries": len(episode["recoveries"]),
                    "executed_distance": metrics["executed_distance"],
                    "astar_calls": metrics["replanning_count"],
                    "expanded_nodes": metrics["astar_expanded_nodes"],
                    "turns": metrics["turn_count"],
                    "astar_planning_ms": metrics["planning_time_ms"],
                })


if __name__ == "__main__":
    main()
