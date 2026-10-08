from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.bar_evaluation import evaluate
from app.services.bar_scenarios import Scenario, load_scenario
from app.services.bar_service import BarController
import astar_core


@pytest.mark.parametrize("name", ["alley_reachable", "alley_turn"])
def test_autonomous_recovery_and_evaluator_gate(name):
    scenario = load_scenario(name)
    controller = BarController(scenario.rows, scenario.start, scenario.goal, 2)
    episode = controller.run()
    report = evaluate(scenario, episode)
    assert episode["success"]
    assert controller.recoveries
    assert all(item["invariant_verified"] and item["retreat_ratio"] <= 1 for item in controller.recoveries)
    assert all(not item["fallback"] for item in controller.recoveries)
    assert report["gate_entries"] >= 1 and report["gate_exits"] >= 1
    assert report["gate_bound_verified"] is True
    assert any(frame["event"] == "move" and frame["phase"] == "retreat" for frame in episode["frames"])
    events = episode["frames"]
    begin = next(i for i, frame in enumerate(events) if frame["event"] == "recover_start")
    end = next(i for i, frame in enumerate(events) if frame["event"] == "recover_end")
    assert all(frame["event"] != "plan" for frame in events[begin + 1:end])
    assert all(frame["phase"] == "retreat" for frame in events[begin + 1:end]
               if frame["event"] == "move")


def test_shortcut_retreat_executes_shorter_cpp_astar_path(monkeypatch):
    scenario = load_scenario("alley_shortcut")
    controller = BarController(scenario.rows, scenario.start, scenario.goal, 2)
    original_plan = controller.plan
    recovery_searches = []

    def observe_plan(target, grid):
        result = original_plan(target, grid)
        if controller.current == (6, 10) and target == (5, 3):
            baseline = astar_core.grid_search(grid, controller.current, target, 4, "dijkstra", False)
            assert result["found"] and baseline["found"]
            assert result["cost"] == baseline["cost"] == 8
            recovery_searches.append(result)
        return result

    monkeypatch.setattr(controller, "plan", observe_plan)
    episode = controller.run()
    report = evaluate(scenario, episode)
    assert episode["success"] and len(recovery_searches) == 1
    assert report["bar_evaluation_status"] == "certified"
    assert report["gate_entry_length"] == 10
    assert report["gate_retreat_length"] == 8
    recovery = episode["recoveries"][0]
    assert recovery["fallback"] is False
    assert recovery["entry_length"] == 10
    assert recovery["retreat_length"] == 8
    assert recovery["invariant_verified"]

    events = episode["frames"]
    begin = next(i for i, frame in enumerate(events) if frame["event"] == "recover_start")
    end = next(i for i, frame in enumerate(events) if frame["event"] == "recover_end")
    selected = events[begin]
    assert selected["path"] == recovery_searches[0]["path"]
    assert selected["path"] != list(reversed(selected["entry_path"]))
    assert [frame["position"] for frame in events[begin + 1:end]
            if frame["event"] == "move"] == selected["path"][1:]


def test_evaluation_metadata_does_not_change_navigation():
    scenario = load_scenario("alley_reachable")
    episode = BarController(scenario.rows, scenario.start, scenario.goal, 2).run()
    alternative = Scenario(scenario.name, scenario.rows, scenario.start, scenario.goal,
                           (((5, 2), (5, 3)),))
    assert BarController(alternative.rows, alternative.start, alternative.goal, 2).run()["frames"] == episode["frames"]
    assert evaluate(scenario, episode) != evaluate(alternative, episode)


def test_wide_mouth_alley_exposes_recovery_coverage_limit():
    scenario = load_scenario("wide_mouth_alley")
    episode = BarController(scenario.rows, scenario.start, scenario.goal, 2).run()
    report = evaluate(scenario, episode)
    assert episode["success"]
    assert episode["recoveries"] == []
    assert report["gate_entries"] == 1 and report["gate_exits"] == 1
    assert report["bar_evaluation_status"] == "uncertified_exit"
    assert report["gate_bound_verified"] is None


def test_no_alley_and_unreachable_remain_finite():
    for name, success in (("open_route", True), ("unreachable", False)):
        scenario = load_scenario(name)
        result = BarController(scenario.rows, scenario.start, scenario.goal, 1).run()
        assert result["success"] is success
        assert result["status"] != "step_limit"
        assert not result["recoveries"]


def test_locked_retreat_falls_back_to_actual_reverse_route(monkeypatch):
    scenario = load_scenario("alley_reachable")
    controller = BarController(scenario.rows, scenario.start, scenario.goal, 2)
    original = controller.plan

    def failed_return(target, grid):
        if controller.current == (5, 10) and target == (5, 3):
            return {"found": False, "path": []}
        return original(target, grid)

    monkeypatch.setattr(controller, "plan", failed_return)
    result = controller.run()
    assert result["success"]
    assert controller.recoveries[0]["fallback"] is True
    assert controller.recoveries[0]["retreat_length"] == controller.recoveries[0]["entry_length"]
    start = next(frame for frame in result["frames"] if frame["event"] == "recover_start")
    assert start["path"] == list(reversed(start["entry_path"]))


def test_astar_matches_dijkstra_on_discovered_snapshot():
    scenario = load_scenario("alley_reachable")
    controller = BarController(scenario.rows, scenario.start, scenario.goal, 2)
    for _ in range(5):
        controller.observe()
        target, route = controller.choose_target()
        if target == controller.goal:
            break
        next_cell = route["path"][1]
        controller.move((next_cell["row"], next_cell["col"]))
    grid = controller.planning_grid()
    known_free = [(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value == 0]
    target = known_free[-1]
    a = astar_core.grid_search(grid, controller.current, target, 4, "astar", False)
    d = astar_core.grid_search(grid, controller.current, target, 4, "dijkstra", False)
    assert a["found"] == d["found"]
    assert a["cost"] == d["cost"]


def test_exhausted_branch_recovers_even_when_no_frontier_remains_anywhere():
    rows = ("########", "#....###", "########", "#..#####", "########")
    result = BarController(rows, (1, 1), (3, 1), 1).run()
    assert result["status"] == "no_reachable_frontier"
    assert result["recoveries"]
    assert result["recoveries"][0]["invariant_verified"]
