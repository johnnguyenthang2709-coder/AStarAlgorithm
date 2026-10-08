"""Reproduce endpoint size, timing, and Python memory for polygon-grid BAR demos."""

import csv
import sys
import tracemalloc
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import create_app


def main() -> None:
    fields = ["scenario", "radius", "shape", "frames", "response_bytes", "endpoint_ms",
              "peak_python_kib", "playback_snapshot_kib", "dom_cells", "goal_reached",
              "recoveries", "executed_distance", "astar_calls", "expanded_nodes", "turns"]
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    with TestClient(create_app()) as client:
        for name in ("irregular_u", "irregular_bugtrap"):
            for radius in (1, 2, 4):
                request = {"scenario": name, "radius": radius}
                start = perf_counter()
                response = client.post("/api/bar/simulate", json=request)
                elapsed_ms = (perf_counter() - start) * 1000
                response.raise_for_status()
                tracemalloc.start()
                memory_response = client.post("/api/bar/simulate", json=request)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                memory_response.raise_for_status()
                episode = response.json()
                metrics = episode["metrics"]
                cells = episode["rows"] * episode["cols"]
                frames = len(episode["frames"])
                writer.writerow({
                    "scenario": name, "radius": radius,
                    "shape": f"{episode['rows']}x{episode['cols']}",
                    "frames": frames, "response_bytes": len(response.content),
                    "endpoint_ms": round(elapsed_ms, 1),
                    "peak_python_kib": round(peak / 1024),
                    "playback_snapshot_kib": round(frames * cells / 1024),
                    "dom_cells": cells, "goal_reached": episode["success"],
                    "recoveries": len(episode["recoveries"]),
                    "executed_distance": metrics["executed_distance"],
                    "astar_calls": metrics["replanning_count"],
                    "expanded_nodes": metrics["astar_expanded_nodes"],
                    "turns": metrics["turn_count"],
                })


if __name__ == "__main__":
    main()
