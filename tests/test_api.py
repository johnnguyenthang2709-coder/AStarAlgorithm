import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import create_app

GRAPH = json.loads((ROOT / "data/road/graph.json").read_text(encoding="utf-8"))
POINT0 = {"lat": GRAPH["nodes"][0]["lat"], "lon": GRAPH["nodes"][0]["lon"]}
POINT597 = {"lat": GRAPH["nodes"][597]["lat"], "lon": GRAPH["nodes"][597]["lon"]}


def test_health_and_openapi():
    app = create_app()
    with TestClient(app) as client:
        engine_id = id(app.state.road_engine)
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "road_graph_loaded": True,
                                 "road_nodes": 2986, "road_edges": 7152}
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        for path in ("/api/health", "/api/road/snap", "/api/road/nodes", "/api/road/geometry", "/api/road/search",
                     "/api/road/compare", "/api/grid/search", "/api/grid/replan"):
            assert path in schema["paths"]
        assert id(app.state.road_engine) == engine_id
        nodes = client.get("/api/road/nodes")
        assert nodes.status_code == 200
        assert len(nodes.json()) == 2986
        assert nodes.json()[0]["node_id"] == 0
        geometry = client.get("/api/road/geometry")
        assert geometry.status_code == 200
        assert geometry.headers["content-type"].startswith("application/geo+json")
        assert len(geometry.json()["features"]) == 7152
        assert geometry.content == (ROOT / "data/road/roads.geojson").read_bytes()
        context = client.get("/api/road/context")
        assert context.status_code == 200
        assert context.content == (ROOT / "data/road/context.geojson").read_bytes()
        preflight = client.options("/api/grid/search", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_degraded_road_graph():
    with TestClient(create_app(ROOT / "tests/missing.json")) as client:
        health = client.get("/api/health")
        assert health.status_code == 503
        assert health.json()["status"] == "degraded"
        assert client.post("/api/road/snap", json=POINT0).status_code == 503
        assert client.get("/api/road/geometry").status_code == 503
        assert client.post("/api/grid/search", json={"grid": [[0]], "start": {"row": 0, "col": 0},
                                                     "goal": {"row": 0, "col": 0}}).status_code == 200


def test_road_bundle_mismatch_degrades_road_only():
    with TemporaryDirectory() as directory:
        bundle = Path(directory)
        for name in ("graph.json", "roads.geojson", "metadata.json"):
            shutil.copyfile(ROOT / "data/road" / name, bundle / name)
        with (bundle / "roads.geojson").open("ab") as output:
            output.write(b" ")
        with TestClient(create_app(bundle / "graph.json")) as client:
            assert client.get("/api/health").status_code == 503
            assert client.get("/api/road/geometry").status_code == 503
            assert client.post("/api/grid/search", json={"grid": [[0]],
                "start": {"row": 0, "col": 0}, "goal": {"row": 0, "col": 0}}).status_code == 200


def test_context_mismatch_is_not_silently_served():
    with TemporaryDirectory() as directory:
        bundle = Path(directory)
        for name in ("graph.json", "roads.geojson", "metadata.json", "context.geojson"):
            shutil.copyfile(ROOT / "data/road" / name, bundle / name)
        with (bundle / "context.geojson").open("ab") as output:
            output.write(b" ")
        with TestClient(create_app(bundle / "graph.json")) as client:
            assert client.get("/api/road/context").status_code == 503
            assert client.post("/api/grid/search", json={"grid": [[0]],
                "start": {"row": 0, "col": 0}, "goal": {"row": 0, "col": 0}}).status_code == 200


def test_road_snap_search_compare_and_validation():
    with TestClient(create_app()) as client:
        snap = client.post("/api/road/snap", json=POINT0)
        assert snap.status_code == 200
        assert snap.json()["node_id"] == 0
        assert snap.json()["osm_id"] == GRAPH["nodes"][0]["osm_id"]
        body = {"start": POINT0, "goal": POINT597}
        a = client.post("/api/road/search", json={**body, "algorithm": "astar", "trace": True})
        d = client.post("/api/road/search", json={**body, "algorithm": "dijkstra", "trace": False})
        assert a.status_code == d.status_code == 200
        aa, dd = a.json(), d.json()
        assert aa["found"] and dd["found"]
        assert aa["start"]["requested"] == POINT0
        assert aa["start"]["snapped"]["node_id"] == 0
        assert aa["route"]["cost_m"] == pytest.approx(dd["route"]["cost_m"])
        assert aa["route"]["cost_m"] == pytest.approx(3925.0937336951697)
        assert len(aa["route"]["edge_path"]) + 1 == len(aa["route"]["node_path"])
        assert aa["trace"] and dd["trace"] == []
        assert isinstance(aa["trace"][0]["state"], int)
        comparison = client.post("/api/road/compare", json=body)
        assert comparison.status_code == 200
        assert comparison.json()["same_optimal_cost"] is True
        assert comparison.json()["cost_difference_m"] == pytest.approx(0)
        same = client.post("/api/road/search", json={"start": POINT0, "goal": POINT0})
        assert same.status_code == 200
        assert same.json()["route"]["node_path"] == [0]
        assert same.json()["route"]["cost_m"] == 0
        point1 = {"lat": GRAPH["nodes"][1]["lat"], "lon": GRAPH["nodes"][1]["lon"]}
        unreachable = client.post("/api/road/search", json={"start": point1, "goal": POINT0})
        assert unreachable.status_code == 200
        assert unreachable.json()["found"] is False
        assert unreachable.json()["route"] is None
        assert client.post("/api/road/snap", json={"lat": 91, "lon": 0}).status_code == 422
        assert client.post("/api/road/search", json={**body, "algorithm": "random"}).status_code == 422


def test_grid_modes_validation_trace_and_replan():
    with TestClient(create_app()) as client:
        body = {"grid": [[0, 0], [0, 0]], "start": {"row": 0, "col": 0},
                "goal": {"row": 1, "col": 1}}
        four = client.post("/api/grid/search", json={**body, "movement": 4, "algorithm": "astar"})
        eight = client.post("/api/grid/search", json={**body, "movement": 8,
                                                      "algorithm": "dijkstra", "trace": True})
        assert four.status_code == eight.status_code == 200
        assert four.json()["cost"] == 2
        assert four.json()["trace"] == []
        assert eight.json()["cost"] == 1.5
        assert eight.json()["trace"][0]["state"] == {"row": 0, "col": 0}
        no_path = client.post("/api/grid/search", json={**body, "grid": [[0, 1], [1, 0]]})
        assert no_path.status_code == 200
        assert no_path.json()["found"] is False and no_path.json()["path"] == []
        same = client.post("/api/grid/search", json={**body, "goal": body["start"]})
        assert same.json()["path"] == [{"row": 0, "col": 0}]
        for bad in ({**body, "grid": [[1, 0], [0, 0]]},
                    {**body, "grid": [[0, 0], [0, 1]]},
                    {**body, "grid": [[0], [0, 0]]},
                    {**body, "grid": []},
                    {**body, "grid": [[0, 2], [0, 0]]},
                    {**body, "grid": [[False, 0], [0, 0]]},
                    {**body, "movement": 6},
                    {**body, "algorithm": "other"},
                    {**body, "goal": {"row": 4, "col": 0}}):
            assert client.post("/api/grid/search", json=bad).status_code == 422
        replan = client.post("/api/grid/replan", json={
            "grid": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            "current": {"row": 0, "col": 0}, "goal": {"row": 2, "col": 2},
            "new_obstacles": [{"row": 1, "col": 1}], "movement": 8,
        })
        assert replan.status_code == 200
        assert {"row": 1, "col": 1} not in replan.json()["path"]
