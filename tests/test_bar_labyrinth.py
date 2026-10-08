"""Seeded irregular corridor geometry and continuous online navigation."""

import math
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point as ShapePoint

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app
from app.services.bar_continuous import ContinuousPolicy, simulate_continuous
from app.services.bar_labyrinth import (
    BLIND_ALLEY, COMPLEX, EXPLORATION, LabyrinthConfig, generate_labyrinth,
)
from app.services.bar_maze import canonical


@pytest.mark.parametrize("config", [EXPLORATION, BLIND_ALLEY, COMPLEX])
def test_reproducible_connected_valid_geometry_without_shortcuts(config):
    first, second = generate_labyrinth(config), generate_labyrinth(config)
    assert first.world.obstacles.wkb == second.world.obstacles.wkb
    assert first.world.start == second.world.start
    assert first.world.goal == second.world.goal
    assert first.open_links == second.open_links
    assert first.world.obstacles.is_valid and first.world.free_space.is_valid
    assert first.world.free_space.geom_type == "Polygon"
    assert first.world.free_space.area > 0
    assert len(first.dead_ends) >= config.trap_count
    assert all(first.world.free_space.contains(ShapePoint(point))
               for point in (first.world.start, first.world.goal))
    assert any(abs(b[0]-a[0]) > .05 and abs(b[1]-a[1]) > .05
               for path in first.centerlines for a, b in zip(path, path[1:]))
    for path in first.centerlines:
        assert all(first.world.collision_free(a, b) for a, b in zip(path, path[1:]))
        for point in path:
            assert first.world.obstacles.distance(ShapePoint(point)) >= config.corridor_width * .40
    for row in range(config.size):
        for col in range(config.size):
            for neighbor in ((row + 1, col), (row, col + 1)):
                if max(neighbor) >= config.size or canonical((row, col), neighbor) in first.open_links:
                    continue
                assert not first.world.collision_free(first.centers[(row, col)], first.centers[neighbor])


def test_angled_walls_occlude_sensor_and_policy_receives_no_hidden_geometry():
    layout = generate_labyrinth(EXPLORATION)
    observation = layout.world.sense(layout.world.start, 5)
    policy = ContinuousPolicy(layout.world.start, layout.world.goal, layout.world.bounds, 5)
    policy.observe(observation)
    assert not hasattr(policy, "world") and not hasattr(policy, "polygons")
    assert policy.known_free.area < layout.world.free_space.area
    assert observation.region.intersection(layout.world.obstacles).area < 1e-8
    assert observation.edges
    assert all(layout.world.obstacles.distance(LineString(edge)) < .003
               for edge in observation.edges)
    assert any(abs(b[0]-a[0]) > .01 and abs(b[1]-a[1]) > .01
               for a, b in observation.edges)


@pytest.mark.parametrize("radius", [5., 7.])
def test_online_navigation_is_continuous_collision_free_and_recovery_bounded(radius):
    world = generate_labyrinth(BLIND_ALLEY).world
    episode = simulate_continuous(world, radius, prefer_novelty=True,
                                  complete_frontier_route=True)
    assert episode["success"] and episode["status"] == "goal_reached"
    assert episode["recoveries"]
    assert any(not recovery["fallback"] for recovery in episode["recoveries"])
    assert all(recovery["invariant_verified"] and
               recovery["retreat_length"] <= recovery["entry_length"] + 1e-6
               for recovery in episode["recoveries"])
    moves = [frame for frame in episode["frames"] if frame["event"] == "move"]
    assert all(world.collision_free(tuple(frame["from"].values()),
                                    tuple(frame["position"].values())) for frame in moves)
    assert episode["metrics"]["executed_distance"] == pytest.approx(
        sum(frame["distance"] for frame in moves))
    assert any(abs(math.sin(frame["heading"])) > .1 and abs(math.cos(frame["heading"])) > .1
               for frame in moves)


def test_loop_heavy_and_dead_end_heavy_configs_and_explicit_invalid_width():
    for rate, traps in ((.30, 2), (.03, 4)):
        layout = generate_labyrinth(LabyrinthConfig(
            seed=23, size=5, loop_rate=rate, dead_end_rate=.8,
            trap_count=traps, irregularity=.9))
        assert layout.world.free_space.geom_type == "Polygon"
        assert len(layout.dead_ends) >= traps
    with pytest.raises(ValueError, match="corridor width"):
        generate_labyrinth(LabyrinthConfig(corridor_width=3.5))


@pytest.mark.parametrize("seed", range(10))
def test_seed_workflow_keeps_geometry_connected_without_policy_filtering(seed):
    layout = generate_labyrinth(LabyrinthConfig(seed=seed, size=5,
                                                corridor_width=2.4,
                                                irregularity=.75))
    assert layout.world.free_space.geom_type == "Polygon"
    assert layout.world.obstacles.is_valid
    assert layout.world.collision_free(layout.world.start, layout.world.start)


def test_api_exposes_observations_without_ground_truth_polygons():
    response = TestClient(create_app()).post("/api/bar/continuous", json={
        "scenario": "lab_seeded", "seed": 23, "size": 5,
        "corridor_width": 2.4, "irregularity": .72, "radius": 5,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["maze_config"]["irregularity"] == .72
    assert body["frames"][0]["event"] == "sense"
    assert "polygons" not in response.text and "centerlines" not in response.text
