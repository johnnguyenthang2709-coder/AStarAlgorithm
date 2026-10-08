"""Topology, geometry, observation isolation, and online Maze 3 regression."""

import math
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app
from app.services.bar_continuous import ContinuousPolicy, simulate_continuous
from app.services.bar_continuous_geometry import ContinuousWorld
from app.services.bar_maze import HARD, SHOWCASE, MazeConfig, canonical, generate_maze


@pytest.mark.parametrize("seed", [0, 17, 23, 431])
def test_seeded_maze_is_reproducible_connected_and_geometrically_faithful(seed):
    config = MazeConfig(seed=seed, size=5, corridor_width=2.0, loop_rate=.15,
                        dead_end_rate=.7, trap_count=2)
    one, two = generate_maze(config), generate_maze(config)
    assert one.open_links == two.open_links
    assert one.world.polygons == two.world.polygons
    assert one.world.start == two.world.start and one.world.goal == two.world.goal
    assert one.loop_count >= 1 and len(one.dead_ends) >= 2
    assert len(one.open_links) >= config.size**2  # tree plus at least one cycle
    assert abs(one.start_cell[0]-one.goal_cell[0]) + abs(one.start_cell[1]-one.goal_cell[1]) >= config.size
    seen = {one.start_cell}
    frontier = [one.start_cell]
    for cell in frontier:
        for edge in one.open_links:
            other = edge[1] if edge[0] == cell else edge[0] if edge[1] == cell else None
            if other is not None and other not in seen:
                seen.add(other)
                frontier.append(other)
    assert len(seen) == config.size**2
    assert all(shape.is_valid for shape in one.world.obstacles.geoms) if one.world.obstacles.geom_type == "MultiPolygon" else one.world.obstacles.is_valid
    pieces = one.world.obstacles.geoms if one.world.obstacles.geom_type == "MultiPolygon" else (one.world.obstacles,)
    assert any(piece.convex_hull.area > piece.area + 1e-6 for piece in pieces)


def test_wall_width_and_closed_doorways_block_actual_segments():
    layout = generate_maze(MazeConfig(seed=17, size=4, corridor_width=1.2,
                                      loop_rate=.1, trap_count=2))
    world = layout.world
    pitch = 5
    for row in range(4):
        for col in range(4):
            for other in ((row+1, col), (row, col+1)):
                if max(other) >= 4:
                    continue
                a, b = ((col+.5)*pitch, (row+.5)*pitch), ((other[1]+.5)*pitch, (other[0]+.5)*pitch)
                assert world.collision_free(a, b) == (canonical((row, col), other) in layout.open_links)
    assert not world.collision_free((0.1, 0.1), (-1., 0.1))


def test_maze_sensor_hides_unseen_walls_and_debug_edges_are_verified():
    layout = generate_maze(SHOWCASE)
    policy = ContinuousPolicy(layout.world.start, layout.world.goal, layout.world.bounds, 5,
                              prefer_novelty=True, include_graph=True)
    observation = layout.world.sense(layout.world.start, 5)
    policy.observe(observation)
    assert not hasattr(policy, "world") and not hasattr(policy, "polygons")
    assert policy.known_free.area < layout.world.free_space.area
    assert observation.region.intersection(layout.world.obstacles).area < 1e-8
    target = observation.candidates[0]
    plan = policy.plan(target)
    policy.plan_frame(target, plan, "explore")
    frame = policy.frames[-1]
    assert frame["graph_links"]
    assert all(layout.world.collision_free(tuple(frame["graph_points"][a].values()),
                                           tuple(frame["graph_points"][b].values()))
               for a, b in frame["graph_links"])


@pytest.mark.parametrize("radius", [5., 7.])
def test_showcase_recovery_and_executed_distance(radius):
    episode = simulate_continuous(generate_maze(SHOWCASE).world, radius, 250,
                                  prefer_novelty=True, complete_frontier_route=True)
    assert episode["metrics"]["replanning_count"] > 0
    assert episode["recoveries"]
    assert all(record["invariant_verified"] and record["retreat_length"] <= record["entry_length"] + 1e-6
               for record in episode["recoveries"])
    assert episode["metrics"]["executed_distance"] == pytest.approx(sum(
        frame["distance"] for frame in episode["frames"] if frame["event"] == "move"))
    assert any(abs(math.sin(frame["heading"])) > .1 and abs(math.cos(frame["heading"])) > .1
               for frame in episode["frames"] if frame["event"] == "move")


def test_api_seeded_parameters_and_hidden_ground_truth():
    response = TestClient(create_app()).post("/api/bar/continuous", json={
        "scenario": "maze_seeded", "seed": 23, "size": 4, "corridor_width": 2.5,
        "loop_rate": .15, "dead_end_rate": .7, "trap_count": 2, "difficulty": "normal",
        "radius": 7, "debug_graph": False,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["maze_config"]["seed"] == 23
    assert body["mode"] == "continuous" and body["robot_radius"] == 0
    assert "polygons" not in response.text and "graph_links" not in response.text
    assert body["frames"][0]["event"] == "sense"


def test_invalid_topology_request_is_reported_instead_of_policy_filtered():
    with pytest.raises(ValueError):
        generate_maze(MazeConfig(seed=1, size=4, trap_count=8, loop_rate=.35))


def test_custom_endpoints_and_disconnected_geometry():
    layout = generate_maze(MazeConfig(seed=17, size=5, start_cell=(4, 0), goal_cell=(0, 4)))
    assert layout.world.start == (2.5, 22.5)
    assert layout.world.goal == (22.5, 2.5)
    with pytest.raises(ValueError, match="meaningfully separated"):
        generate_maze(MazeConfig(size=5, start_cell=(0, 0), goal_cell=(0, 1)))
    separated = ContinuousWorld((0., 0., 10., 10.),
                                (((4., 0.), (6., 0.), (6., 10.), (4., 10.)),),
                                (2., 5.), (8., 5.))
    assert not separated.collision_free(separated.start, separated.goal)
    episode = simulate_continuous(separated, 3, 30, prefer_novelty=True,
                                  complete_frontier_route=True)
    assert not episode["success"] and episode["status"] in ("no_reachable_frontier", "step_limit")
