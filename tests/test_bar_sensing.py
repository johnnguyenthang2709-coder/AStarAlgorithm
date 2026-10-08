from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.bar_scenarios import load_scenario
from app.services.bar_sensing import BLOCKED, FREE, UNKNOWN, sense


def test_fixtures_are_valid_and_gate_is_evaluation_only():
    for name in ("alley_reachable", "alley_turn", "wide_mouth_alley", "open_route", "unreachable"):
        scenario = load_scenario(name)
        assert scenario.rows[scenario.start[0]][scenario.start[1]] == "."
    assert load_scenario("open_route").evaluation_gates == ()
    assert len(load_scenario("wide_mouth_alley").evaluation_gates) == 3


def test_radius_and_occlusion():
    rows = (".....", ".#...", ".....")
    known = [[UNKNOWN] * 5 for _ in rows]
    changes = sense(rows, known, (1, 0), 2)
    assert ((1, 1), BLOCKED) in changes
    assert known[1][2] == UNKNOWN
    assert known[0][0] == FREE
    assert known[0][3] == UNKNOWN
    assert known[2][1] == UNKNOWN  # corner ray touches the blocker
