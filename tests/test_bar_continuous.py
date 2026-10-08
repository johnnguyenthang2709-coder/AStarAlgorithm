"""Focused continuous-world and C++ A* checks; grid BAR fixtures stay separate."""

import math
import sys
from pathlib import Path

import pytest
from shapely.geometry import Point as ShapePoint, box
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import astar_core
from app.services.bar_continuous import ContinuousPolicy, ExploreNode, path_length, simulate_continuous
from app.services.bar_continuous_geometry import ContinuousWorld, SensorObservation, distance, segment_in_region
from app.main import create_app


def room(obstacles=(), start=(2.0, 5.0), goal=(9.0, 5.0)):
    return ContinuousWorld((0.0, 0.0, 12.0, 10.0), tuple(obstacles), start, goal)


def test_arbitrary_angle_euclidean_graph_and_dijkstra_agree():
    points = [(0., 0.), (3., 4.), (6., 0.), (7., 2.)]
    links = [(0, 1), (1, 2), (2, 3)]
    astar = astar_core.visibility_search(points, links, 0, 3, "astar")
    dijkstra = astar_core.visibility_search(points, links, 0, 3, "dijkstra")
    assert astar["found"] and astar["path"] == [0, 1, 2, 3]
    assert astar["cost"] == pytest.approx(10 + math.sqrt(5))
    assert astar["cost"] == pytest.approx(dijkstra["cost"])


def test_continuous_api_exposes_observations_without_ground_truth_polygons():
    response = TestClient(create_app()).post("/api/bar/continuous",
                                           json={"scenario": "irregular_u", "radius": 6})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "continuous" and body["sensor_fov_degrees"] == 360
    assert body["robot_radius"] == 0 and body["success"]
    assert body["frames"][0]["event"] == "sense"
    assert "region" in body["frames"][0]
    assert "polygons" not in response.text


def test_polygon_collision_narrow_passage_boundary_and_concavity():
    world = room((
        ((4., 0.), (5., 0.), (5., 4.), (4., 4.)),
        ((4., 6.), (5., 6.), (5., 10.), (4., 10.)),
    ))
    assert world.collision_free((2., 5.), (9., 5.))
    assert not world.collision_free((2., 3.), (9., 3.))
    assert not world.collision_free((2., 5.), (13., 5.))
    assert not world.collision_free((2., 4.), (9., 4.))
    concave = room((
        ((4., 2.), (8., 2.), (8., 3.), (5., 3.), (5., 7.), (4., 7.)),
    ))
    assert not concave.collision_free((3., 5.), (6., 5.))
    assert concave.collision_free((6., 5.), (7., 5.))


def test_360_degree_sensing_occludes_hidden_geometry_and_policy_has_no_world():
    front = ((4., 1.), (5., 1.), (5., 9.), (4., 9.))
    hidden = ((7., 3.), (8., 3.), (8., 4.), (7., 4.))
    a = room((front,))
    b = room((front, hidden))
    seen_a, seen_b = a.sense(a.start, 7), b.sense(b.start, 7)
    assert seen_a.region.symmetric_difference(seen_b.region).area == pytest.approx(0, abs=1e-8)
    assert seen_a.candidates == seen_b.candidates
    assert seen_a.edges == seen_b.edges
    assert seen_a.region.covers(ShapePoint(2, 8))
    assert not seen_a.region.covers(ShapePoint(7, 5))
    policy = ContinuousPolicy(a.start, a.goal, a.bounds, 7)
    policy.observe(seen_a)
    assert not hasattr(policy, "polygons")
    assert not segment_in_region(policy.known_free, a.start, (7., 5.))


def test_a_star_return_shortens_executed_entry_and_fallback_reverses_it(monkeypatch):
    policy = ContinuousPolicy((1., 1.), (9., 9.), (0., 0., 10., 10.), 3)
    policy.known_free = box(0, 0, 10, 10)
    for point in ((1., 5.), (5., 5.), (5., 1.)):
        policy.move(point, "explore")
        policy.scan_positions.append(point)
    ancestor = ExploreNode((1., 1.), 0)
    route, fallback, entry = policy.recovery_route(ancestor)
    assert not fallback
    assert route == [(5., 1.), (1., 1.)]
    assert path_length(route) < entry
    before = policy.executed
    for point in route[1:]:
        policy.move(point, "retreat")
    policy.finish_recovery(ancestor, fallback, entry, before)
    assert policy.recoveries[0]["invariant_verified"]
    assert policy.recoveries[0]["retreat_length"] == pytest.approx(4)

    other = ContinuousPolicy((1., 1.), (9., 9.), (0., 0., 10., 10.), 3)
    other.known_free = box(0, 0, 10, 10)
    other.move((2., 2.), "explore")
    monkeypatch.setattr(other, "plan", lambda _target: {"found": False, "route": []})
    reverse, used_fallback, recorded = other.recovery_route(ExploreNode((1., 1.), 0))
    assert used_fallback and reverse == [(2., 2.), (1., 1.)]
    assert path_length(reverse) == pytest.approx(recorded)

    monkeypatch.setattr(other, "plan", lambda _target: {
        "found": True, "route": [(2., 2.), (9., 9.), (1., 1.)],
        "graph_points": [], "graph_links": [],
    })
    reverse, used_fallback, recorded = other.recovery_route(ExploreNode((1., 1.), 0))
    assert used_fallback and reverse == [(2., 2.), (1., 1.)]
    assert path_length(reverse) == pytest.approx(recorded)


def test_failed_target_is_deferred_while_parent_sibling_survives():
    policy = ContinuousPolicy((1., 1.), (9., 9.), (0., 0., 10., 10.), 2)
    policy.known_free = box(0, 0, 5, 3)
    root = policy.stack[0]
    child = ExploreNode((3., 1.), 1, [(4.3, 1.5)])
    root.candidates = [(1., 2.7)]
    policy.stack.append(child)
    policy.current = child.position
    policy.scan_positions.append(child.position)
    action, target = policy.select()
    assert (action, target) == ("explore", (4.3, 1.5))
    policy.failed_plan(action, target, {"route": [], "nodes": 2, "edges": 0})
    assert policy.frames[-1]["status"] == "unreachable_target"
    assert policy.candidate_key(target) not in policy.tried
    assert policy.select() == ("recover", root)
    assert policy.recovery_trigger(root) == "graph_blocked_target"
    policy.complete_recovery(root)
    assert root.candidates == [(1., 2.7), (4.3, 1.5)]
    assert policy.select() == ("explore", (1., 2.7))
    policy.scan_positions.append((2., 2.))  # a verified waypoint can change the graph without adding area
    assert policy.available(root) == [(4.3, 1.5)]


def test_retreat_observations_belong_to_surviving_ancestor_and_goal_failure_waits():
    policy = ContinuousPolicy((1., 1.), (4., 1.), (0., 0., 10., 10.), 2)
    root = policy.stack[0]
    child = ExploreNode((3., 1.), 1)
    policy.stack.append(child)
    policy.current = child.position
    policy.known_free = box(0, 0, 2, 2)
    policy.observe(SensorObservation(box(0, 0, 5, 3), ((4.3, 1.5),), ()), owner=root)
    assert root.candidates == [(4.3, 1.5)] and not child.candidates
    assert policy.select() == ("goal", (4., 1.))
    policy.failed_plan("goal", (4., 1.), {"route": [], "nodes": 2, "edges": 0})
    assert policy.select() == ("recover", root)
    policy.known_free = policy.known_free.union(box(5, 0, 6, 3))
    assert policy.select() == ("goal", (4., 1.))


def test_nearest_viable_ancestor_is_chosen_and_empty_parent_can_be_skipped():
    policy = ContinuousPolicy((1., 1.), (9., 9.), (0., 0., 10., 10.), 2)
    policy.known_free = box(0, 0, 5, 3)
    root = policy.stack[0]
    root.candidates = [(1., 2.7)]
    parent = ExploreNode((2., 1.), 1, [(4.3, 1.5)])
    leaf = ExploreNode((3., 1.), 2)
    policy.stack.extend((parent, leaf))
    policy.current = leaf.position
    policy.scan_positions.extend((parent.position, leaf.position))
    assert policy.select() == ("recover", parent)
    assert policy.recovery_trigger(parent) == "exhausted_branch"
    parent.candidates.clear()
    assert policy.select() == ("recover", root)


@pytest.mark.parametrize("radius", [4., 6.])
def test_online_continuous_episode_is_deterministic_and_recoveries_are_bounded(radius):
    world = ContinuousWorld.load("irregular_u")
    episode = simulate_continuous(world, radius)
    assert episode["status"] == "goal_reached"
    assert episode["metrics"]["replanning_count"] > 0
    assert any(frame["event"] == "recover_start" and not frame["fallback"]
               for frame in episode["frames"])
    assert episode["recoveries"]
    assert all(item["invariant_verified"] and item["retreat_length"] <= item["entry_length"] + 1e-6
               for item in episode["recoveries"])
    moves = [frame for frame in episode["frames"] if frame["event"] == "move"]
    assert sum(frame["distance"] for frame in moves) == pytest.approx(episode["metrics"]["executed_distance"])
    assert any(abs(math.sin(frame["heading"])) > 0.1 and abs(math.cos(frame["heading"])) > 0.1
               for frame in moves)
    assert distance(tuple(moves[-1]["position"].values()), world.goal) < 1e-6
