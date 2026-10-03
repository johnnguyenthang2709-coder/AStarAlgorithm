"""Deterministic export tests; no network calls."""

import importlib.util
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sys

import networkx as nx
from shapely.geometry import LineString

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "preprocess_roads.py"
sys.path.insert(0, str(MODULE.parent))
spec = importlib.util.spec_from_file_location("preprocess_roads", MODULE)
preprocess = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preprocess)
from cartography import build_context, enrich_roads, osm_geometry

CONFIG = {"center_lat": 10, "center_lon": 106, "radius_m": 2000,
          "network_type": "drive", "simplify": True, "retain_all": False}


class ExportTests(unittest.TestCase):
    def graph(self):
        graph = nx.MultiDiGraph()
        graph.add_node(20, y=10.0, x=106.001)
        graph.add_node(10, y=10.0, x=106.0)
        graph.add_edge(10, 20, key=2, length=150, osmid=12, name="long")
        graph.add_edge(10, 20, key=1, length=120, osmid=[13, 14], name="short",
                       geometry=LineString([(106.001, 10), (106.0005, 10.0001), (106, 10)]))
        graph.add_edge(10, 20, key=0, length=120, osmid=15, name="tie winner")
        graph.add_edge(20, 10, key=0, length=130, osmid=16, name="reverse")
        return graph

    def test_parallel_reduction_direction_and_geometry(self):
        routing, geojson, metadata = preprocess.build_export(self.graph(), CONFIG)
        self.assertEqual([node["osm_id"] for node in routing["nodes"]], [10, 20])
        self.assertEqual([(e["from"], e["to"]) for e in routing["edges"]], [(0, 1), (1, 0)])
        self.assertEqual(routing["edges"][0]["osm_key"], 0)
        self.assertEqual(routing["edges"][0]["length_m"], 120)
        self.assertEqual(routing["edges"][1]["length_m"], 130)
        self.assertEqual(metadata["parallel_edges_removed"], 2)
        self.assertEqual(metadata["haversine_edge_violations"], 0)
        self.assertEqual(geojson["features"][0]["geometry"]["coordinates"],
                         [[106, 10], [106.001, 10]])

    def test_reversed_line_geometry_is_oriented(self):
        graph = self.graph()
        graph.remove_edge(10, 20, key=0)
        routing, _, _ = preprocess.build_export(graph, CONFIG)
        self.assertEqual(routing["edges"][0]["osmid"], [13, 14])
        self.assertEqual(routing["edges"][0]["geometry"],
                         [[106, 10], [106.0005, 10.0001], [106.001, 10]])

    def test_invalid_lengths_rejected(self):
        for length in (float("nan"), float("inf"), -1, None):
            graph = self.graph()
            graph.add_edge(20, 20, key=1, length=length)
            with self.subTest(length=length), self.assertRaises(ValueError):
                preprocess.build_export(graph, CONFIG)

    def test_export_manifest_binds_graph_and_geometry(self):
        routing, roads, metadata = preprocess.build_export(self.graph(), CONFIG)
        with TemporaryDirectory() as directory:
            output = Path(directory)
            preprocess.write_export(output, routing, roads, metadata)
            manifest = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["graph_sha256"], hashlib.sha256(
                (output / "graph.json").read_bytes()).hexdigest())
            self.assertEqual(manifest["roads_sha256"], hashlib.sha256(
                (output / "roads.geojson").read_bytes()).hexdigest())
            self.assertEqual(manifest["exported_edges"], len(roads["features"]))

    def test_cartography_does_not_change_routing_export(self):
        graph = self.graph()
        before, _, _ = preprocess.build_export(graph, CONFIG)
        graph[10][20][0].update(highway="secondary", oneway=True)
        after, roads, _ = preprocess.build_export(graph, CONFIG)
        self.assertEqual(before, after)
        self.assertEqual(roads["features"][0]["properties"]["highway"], "secondary")
        self.assertIs(roads["features"][0]["properties"]["oneway"], True)

    def test_saved_osm_tags_enrich_only_display_properties(self):
        routing, roads, _ = preprocess.build_export(self.graph(), CONFIG)
        original = json.dumps(routing, sort_keys=True)
        enrich_roads(roads, [{"type": "way", "id": 15, "tags": {"highway": "secondary", "oneway": "-1"}}])
        self.assertEqual(roads["features"][0]["properties"]["highway"], ["secondary"])
        self.assertIs(roads["features"][0]["properties"]["oneway"], True)
        self.assertEqual(json.dumps(routing, sort_keys=True), original)

    def test_buildings_require_complete_valid_source_rings(self):
        points = [{"lon": 106, "lat": 10}, {"lon": 106.001, "lat": 10},
                  {"lon": 106.001, "lat": 10.001}, {"lon": 106, "lat": 10}]
        element = {"type": "way", "id": 1, "geometry": points, "tags": {"building": "yes"}}
        self.assertEqual(osm_geometry(element, {})["type"], "Polygon")
        self.assertIsNone(osm_geometry({**element, "geometry": points[:-1]}, {}))
        result = build_context([element], CONFIG)
        self.assertEqual(result["counts"]["buildings"], 1)
        self.assertEqual(set(result["features"][0]["properties"]), {"osm_id", "building"})

    def test_poi_filter_deduplicates_names_and_excludes_unrequested_tags(self):
        elements = [
            {"type": "node", "id": 1, "lat": 10, "lon": 106, "tags": {"amenity": "university", "name": "University"}},
            {"type": "node", "id": 2, "lat": 10.001, "lon": 106, "tags": {"amenity": "university", "name": "University"}},
            {"type": "node", "id": 3, "lat": 10, "lon": 106, "tags": {"shop": "convenience"}},
            {"type": "node", "id": 4, "lat": 11, "lon": 106, "tags": {"amenity": "hospital"}}]
        result = build_context(elements, CONFIG)
        self.assertEqual(result["counts"]["pois"], 1)
        self.assertEqual(result["features"][0]["properties"]["osm_id"], "node/1")

    def test_context_manifest_hash(self):
        routing, roads, metadata = preprocess.build_export(self.graph(), CONFIG)
        context = build_context([], CONFIG)
        with TemporaryDirectory() as directory:
            output = Path(directory)
            preprocess.write_export(output, routing, roads, metadata, context)
            manifest = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["context_sha256"], hashlib.sha256((output / "context.geojson").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
