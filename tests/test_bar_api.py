from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import create_app


@pytest.mark.parametrize("scenario,expected", [
    ("alley_reachable", True), ("alley_turn", True), ("alley_shortcut", True),
    ("wide_mouth_alley", True),
    ("open_route", True), ("unreachable", False),
])
def test_bar_api_episode_and_metrics(scenario, expected):
    with TestClient(create_app()) as client:
        response = client.post("/api/bar/simulate", json={"scenario": scenario, "radius": 2})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is expected
    assert data["frames"][0]["event"] == "sense"
    assert data["metrics"]["replanning_count"] > 0
    assert data["metrics"]["planning_time_ms"] >= 0
    assert "evaluation_gate" not in data
    assert "groundTruthMap" not in data
    if scenario.startswith("alley"):
        assert data["metrics"]["gate_bound_verified"] is True
        assert data["recoveries"][0]["invariant_verified"] is True
    if scenario == "wide_mouth_alley":
        assert data["metrics"]["bar_evaluation_status"] == "uncertified_exit"
        assert data["metrics"]["gate_bound_verified"] is None


def test_bar_api_rejects_invalid_radius_and_scenario():
    with TestClient(create_app()) as client:
        assert client.post("/api/bar/simulate", json={"scenario": "open_route", "radius": 0}).status_code == 422
        assert client.post("/api/bar/simulate", json={"scenario": "other"}).status_code == 422
