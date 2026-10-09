"""Incremental wall mask must preserve the authoritative full frontier."""

import sys
from pathlib import Path

import pytest
from shapely.errors import GEOSException
from shapely.geometry import box
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app.services.bar_continuous as continuous
from app.services.bar_continuous import ContinuousPolicy, simulate_continuous
from app.services.bar_continuous_geometry import SensorObservation
from app.services.bar_continuous_geometry import RAY_MARGIN
from app.services.bar_indoor import APARTMENT, OFFICE, CHALLENGE, generate_indoor
from app.services.bar_information import possible_frontier, visible_frontier_gain
from app.services.bar_labyrinth import BLIND_ALLEY, COMPLEX, EXPLORATION, generate_labyrinth


def test_repeated_observation_doorway_and_wall_only_change():
    policy = ContinuousPolicy((4, 4), (18, 4), (0, 0, 20, 10), 5, radar_informed=True)
    first = SensorObservation(box(0, 0, 8, 8), ((7, 4),),
                              (((8, 0), (8, 3)), ((8, 5), (8, 8))))
    policy.observe(first)
    initial = policy._frontier_gain((7, 4))
    assert initial > 0
    mask, frontier = policy._wall_mask, policy._frontier
    policy.observe(first)
    assert policy._wall_mask is mask and policy._frontier is frontier
    assert policy._frontier_gain((7, 4)) == initial

    policy.observe(SensorObservation(box(8, 3, 12, 5), (), ()))
    assert policy._frontier is None and policy._wall_mask is mask
    new_free_score = policy._frontier_gain((7, 4))
    assert new_free_score != initial
    policy.observe(SensorObservation(box(8, 3, 12, 5), (), (((12, 3), (12, 5)),)))
    assert policy._frontier is None and policy._wall_mask is not mask
    policy._frontier_gain((7, 4))
    authoritative = possible_frontier(policy.known_free, policy.border,
                                       list(policy.observed_walls.values()))
    assert policy._frontier.hausdorff_distance(authoritative) < 1e-8


def test_restored_wall_state_uses_full_reconstruction():
    policy = ContinuousPolicy((4, 4), (18, 4), (0, 0, 20, 10), 5, radar_informed=True)
    policy.observe(SensorObservation(box(0, 0, 8, 8), (), ()))
    policy.observed_walls[((8, 0), (8, 8))] = ((8, 0), (8, 8))
    actual = policy._frontier_gain((7, 4))
    assert policy._wall_mask is None
    authoritative = possible_frontier(policy.known_free, policy.border,
                                       list(policy.observed_walls.values()))
    expected = visible_frontier_gain((7, 4), 5,
                                     prep(policy.known_free.buffer(2 * RAY_MARGIN)), authoritative)
    assert actual == pytest.approx(expected, abs=1e-8)


def test_failed_incremental_mask_update_falls_back_to_full(monkeypatch):
    policy = ContinuousPolicy((4, 4), (18, 4), (0, 0, 20, 10), 5, radar_informed=True)

    def fail(_mask, _walls):
        raise GEOSException("synthetic union failure")

    monkeypatch.setattr(continuous, "extend_wall_mask", fail)
    policy.observe(SensorObservation(box(0, 0, 8, 8), (), (((8, 0), (8, 8)),)))
    assert policy._wall_mask is None
    actual = policy._frontier_gain((7, 4))
    expected_frontier = possible_frontier(policy.known_free, policy.border,
                                          list(policy.observed_walls.values()))
    assert policy._frontier.hausdorff_distance(expected_frontier) < 1e-8
    assert actual == pytest.approx(visible_frontier_gain(
        (7, 4), 5, prep(policy.known_free.buffer(2 * RAY_MARGIN)), expected_frontier), abs=1e-8)


def run_episode(world, radius, novelty, monkeypatch, reference):
    snapshots = []
    original_select = continuous.ContinuousPolicy.select
    original_frontier = continuous.possible_frontier
    original_gain = continuous.visible_frontier_gain
    expected_frontier = None

    def select(policy):
        decision = original_select(policy)
        snapshots.append((decision[0] if decision else None,
                          decision[1].position if decision and decision[0] == "recover"
                          else decision[1] if decision else None,
                          policy.last_decision.get("eligible"),
                          tuple((node.position, node.branch_id, node.parent_id,
                                 tuple(node.candidates)) for node in policy.stack),
                          tuple(sorted(policy.radar_pending)),
                          tuple(sorted(policy.deferred))))
        return decision

    def full(known_free, border, walls, wall_mask=None):
        return original_frontier(known_free, border, walls)

    def compare_frontier(known_free, border, walls, wall_mask=None):
        nonlocal expected_frontier
        actual = original_frontier(known_free, border, walls, wall_mask)
        expected_frontier = original_frontier(known_free, border, walls)
        assert actual.is_empty == expected_frontier.is_empty
        if not actual.is_empty:
            assert actual.hausdorff_distance(expected_frontier) < 1e-8
        return actual

    def compare_gain(point, radius, prepared_free, frontier):
        actual = original_gain(point, radius, prepared_free, frontier)
        expected = original_gain(point, radius, prepared_free, expected_frontier)
        assert actual == pytest.approx(expected, abs=1e-8)
        assert (actual <= 1e-9) == (expected <= 1e-9)
        return actual

    with monkeypatch.context() as patch:
        patch.setattr(continuous.ContinuousPolicy, "select", select)
        patch.setattr(continuous, "possible_frontier",
                      full if reference else compare_frontier)
        if not reference:
            patch.setattr(continuous, "visible_frontier_gain", compare_gain)
        episode = simulate_continuous(world, radius, prefer_novelty=novelty,
                                      complete_frontier_route=True,
                                      radar_informed=True)
    return episode, snapshots


@pytest.mark.parametrize("make_world,radius,novelty", (
    (lambda: generate_labyrinth(BLIND_ALLEY).world, 5, True),
    (lambda: generate_labyrinth(COMPLEX).world, 7, True),
    (lambda: generate_labyrinth(EXPLORATION).world, 5, True),
    (lambda: generate_indoor(APARTMENT).world, 5, False),
    (lambda: generate_indoor(APARTMENT).world, 7, False),
    (lambda: generate_indoor(OFFICE).world, 5, False),
    (lambda: generate_indoor(OFFICE).world, 7, False),
    (lambda: generate_indoor(CHALLENGE).world, 5, False),
))
def test_complete_decisions_match_full_frontier(make_world, radius, novelty, monkeypatch):
    expected, reference_states = run_episode(make_world(), radius, novelty, monkeypatch, True)
    actual, cached_states = run_episode(make_world(), radius, novelty, monkeypatch, False)
    assert actual["status"] == expected["status"] == "goal_reached"
    assert cached_states == reference_states
    assert actual["metrics"]["executed_distance"] == expected["metrics"]["executed_distance"]
    assert actual["frames"] == expected["frames"]
    for field in ("replanning_count", "astar_expanded_nodes", "turn_count"):
        assert actual["metrics"][field] == expected["metrics"][field]
    assert actual["recoveries"] == expected["recoveries"]
