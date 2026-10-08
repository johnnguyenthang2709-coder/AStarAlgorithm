from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.bar_scenarios import load_scenario
from app.services.bar_service import BarController


def test_frontier_exploration_reaches_open_goal_without_hidden_moves():
    scenario = load_scenario("open_route")
    result = BarController(scenario.rows, scenario.start, scenario.goal, 1).run()
    assert result["success"]
    assert result["metrics"]["executed_distance"] >= 8
    assert all(frame["event"] != "move" or frame["position"] for frame in result["frames"])


def test_unreachable_goal_terminates_after_exploring_known_component():
    scenario = load_scenario("unreachable")
    result = BarController(scenario.rows, scenario.start, scenario.goal, 2).run()
    assert result["status"] == "no_reachable_frontier"
    assert result["metrics"]["executed_distance"] < 100


def test_gate_metadata_is_absent_from_policy_and_planning_grid_masks_unknown():
    scenario = load_scenario("alley_reachable")
    controller = BarController(scenario.rows, scenario.start, scenario.goal, 1)
    controller.observe()
    assert 1 in controller.planning_grid()[5]
    assert not hasattr(controller, "evaluation_gate")
