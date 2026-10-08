import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

from import_bar_polygon import GridTransform, import_scenario, rasterize_bounded
from evaluate_author_map import read_polygons, segment_blocked
from app.main import create_app
from app.services.bar_scenarios import load_scenario
from app.services.bar_sensing import UNKNOWN, sense
from app.services.bar_service import BarController


def test_repeated_headers_parse_multiple_polygons_and_explicit_closure(tmp_path):
    path = tmp_path / "map.csv"
    path.write_text("x,y\n1,1\n3,1\n3,3\n1,3\n1,1\nx,y\n5,5\n7,5\n6,7\n", encoding="utf-8")
    polygons = read_polygons(path)
    assert len(polygons) == 2
    assert len(polygons[0]) == 4
    assert polygons[1] == [(5, 5), (7, 5), (6, 7)]


@pytest.mark.parametrize("contents", [
    "0,0\n1,0\n1,1\n", "x,y\n1,1\n2,2\n3,3\n", "x,y\n0,0\n1,0\n0,nan\n",
    "x,y\n0,0\n1,0\n0,1\nx,y\n", "x,y\n0,0,1\n1,0\n0,1\n",
])
def test_malformed_polygon_csv_is_rejected(tmp_path, contents):
    path = tmp_path / "invalid.csv"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        read_polygons(path)


def test_cartesian_y_up_to_grid_row_down_and_clearance(tmp_path):
    path = tmp_path / "map.csv"
    path.write_text("x,y\n1,1\n3,1\n3,3\n1,3\n", encoding="utf-8")
    transform = GridTransform(0, 0, 6, 6, 1)
    assert transform.cell((0.5, 5.5)) == (0, 0)
    assert transform.cell((5.5, 0.5)) == (5, 5)
    image_axis = GridTransform(0, 0, 6, 6, 1, "down")
    assert image_axis.cell((0.5, 0.5)) == (0, 0)
    assert image_axis.center(5, 5) == (5.5, 5.5)
    scenario = import_scenario(path, transform, (0.5, 5.5), (5.5, 0.5), 0.0)
    assert scenario["rows"][3][2] == "#"
    assert scenario["map_source"]["polygon_count"] == 1
    with pytest.raises(ValueError, match="exact cell centers"):
        transform.cell((1, 1))
    with pytest.raises(ValueError, match="outside"):
        transform.cell((-0.5, 5.5))
    with pytest.raises(ValueError, match="clearance"):
        import_scenario(path, transform, (2.5, 2.5), (5.5, 0.5), 0.0)
    with pytest.raises(ValueError, match="start is blocked or lacks"):
        import_scenario(path, transform, (0.5, 5.5), (5.5, 5.5), 2.6)


def test_intersected_grid_edge_is_not_traversable_and_clearance_expands_wall():
    polygons = [[(0.9, 1.2), (1.1, 1.2), (1.1, 1.8), (0.9, 1.8)]]
    transform = GridTransform(0, 0, 3, 3, 1)
    assert segment_blocked(transform.center(1, 0), transform.center(1, 1), polygons, 0)
    rows = rasterize_bounded(polygons, transform, 0)
    assert rows[1][0] == rows[1][1] == "#"
    wider = rasterize_bounded(polygons, transform, 0.5)
    assert sum(row.count("#") for row in wider) >= sum(row.count("#") for row in rows)


def test_disconnected_wall_and_resolution_dependent_passage():
    transform = GridTransform(0, 0, 8, 8, 1)
    wall = [[(3.2, 0), (4.8, 0), (4.8, 8), (3.2, 8)]]
    rows = rasterize_bounded(wall, transform, 0)
    assert all(row[3:5] == "##" for row in rows)
    # The same gap closes under conservative size-2 rasterization, but
    # remains traversable at size 0.5.
    bars = [[(2, 3), (6, 3), (6, 3.25), (2, 3.25)],
            [(2, 4.75), (6, 4.75), (6, 5), (2, 5)]]
    fine = rasterize_bounded(bars, GridTransform(0, 0, 8, 8, 0.5), 0)
    coarse = rasterize_bounded(bars, GridTransform(0, 0, 8, 8, 2), 0)
    assert all(value == "." for value in fine[7])
    assert fine[8][8] == "."
    assert coarse[1][2] == "#" or coarse[2][2] == "#"
    assert all("#" in row for row in coarse[1:3])


@pytest.mark.parametrize("name,radius", [
    ("irregular_u", 1), ("irregular_u", 2), ("irregular_u", 4),
    ("irregular_bugtrap", 1), ("irregular_bugtrap", 2), ("irregular_bugtrap", 4),
])
def test_imported_scenarios_reproduce_and_all_grid_steps_are_polygon_clear(name, radius):
    scenario = load_scenario(name)
    source = ROOT / "data" / "bar" / "polygon_sources" / f"{name}.csv"
    metadata = scenario.map_source
    transform = GridTransform(*metadata["bounds"], metadata["cell_size"],
                              "up" if "CSV y up" in metadata["axis"] else "down")
    regenerated = import_scenario(source, transform,
                                  transform.center(*scenario.start),
                                  transform.center(*scenario.goal), metadata["robot_radius"])
    assert tuple(regenerated["rows"]) == scenario.rows
    assert regenerated["map_source"] == metadata
    polygons = read_polygons(source)
    for r, row in enumerate(scenario.rows):
        for c, value in enumerate(row):
            if value != ".":
                continue
            for nr, nc in ((r + 1, c), (r, c + 1)):
                if nr < len(scenario.rows) and nc < len(row) and scenario.rows[nr][nc] == ".":
                    assert not segment_blocked(transform.center(r, c), transform.center(nr, nc),
                                               polygons, metadata["robot_radius"])
    first = BarController(scenario.rows, scenario.start, scenario.goal, radius)
    episode = first.run()
    second = BarController(scenario.rows, scenario.start, scenario.goal, radius).run()
    assert episode["status"] == "goal_reached"
    assert episode["metrics"]["executed_distance"] == second["metrics"]["executed_distance"]
    assert len(episode["recoveries"]) == len(second["recoveries"])
    assert all(recovery["invariant_verified"] for recovery in episode["recoveries"])
    assert any(UNKNOWN in row for row in first.known)
    if radius >= 2 or name == "irregular_bugtrap":
        assert episode["recoveries"]


def test_polygon_wall_occludes_unsensed_cells():
    scenario = load_scenario("irregular_u")
    known = [[UNKNOWN] * len(scenario.rows[0]) for _ in scenario.rows]
    sense(scenario.rows, known, (20, 17), 8)
    assert known[20][12] == 1  # near side of left wall is sensed
    assert known[20][5] == UNKNOWN  # beyond the wall is hidden


def test_api_exposes_grid_adaptation_without_hidden_polygon_vertices():
    with TestClient(create_app()) as client:
        response = client.post("/api/bar/simulate", json={"scenario": "irregular_u", "radius": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["map_kind"] == "polygon_grid"
    assert payload["success"]
    assert "map_source" not in payload and "polygons" not in payload
    assert "rows" in payload and "cols" in payload
