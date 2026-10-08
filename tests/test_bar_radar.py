"""Radar ranking uses observed geometry without erasing uncertain exploration."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import ContinuousPolicy, ExploreNode, path_length, simulate_continuous
from app.services.bar_continuous_geometry import SensorObservation, distance
from app.services.bar_information import wall_key
from app.main import create_app
from app.services.bar_indoor import APARTMENT, OFFICE, generate_indoor
from app.services.bar_labyrinth import BLIND_ALLEY, EXPLORATION, generate_labyrinth


def test_observed_wall_suppresses_closed_frontier_but_keeps_uncertain_target():
    policy = ContinuousPolicy((6, 5), (29, 5), (0, 0, 30, 10), 5, radar_informed=True)
    policy.known_free = box(2, 0, 20, 10)
    policy.observed_walls = {((2, 0), (2, 10)): ((2, 0), (2, 10))}
    parent = ExploreNode((15, 5), 0, [(18, 5)], branch_id=0)
    child = ExploreNode((6, 5), 1, [(4, 5)], branch_id=1, parent_id=0)
    policy.stack = [parent, child]
    policy.history = [(15, 5), (6, 5)]
    policy.scan_positions = [(15, 5), (6, 5)]
    assert policy._frontier_gain((4, 5)) == 0
    assert policy._frontier_gain((18, 5)) > 0
    action, selected = policy.select()
    assert action == "recover" and selected is parent
    assert child.candidates == [(4, 5)]
    route, fallback, entry = policy.recovery_route(parent)
    assert not fallback and path_length(route) == pytest.approx(9)
    assert entry == pytest.approx(9)
    policy.current = parent.position
    policy.complete_recovery(parent)
    assert (4, 5) in parent.candidates  # postponement is not a permanent blacklist
    assert policy.select() == ("explore", (18, 5))
    # If no positive target remains elsewhere, the uncertain target is revisited.
    assert policy.select() == ("explore", (4, 5))


def test_hidden_side_doorway_and_corner_keep_visible_frontiers():
    doorway = ContinuousPolicy((5, 5), (19, 5), (0, 0, 20, 10), 5, radar_informed=True)
    doorway.known_free = unary_union([box(0, 0, 10, 10), box(10, 4, 13, 6)])
    doorway.observed_walls = {
        ((10, 0), (10, 4)): ((10, 0), (10, 4)),
        ((10, 6), (10, 10)): ((10, 6), (10, 10)),
    }
    assert doorway._frontier_gain((9, 5)) > 0

    corner = ContinuousPolicy((4, 2), (19, 9), (0, 0, 20, 12), 5, radar_informed=True)
    corner.known_free = unary_union([box(0, 0, 10, 4), box(8, 4, 12, 10)])
    assert corner._frontier_gain((9, 6)) > 0


def test_wall_only_observation_invalidates_ranking_cache():
    policy = ContinuousPolicy((5, 5), (19, 5), (0, 0, 20, 10), 5, radar_informed=True)
    policy.observe(SensorObservation(box(0, 0, 10, 10), (), ()))
    before = policy._frontier_gain((9, 5))
    assert before > 0
    policy.observe(SensorObservation(box(0, 0, 10, 10), (), (((10, 0), (10, 10)),)))
    assert policy.frames[-1]["new_area"] == 0
    assert policy._frontier_gain((9, 5)) == 0
    assert len(policy.observed_walls) == 1


def test_graph_blocked_target_waits_for_verified_graph_change():
    policy = ContinuousPolicy((1, 1), (9, 9), (0, 0, 10, 10), 2, radar_informed=True)
    policy.known_free = box(0, 0, 5, 3)
    target = (4.3, 1.5)
    policy.stack[0].candidates = [target]
    policy.deferred[policy.candidate_key(target)] = (policy.known_free.area, len(policy.scan_positions))
    assert policy.available(policy.stack[0], include_uncertain=True) == []
    assert policy.stack[0].candidates == [target]
    policy.scan_positions.append((2, 1))
    assert policy.available(policy.stack[0], include_uncertain=True) == [target]


def test_radar_mode_preserves_shortest_verified_return_and_reverse_fallback(monkeypatch):
    policy = ContinuousPolicy((1, 1), (9, 9), (0, 0, 10, 10), 3,
                              radar_informed=True)
    policy.known_free = box(0, 0, 10, 10)
    for point in ((1, 5), (5, 5), (5, 1)):
        policy.move(point, "explore")
        policy.scan_positions.append(point)
    ancestor = ExploreNode((1, 1), 0)
    route, fallback, entry = policy.recovery_route(ancestor)
    assert not fallback and path_length(route) == pytest.approx(4)
    assert entry == pytest.approx(12)
    before = policy.executed
    for point in route[1:]:
        policy.move(point, "retreat")
    policy.finish_recovery(ancestor, fallback, entry, before)
    assert policy.recoveries[0]["invariant_verified"]
    policy.current = (5, 1)
    policy.history = [(1, 1), (5, 1)]
    monkeypatch.setattr(policy, "plan", lambda _target: {"found": False, "route": []})
    reverse, fallback, entry = policy.recovery_route(ancestor)
    assert fallback and reverse == [(5, 1), (1, 1)]
    assert path_length(reverse) == pytest.approx(entry)


def test_audited_branch_anchor_counterfactual_defers_observed_dead_end(monkeypatch):
    """Hold the legacy trajectory fixed until the exact audited decision state."""
    original_observe = ContinuousPolicy.observe
    original_select = ContinuousPolicy.select
    wall_fragments = {}
    decisions = 0
    captured = {}

    class CapturedDecision(Exception):
        pass

    def observe(policy, observation, owner=None):
        for a, b in observation.edges:
            wall_fragments[wall_key(a, b)] = (a, b)
        return original_observe(policy, observation, owner)

    def select(policy):
        nonlocal decisions
        if decisions == 8:
            policy.radar_informed = True
            policy.observed_walls = wall_fragments.copy()
            policy._frontier = None
            policy._prepared_free = None
            policy._frontier_scores.clear()
            captured["position"] = policy.current
            captured["local_candidates"] = len(policy.available(policy.stack[-1]))
            captured["candidate_scores"] = [policy._frontier_gain(candidate)
                                            for candidate in policy.stack[-1].candidates]
            captured["decision"] = original_select(policy)
            raise CapturedDecision
        decisions += 1
        return original_select(policy)

    monkeypatch.setattr(ContinuousPolicy, "observe", observe)
    monkeypatch.setattr(ContinuousPolicy, "select", select)
    with pytest.raises(CapturedDecision):
        simulate_continuous(generate_labyrinth(BLIND_ALLEY).world, 5,
                            prefer_novelty=True, complete_frontier_route=True)
    assert distance(captured["position"], (17.489416236334066, 15.822843066059457)) < 1e-6
    assert captured["local_candidates"] == 0
    assert captured["candidate_scores"] and max(captured["candidate_scores"]) <= 1e-9
    assert captured["decision"][0] == "recover"


def test_api_exposes_optional_decision_trace_without_hidden_map_data():
    response = TestClient(create_app()).post("/api/bar/continuous", json={
        "scenario": "lab_alley", "radius": 5, "debug_exploration": True,
    })
    assert response.status_code == 200
    episode = response.json()
    assert episode["status"] == "goal_reached"
    assert "ranking_time_ms" in episode["metrics"]
    assert any((frame.get("decision", {}).get("estimated_gain") or 0) > 0
               for frame in episode["frames"] if frame["event"] == "plan")
    assert "polygons" not in response.text and "dead_ends" not in response.text


@pytest.mark.parametrize("radius", (5., 7.))
def test_seeded_dead_end_reaches_goal_with_fewer_local_probes(radius):
    world = generate_labyrinth(BLIND_ALLEY).world
    episode = simulate_continuous(world, radius, prefer_novelty=True,
                                  complete_frontier_route=True, radar_informed=True,
                                  include_graph=True)
    assert episode["status"] == "goal_reached"
    assert all(record["invariant_verified"] for record in episode["recoveries"])
    assert all(world.collision_free((frame["from"]["x"], frame["from"]["y"]),
                                    (frame["position"]["x"], frame["position"]["y"]))
               for frame in episode["frames"] if frame["event"] == "move")
    if radius == 5:
        anchor = (17.489416236334066, 15.822843066059457)
        probes = [frame for frame in episode["frames"] if frame["event"] == "move"
                  and frame["phase"] == "explore"
                  and distance((frame["from"]["x"], frame["from"]["y"]), anchor) < .01]
        assert len(probes) < 7  # audited legacy run made seven low-gain probes here


@pytest.mark.parametrize("world_factory,prefer_novelty", (
    (lambda: generate_labyrinth(EXPLORATION).world, True),
    (lambda: generate_indoor(APARTMENT).world, False),
    (lambda: generate_indoor(OFFICE).world, False),
))
def test_other_branches_and_indoor_rooms_remain_reachable(world_factory, prefer_novelty):
    world = world_factory()
    episode = simulate_continuous(world, 5, prefer_novelty=prefer_novelty,
                                  complete_frontier_route=True, radar_informed=True,
                                  trace_hierarchy=True)
    assert episode["status"] == "goal_reached"
    assert all(record["invariant_verified"] for record in episode["recoveries"])
    assert any(frame["event"] == "branch" and frame["status"] == "active"
               for frame in episode["frames"])
