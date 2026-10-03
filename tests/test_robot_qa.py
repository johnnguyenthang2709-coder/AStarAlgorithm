"""Deterministic Robot Lab scenarios through the real API and C++ binding."""

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as active:
        yield active


@pytest.mark.parametrize("grid,start,goal,movement,found,cost", [
    ([[0, 0, 0, 0]], (0, 0), (0, 3), 4, True, 3),
    ([[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 0]],
     (0, 0), (0, 4), 4, True, 8),
    ([[0, 1], [1, 0]], (0, 0), (1, 1), 8, False, None),
    ([[0, 0], [0, 0]], (0, 0), (1, 1), 8, True, 1.5),
    ([[1, 0], [0, 0]], (0, 1), (1, 0), 8, True, 2),
])
def test_grid_scenarios(client, grid, start, goal, movement, found, cost):
    response = client.post("/api/grid/search", json={
        "grid": grid, "start": {"row": start[0], "col": start[1]},
        "goal": {"row": goal[0], "col": goal[1]},
        "movement": movement, "algorithm": "astar", "trace": True})
    assert response.status_code == 200
    result = response.json()
    assert result["found"] is found
    assert result["cost"] == cost
    assert bool(result["path"]) is found
    assert result["trace"]


def test_replan_uses_current_robot_cell(client):
    grid = [[0] * 5 for _ in range(3)]
    initial = client.post("/api/grid/search", json={
        "grid": grid, "start": {"row": 1, "col": 0},
        "goal": {"row": 1, "col": 4}, "movement": 4}).json()
    assert initial["path"][1] == {"row": 1, "col": 1}
    replanned = client.post("/api/grid/replan", json={
        "grid": grid, "current": initial["path"][1],
        "goal": {"row": 1, "col": 4},
        "new_obstacles": [{"row": 1, "col": 2}],
        "movement": 4, "algorithm": "astar", "trace": True})
    assert replanned.status_code == 200
    route = replanned.json()
    assert route["found"] is True
    assert route["path"][0] == {"row": 1, "col": 1}
    assert route["path"][-1] == {"row": 1, "col": 4}
    assert {"row": 1, "col": 2} not in route["path"]
    assert route["cost"] == 5
