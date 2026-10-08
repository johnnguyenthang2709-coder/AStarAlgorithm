from pathlib import Path
from collections import deque
from random import Random
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.bar_scenarios import load_scenario
from app.services.bar_service import BarController
from app.services.bar_sensing import FREE, UNKNOWN
from app.services.bar_sensing import BLOCKED, cardinal


@pytest.mark.parametrize("radius", [1, 2, 3])
def test_different_radii_recover_and_reach_goal(radius):
    scenario = load_scenario("alley_reachable")
    episode = BarController(scenario.rows, scenario.start, scenario.goal, radius).run()
    assert episode["success"]
    assert episode["recoveries"][0]["invariant_verified"]


def test_every_plan_and_move_uses_only_previously_observed_free_cells():
    scenario = load_scenario("alley_turn")
    episode = BarController(scenario.rows, scenario.start, scenario.goal, 2).run()
    known = [[UNKNOWN] * len(scenario.rows[0]) for _ in scenario.rows]
    previous = scenario.start
    for frame in episode["frames"]:
        for change in frame.get("changes", []):
            cell = change["cell"]
            known[cell["row"]][cell["col"]] = change["state"]
        if frame["event"] in ("plan", "recover_start"):
            assert frame["path"][0] == {"row": previous[0], "col": previous[1]}
            assert all(known[cell["row"]][cell["col"]] == FREE for cell in frame["path"])
        if frame["event"] == "move":
            cell = frame["position"]
            assert known[cell["row"]][cell["col"]] == FREE
            assert abs(cell["row"] - previous[0]) + abs(cell["col"] - previous[1]) == 1
            previous = (cell["row"], cell["col"])


def test_frontier_exhaustion_does_not_cycle_with_unchanged_observations():
    scenario = load_scenario("unreachable")
    controller = BarController(scenario.rows, scenario.start, scenario.goal, 1)
    episode = controller.run()
    assert episode["status"] == "no_reachable_frontier"
    assert episode["metrics"]["executed_distance"] < 2 * len(scenario.rows) * len(scenario.rows[0])


def test_linear_bridge_analysis_matches_edge_removal_oracle():
    random = Random(2718)
    for _ in range(30):
        controller = BarController((".....",) * 5, (0, 0), (4, 4), 1)
        controller.known = [[FREE if random.random() < 0.7 else BLOCKED for _ in range(5)] for _ in range(5)]
        controller.known[0][0] = FREE
        controller.history = [(0, 0)]
        for _ in range(12):
            options = [cell for cell in cardinal(controller.current, 5, 5)
                       if controller.known[cell[0]][cell[1]] == FREE]
            if not options:
                break
            controller.current = random.choice(options)
            controller.history.append(controller.current)
        for r in range(5):
            for c in range(5):
                if controller.known[r][c] == BLOCKED and random.random() < 0.25:
                    controller.known[r][c] = UNKNOWN
        active = set(controller.frontiers())
        expected = None
        seen_edges = set()
        for a, b in zip(controller.history, controller.history[1:]):
            edge = frozenset((a, b))
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            side = {controller.current}
            queue = deque([controller.current])
            while queue:
                cell = queue.popleft()
                for neighbor in cardinal(cell, 5, 5):
                    if (controller.known[neighbor[0]][neighbor[1]] == FREE and neighbor not in side
                            and frozenset((cell, neighbor)) != edge):
                        side.add(neighbor)
                        queue.append(neighbor)
            if (0, 0) in side or active & side:
                continue
            outside, inside = (a, b) if a not in side else (b, a)
            crossings = [i for i, pair in enumerate(zip(controller.history, controller.history[1:]))
                         if pair == (outside, inside)]
            if crossings:
                expected = (outside, controller.history[crossings[-1]:])
                break
        assert controller.exhausted_branch() == expected
