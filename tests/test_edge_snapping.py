"""Coordinate API checks; node-to-node regressions remain in their original suites."""
import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import astar_core
from app.main import create_app
from app.routers.road import get_engine


@pytest.fixture
def road_client(tmp_path):
    points = [(10, 106), (10, 106.002), (10.002, 106.002)]
    edges = []
    for source, target, cost, geometry in (
        (0, 1, 400, [points[0], (10.001, 106.001), points[1]]),
        (1, 0, 500, [points[1], (10.001, 106.001), points[0]]),
        (1, 2, 300, [points[1], points[2]]),
    ):
        edges.append({"from": source, "to": target, "length_m": cost,
                      "osm_key": "0", "osmid": 1, "name": "Test road",
                      "geometry": [(lon,lat) for lat,lon in geometry]})
    graph = dict(schema_version=1,
                 nodes=[dict(id=i, osm_id=i+1, lat=p[0], lon=p[1]) for i, p in enumerate(points)],
                 edges=edges)
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph), encoding="utf-8")
    engine = astar_core.RoadEngine(str(path))
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: engine
    with TestClient(app) as client:
        yield client, engine


def point(lat, lon):
    return dict(lat=lat, lon=lon)


@pytest.mark.parametrize("start,goal,expected", [
    (point(10.0005,106.0005), point(10.001,106.002), 450),  # different roads
    (point(10.0005,106.0005), point(10.0005,106.0015), 200),  # same curved road
    (point(10.001,106.002), point(10.0005,106.0005), None),  # one-way exit
    (point(10.0005,106.0015), point(10.0005,106.0005), 250),  # reverse own cost
    (point(10.001,106.001), point(10.0005,106.0015), 100),  # curved midpoint
    (point(10.001,106.001), point(10.001,106.001), 0),
])
def test_edge_search_compare(road_client, start, goal, expected):
    client, engine = road_client
    before = (engine.node_count, engine.edge_count, astar_core.road_nodes(engine))
    comparison = client.post("/api/road/compare", json=dict(start=start, goal=goal, trace=True))
    assert comparison.status_code == 200, comparison.text
    data = comparison.json()
    assert data["same_optimal_cost"]
    assert data["start"]["requested"] == start
    assert data["goal"]["requested"] == goal
    search = client.post("/api/road/search", json=dict(start=start, goal=goal, trace=True))
    assert search.status_code == 200, search.text
    result = search.json()
    assert result["start"] == data["start"] and result["goal"] == data["goal"]
    assert result["found"] == (expected is not None)
    if expected is not None:
        assert data["cost_difference_m"] == pytest.approx(0, abs=1e-6)
        assert result["route"]["cost_m"] == pytest.approx(expected, abs=1e-6)
        for key, index in (("start", 0), ("goal", -1)):
            snapped = result[key]["snapped"]
            assert result["route"]["geometry"][index] == {k: snapped[k] for k in ("lat", "lon")}
        known = {n["node_id"] for n in before[2] + result["trace_nodes"]}
        assert all(event["state"] in known for event in result["trace"])
        assert all(event["parent"] is None or event["parent"] in known for event in result["trace"])
    assert (engine.node_count, engine.edge_count, astar_core.road_nodes(engine)) == before


def test_snap_projects_onto_curve(road_client):
    client, _ = road_client
    response = client.post("/api/road/snap", json=point(10.0011,106.001))
    assert response.status_code == 200
    snap = response.json()
    assert snap["node_id"] is None
    assert (snap["from_node"], snap["to_node"]) == (0,1)
    assert snap["fraction"] == pytest.approx(.5, abs=1e-8)
    assert snap["lat"] == pytest.approx(10.001)
    assert snap["lon"] == pytest.approx(106.001)
    assert 11 < snap["snap_distance_m"] < 12
