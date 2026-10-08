from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_author_map import blocked, rasterize, read_polygons, segment_blocked


def test_external_polygon_csv_is_rasterized_without_bundling_authors_map(tmp_path):
    source = tmp_path / "polygon.csv"
    source.write_text("x,y\n1,1\n3,1\n3,3\n1,3\n", encoding="utf-8")
    polygons = read_polygons(source)
    assert len(polygons) == 1
    assert blocked((2, 2), polygons, 0)
    assert not blocked((0, 0), polygons, 0)
    rows = rasterize(polygons, 1, 0, (4, 4))
    assert rows[2][2] == "#"
    assert rows[0][0] == "."
    assert segment_blocked((0, 2), (4, 2), polygons, 0)


def test_conservative_raster_removes_edge_that_crosses_polygon_between_free_centers():
    polygon = [[(0.4, -0.2), (0.6, -0.2), (0.6, 0.2), (0.4, 0.2)]]
    assert not blocked((0, 0), polygon, 0)
    assert not blocked((1, 0), polygon, 0)
    assert segment_blocked((0, 0), (1, 0), polygon, 0)
    center_only = rasterize(polygon, 1, 0, (2, 2), conservative_edges=False)
    conservative = rasterize(polygon, 1, 0, (2, 2))
    assert center_only[0][:2] == ".."
    assert conservative[0][:2] == "##"
