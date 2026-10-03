from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import astar_core


def test_binding_import_and_road_graph():
    engine = astar_core.RoadEngine(str(ROOT / "data/road/graph.json"))
    assert engine.node_count == 2986
    assert engine.edge_count == 7152
    snapped = astar_core.road_snap(engine, 10.7729, 106.6592)
    assert isinstance(snapped["node_id"], int)
    assert snapped["snap_distance_m"] >= 0
    nodes = astar_core.road_nodes(engine)
    assert len(nodes) == engine.node_count
    assert nodes[0]["node_id"] == 0
    result = astar_core.road_search(engine, 0, 597, "astar", False)
    assert result["found"] is True
    assert result["trace"] == []
    traced = astar_core.road_search(engine, 0, 597, "astar", True)
    assert traced["trace"]
    for event in traced["trace"][::max(1, len(traced["trace"]) // 20)]:
        assert event["f"] == pytest.approx(event["g"] + event["h"])
        assert isinstance(event["state"], int)
        assert event["parent"] is None or isinstance(event["parent"], int)
    assert result["route"]["node_path"][0] == 0
    assert result["route"]["node_path"][-1] == 597
    assert result["route"]["cost_m"] == pytest.approx(3925.0937336951697)
    assert len(result["route"]["edge_path"]) + 1 == len(result["route"]["node_path"])
    assert result["metrics"]["expanded_nodes"] > 0
    compared = astar_core.road_compare(engine, 0, 597, False)
    assert compared["same_optimal_cost"] is True
    assert compared["cost_difference_m"] == pytest.approx(0)
    unreachable = astar_core.road_search(engine, 1, 0, "astar", False)
    assert unreachable["found"] is False
    assert unreachable["route"] is None


def test_binding_grid_and_trace():
    grid = [[0, 0], [0, 0]]
    four = astar_core.grid_search(grid, (0, 0), (1, 1), 4, "astar", False)
    eight = astar_core.grid_search(grid, (0, 0), (1, 1), 8, "dijkstra", True)
    assert four["cost"] == 2
    assert four["trace"] == []
    assert eight["cost"] == 1.5
    assert eight["trace"]
    assert eight["trace"][0]["state"] == {"row": 0, "col": 0}
    assert astar_core.grid_search([[0, 1], [1, 0]], (0, 0), (1, 1), 8)["found"] is False


def test_binding_exceptions_are_python_exceptions():
    with pytest.raises(ValueError, match="movement"):
        astar_core.grid_search([[0]], (0, 0), (0, 0), 5)
    with pytest.raises(ValueError, match="grid values"):
        astar_core.grid_search([[2]], (0, 0), (0, 0))
    with pytest.raises(RuntimeError, match="cannot open road graph"):
        astar_core.RoadEngine(str(ROOT / "tests/missing.json"))
    engine = astar_core.RoadEngine(str(ROOT / "data/road/graph.json"))
    with pytest.raises(IndexError, match="out of range"):
        astar_core.road_search(engine, -1, 0)
