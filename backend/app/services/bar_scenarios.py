"""Benchmark maps. The evaluator gate is deliberately separate from robot observations."""

import json
from dataclasses import dataclass
from pathlib import Path


SCENARIO_DIR = Path(__file__).resolve().parents[3] / "data" / "bar"


@dataclass(frozen=True)
class Scenario:
    name: str
    rows: tuple[str, ...]
    start: tuple[int, int]
    goal: tuple[int, int]
    evaluation_gates: tuple[tuple[tuple[int, int], tuple[int, int]], ...]


def load_scenario(name: str) -> Scenario:
    if not name or not name.replace("_", "").isalnum():
        raise ValueError("invalid scenario name")
    path = SCENARIO_DIR / f"{name}.json"
    if not path.is_file():
        raise ValueError("unknown BAR scenario")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = tuple(data["rows"])
    if not rows or not rows[0] or any(len(row) != len(rows[0]) or set(row) - {".", "#"} for row in rows):
        raise ValueError("scenario grid must be a nonempty rectangular ./# map")
    start, goal = tuple(data["start"]), tuple(data["goal"])
    def free(cell: tuple[int, int]) -> bool:
        r, c = cell
        return 0 <= r < len(rows) and 0 <= c < len(rows[0]) and rows[r][c] == "."
    if not free(start) or not free(goal):
        raise ValueError("scenario endpoints must be free")
    raw_gates = data.get("evaluation_gate_edges", [])
    if "evaluation_gate" in data:
        raw_gates = [data["evaluation_gate"]]
    gates = tuple((tuple(item["outside"]), tuple(item["inside"])) for item in raw_gates)
    if len(set(gates)) != len(gates) or any(
        not all(free(cell) for cell in gate) or
        abs(gate[0][0] - gate[1][0]) + abs(gate[0][1] - gate[1][1]) != 1
        for gate in gates
    ):
        raise ValueError("evaluation gate edges must be distinct adjacent free-cell pairs")
    return Scenario(name, rows, start, goal, gates)
