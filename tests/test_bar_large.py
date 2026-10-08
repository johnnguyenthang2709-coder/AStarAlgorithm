import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import create_app
from app.services.bar_evaluation import evaluate
from app.services.bar_scenarios import load_scenario
from app.services.bar_sensing import UNKNOWN
from app.services.bar_service import BarController


@pytest.mark.parametrize("name,shape,expected", [
    ("expedition_narrow", (32, 32), {1: "no_entry", 2: "certified", 4: "certified"}),
    ("expedition_wide", (40, 40), {1: "uncertified_exit", 2: "uncertified_exit", 4: "uncertified_exit"}),
])
def test_large_scenarios_preserve_recovery_labels_and_partial_knowledge(name, shape, expected):
    scenario = load_scenario(name)
    assert (len(scenario.rows), len(scenario.rows[0])) == shape
    assert sum(row.count(".") for row in scenario.rows) > 100
    for radius, status in expected.items():
        controller = BarController(scenario.rows, scenario.start, scenario.goal, radius)
        episode = controller.run()
        report = evaluate(scenario, episode)
        assert episode["status"] == "goal_reached"
        assert report["bar_evaluation_status"] == status
        assert any(UNKNOWN in row for row in controller.known)
        assert all(recovery["invariant_verified"] for recovery in episode["recoveries"])
        if status == "certified":
            assert report["gate_bound_verified"] is True
            assert report["gate_retreat_length"] <= report["gate_entry_length"]
        elif status == "uncertified_exit":
            assert report["gate_entries"] == report["gate_exits"] >= 1
            assert report["gate_bound_verified"] is None
            assert episode["recoveries"]  # interior branches may still recover


@pytest.mark.parametrize("name,shape", [
    ("expedition_narrow", (32, 32)),
    ("expedition_wide", (40, 40)),
])
def test_large_scenarios_are_available_through_existing_api(name, shape):
    with TestClient(create_app()) as client:
        response = client.post("/api/bar/simulate", json={"scenario": name, "radius": 2})
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["rows"], data["cols"]) == shape
    assert data["success"]
    assert len(data["frames"]) > 300
    assert "evaluation_gate" not in data
