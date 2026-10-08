"""Indoor layouts are simulator fixtures; navigation sees observations only."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point as ShapePoint, box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app
import astar_core
from app.services.bar_continuous import ContinuousPolicy, path_length, simulate_continuous
from app.services.bar_indoor import (
    APARTMENT, OFFICE, CHALLENGE, IndoorConfig, generate_indoor,
)


@pytest.mark.parametrize("layout", ("apartment", "office", "challenge"))
@pytest.mark.parametrize("seed", (0, 1, 41))
def test_seeded_indoor_geometry_and_doorways(layout, seed):
    config = IndoorConfig(layout, seed)
    first, second = generate_indoor(config), generate_indoor(config)
    assert first.world.obstacles.wkb == second.world.obstacles.wkb
    assert first.world.free_space.is_valid
    assert first.world.free_space.geom_type == "Polygon"
    assert len(first.rooms) == 8 and len(first.doors) >= 8
    assert len({room.bounds[2] - room.bounds[0] for room in first.rooms}) > 1
    assert all(first.world.free_space.covers(box(*door.bounds)) for door in first.doors)
    assert first.world.free_space.contains(ShapePoint(first.world.start))
    assert first.world.free_space.contains(ShapePoint(first.world.goal))
    assert all(first.world.obstacles.covers(shape) for shape in first.furniture)


def test_furniture_occludes_sensor_and_policy_has_no_hidden_room_graph():
    layout = generate_indoor(CHALLENGE)
    room = next(room for room in layout.rooms if room.name == "workshop")
    obstacle = next(shape for shape in layout.furniture if room.bounds[0] < shape.centroid.x < room.bounds[2]
                    and room.bounds[1] < shape.centroid.y < room.bounds[3])
    left = (obstacle.bounds[0] - .6, (obstacle.bounds[1] + obstacle.bounds[3])/2)
    right = (obstacle.bounds[2] + .6, left[1])
    assert layout.world.collision_free(left, left)
    assert layout.world.collision_free(right, right)
    assert not layout.world.collision_free(left, right)
    observation = layout.world.sense(left, 5)
    assert observation.region.covers(ShapePoint(left))
    assert not observation.region.covers(ShapePoint(right))
    policy = ContinuousPolicy(layout.world.start, layout.world.goal, layout.world.bounds, 5,
                              trace_hierarchy=True)
    policy.observe(layout.world.sense(layout.world.start, 5))
    assert not hasattr(policy, "rooms") and not hasattr(policy, "doors")
    assert policy.known_free.area < layout.world.free_space.area


@pytest.mark.parametrize("config", (APARTMENT, OFFICE, CHALLENGE))
@pytest.mark.parametrize("radius", (5., 7.))
def test_online_indoor_navigation_returns_to_parent_and_reaches_goal(config, radius):
    world = generate_indoor(config).world
    episode = simulate_continuous(world, radius, prefer_novelty=False,
                                  complete_frontier_route=True, trace_hierarchy=True)
    assert episode["status"] == "goal_reached"
    frames = episode["frames"]
    returns = [frame for frame in frames if frame["event"] == "recover_start"]
    assert returns and all(not frame["fallback"] for frame in returns)
    assert all(item["invariant_verified"] for item in episode["recoveries"])
    assert all(item["retreat_length"] <= item["entry_length"] + 1e-6
               for item in episode["recoveries"])
    assert all(world.collision_free((frame["from"]["x"], frame["from"]["y"]),
                                    (frame["position"]["x"], frame["position"]["y"]))
               for frame in frames if frame["event"] == "move")
    assert any(frame["event"] == "branch" and frame["status"] == "exhausted"
               for frame in frames)
    assert episode["metrics"]["observed_branches"] > 0
    assert episode["metrics"]["observed_free_area"] > 0


def test_challenge_trace_shows_exhaustion_astar_return_and_sibling():
    episode = simulate_continuous(generate_indoor(CHALLENGE).world, 5,
                                  prefer_novelty=False, complete_frontier_route=True,
                                  trace_hierarchy=True, include_graph=True)
    frames = episode["frames"]
    active = [frame["branch_id"] for frame in frames
              if frame["event"] == "branch" and frame["status"] == "active"]
    assert len(active) == len(set(active))
    exhausted = {frame["branch_id"] for frame in frames
                 if frame["event"] == "branch" and frame["status"] == "exhausted"}
    assert exhausted and all(active.count(branch) == 1 for branch in exhausted)
    for index, frame in enumerate(frames):
        if frame["event"] != "recover_start" or frame["fallback"]:
            continue
        end = next(i for i in range(index + 1, len(frames)) if frames[i]["event"] == "recover_end")
        siblings = [item for item in frames[end + 1:] if item["event"] == "branch"
                    and item["status"] == "active" and item["parent_id"] == frame["parent_id"]]
        if siblings:
            assert frame["trigger"] == "exhausted_branch"
            assert path_length([(p["x"], p["y"]) for p in frame["path"]]) <= frame["entry_length"] + 1e-6
            points = [(p["x"], p["y"]) for p in frame["graph_points"]]
            start = (frame["position"]["x"], frame["position"]["y"])
            anchor = (frame["anchor"]["x"], frame["anchor"]["y"])
            dijkstra = astar_core.visibility_search(points, frame["graph_links"],
                                                    points.index(start), points.index(anchor),
                                                    "dijkstra")
            assert dijkstra["found"]
            assert path_length([(p["x"], p["y"]) for p in frame["path"]]) == pytest.approx(dijkstra["cost"])
            assert siblings[0]["branch_id"] != frame["branch_id"]
            break
    else:
        pytest.fail("no explore → exhausted → A* return → sibling trace")


def test_indoor_multidoor_rooms_and_hallway_cycle_are_real_geometry():
    layout = generate_indoor(OFFICE)
    counts = {room.name: sum(door.room == room.name for door in layout.doors)
              for room in layout.rooms}
    assert counts["records"] == 2 and counts["studio"] == 2
    assert counts["break"] == 2 and counts["archive"] == 2
    # The two doors of each side room open onto separate portions of the
    # connected hallway system. These are geometric apertures, not policy links.
    for door in layout.doors:
        center = ((door.bounds[0] + door.bounds[2])/2,
                  (door.bounds[1] + door.bounds[3])/2)
        assert layout.world.collision_free(center, center)


def test_indoor_api_emits_observations_not_hidden_layout_metadata():
    response = TestClient(create_app()).post("/api/bar/continuous", json={
        "scenario": "indoor_seeded", "indoor_layout": "apartment", "seed": 41, "radius": 5,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["indoor_config"] == {"layout": "apartment", "seed": 41}
    assert body["success"] and body["frames"][0]["event"] == "sense"
    assert "rooms" not in response.text and "furniture" not in response.text
    assert "doors" not in response.text and "corridor_bounds" not in response.text


def test_seed_reproduces_motion_and_changes_floor_plan_geometry():
    config = IndoorConfig("apartment", 9)
    world = generate_indoor(config).world
    assert world.obstacles.wkb != generate_indoor(IndoorConfig("apartment", 10)).world.obstacles.wkb
    first = simulate_continuous(world, 5, prefer_novelty=False,
                                complete_frontier_route=True, trace_hierarchy=True)
    second = simulate_continuous(generate_indoor(config).world, 5, prefer_novelty=False,
                                 complete_frontier_route=True, trace_hierarchy=True)
    def motion(episode):
        return [(frame["position"], frame["phase"]) for frame in episode["frames"]
                if frame["event"] == "move"]
    assert motion(first) == motion(second)
    assert first["metrics"]["executed_distance"] == second["metrics"]["executed_distance"]
