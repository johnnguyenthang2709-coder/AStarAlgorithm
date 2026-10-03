"""Download and export a distance-only directed OSMnx road graph."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import networkx as nx
import osmnx as ox
from cartography import build_context, enrich_roads, read_elements

EARTH_RADIUS_M = 6_371_008.8
HEURISTIC_TOLERANCE_M = 0.01


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _attribute(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_attribute(item) for item in value]
    return str(value)


def _key_order(key: object) -> tuple[int, object]:
    if isinstance(key, int) and not isinstance(key, bool):
        return 0, key
    return 1, str(key)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def _geometry(data: dict, source: dict, target: dict) -> list[list[float]]:
    if data.get("geometry") is None:
        coords = [[float(source["x"]), float(source["y"])],
                  [float(target["x"]), float(target["y"])]]
    else:
        shape = data["geometry"]
        if shape.geom_type != "LineString":
            raise ValueError("edge geometry must be a LineString")
        coords = [[float(lon), float(lat)] for lon, lat in shape.coords]
    if len(coords) < 2 or any(not all(math.isfinite(x) for x in point) for point in coords):
        raise ValueError("edge geometry is malformed")
    # OSMnx geometry can be stored in either orientation for a directed edge.
    start = (float(source["x"]), float(source["y"]))
    score_forward = sum((coords[0][i] - start[i]) ** 2 for i in range(2))
    score_reverse = sum((coords[-1][i] - start[i]) ** 2 for i in range(2))
    if score_reverse < score_forward:
        coords.reverse()
    return coords


def build_export(graph: nx.MultiDiGraph, config: dict) -> tuple[dict, dict, dict]:
    if not isinstance(graph, nx.MultiDiGraph) or not graph.is_directed():
        raise ValueError("expected a directed OSMnx MultiDiGraph")
    node_ids = sorted(graph.nodes)
    dense = {osm_id: index for index, osm_id in enumerate(node_ids)}
    nodes = []
    for osm_id in node_ids:
        attrs = graph.nodes[osm_id]
        lat = _finite_number(attrs.get("y"), "node latitude")
        lon = _finite_number(attrs.get("x"), "node longitude")
        if abs(lat) > 90 or abs(lon) > 180:
            raise ValueError("node coordinate outside Earth bounds")
        nodes.append({"id": dense[osm_id], "osm_id": int(osm_id), "lat": lat, "lon": lon})

    selected: dict[tuple[int, int], tuple[tuple, dict]] = {}
    display = {}
    for source, target, key, data in graph.edges(keys=True, data=True):
        length = _finite_number(data.get("length"), f"edge {source}->{target} length")
        if length < 0:
            raise ValueError(f"edge {source}->{target} has negative length")
        pair = (dense[source], dense[target])
        ranking = (length, _key_order(key))
        if pair not in selected or ranking < selected[pair][0]:
            display[pair] = {"highway": _attribute(data.get("highway")),
                             "oneway": _attribute(data.get("oneway"))}
            selected[pair] = (ranking, {
                "from": pair[0],
                "to": pair[1],
                "length_m": length,
                "osm_key": _attribute(key),
                "osmid": _attribute(data.get("osmid")),
                "name": _attribute(data.get("name")),
                "geometry": _geometry(data, graph.nodes[source], graph.nodes[target]),
            })

    edges = [selected[pair][1] for pair in sorted(selected)]
    gaps = [_haversine(nodes[edge["from"]]["lat"], nodes[edge["from"]]["lon"],
                       nodes[edge["to"]]["lat"], nodes[edge["to"]]["lon"])
            - edge["length_m"] for edge in edges]
    features = [{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": edge["geometry"]},
        "properties": {**{name: edge[name] for name in
                       ("from", "to", "length_m", "osm_key", "osmid", "name")},
                       **display[(edge["from"], edge["to"])]},
    } for edge in edges]
    metadata = {
        "center_lat": config["center_lat"],
        "center_lon": config["center_lon"],
        "center_source": config.get("center_source"),
        "radius_m": config["radius_m"],
        "dist_type": "bbox",
        "network_type": config["network_type"],
        "simplify": config["simplify"],
        "osmnx_version": ox.__version__,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_nodes": graph.number_of_nodes(),
        "original_edges": graph.number_of_edges(),
        "exported_nodes": len(nodes),
        "exported_edges": len(edges),
        "parallel_edges_removed": graph.number_of_edges() - len(edges),
        "haversine_edge_tolerance_m": HEURISTIC_TOLERANCE_M,
        "haversine_edge_violations": sum(gap > HEURISTIC_TOLERANCE_M for gap in gaps),
        "maximum_haversine_over_length_m": max((max(0.0, gap) for gap in gaps), default=0.0),
        "connected_component_policy": "largest weakly connected component (OSMnx retain_all=False)"
            if not config["retain_all"] else "retain all components",
        "exported_weak_components": nx.number_weakly_connected_components(graph),
        "exported_strong_components": nx.number_strongly_connected_components(graph),
    }
    return {"schema_version": 1, "nodes": nodes, "edges": edges}, \
        {"type": "FeatureCollection", "features": features}, metadata


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")


def write_export(output: Path, routing: dict, roads: dict, metadata: dict, context: dict | None = None) -> None:
    """Write one road bundle and bind its two data files to the manifest."""
    output.mkdir(parents=True, exist_ok=True)
    graph_path = output / "graph.json"
    roads_path = output / "roads.geojson"
    _write_json(graph_path, routing)
    _write_json(roads_path, roads)
    manifest = {**metadata,
                "graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
                "roads_sha256": hashlib.sha256(roads_path.read_bytes()).hexdigest()}
    if context is not None:
        _write_json(output / "context.geojson", context)
        manifest.update(context_sha256=hashlib.sha256((output / "context.geojson").read_bytes()).hexdigest(),
                        cartography_counts=context["counts"])
    _write_json(output / "metadata.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("data/road/config.json"))
    parser.add_argument("--output", type=Path, default=Path("data/road"))
    parser.add_argument("--context-only", action="store_true",
                        help="Enrich display data without writing or downloading routing data")
    parser.add_argument("--osm-source", type=Path, action="append", default=[],
                        help="Saved Overpass JSON input; repeat to combine road and context snapshots")
    parser.add_argument("--download-context", action="store_true",
                        help="Download local OSM buildings and selected POIs during preprocessing only")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    lat = _finite_number(config["center_lat"], "center_lat")
    lon = _finite_number(config["center_lon"], "center_lon")
    radius = _finite_number(config["radius_m"], "radius_m")
    if abs(lat) > 90 or abs(lon) > 180 or radius <= 0:
        raise ValueError("invalid center or radius")
    if config["network_type"] != "drive" or config["simplify"] is not True:
        raise ValueError("this export expects network_type=drive and simplify=true")
    if args.download_context:
        import requests
        west, south, east, north = ox.utils_geo.bbox_from_point((lat, lon), dist=radius)
        clauses = [f'nwr({south},{west},{north},{east})["{key}"];' for key in
                   ("building", "amenity", "leisure", "public_transport")]
        clauses.append(f'node({south},{west},{north},{east})["highway"="bus_stop"];')
        query = '[out:json][timeout:60];(' + ''.join(clauses) + ');out geom;'
        response = requests.post(ox.settings.overpass_url + '/interpreter', data={"data": query},
            headers={"User-Agent": ox.settings.http_user_agent}, timeout=(10, 90))
        response.raise_for_status()
        snapshot = args.output / "osm-context-source.json"
        args.output.mkdir(parents=True, exist_ok=True)
        _write_json(snapshot, response.json())
        args.osm_source.append(snapshot)
    elements = read_elements(args.osm_source) if args.osm_source else []
    context = build_context(elements, config)
    if args.context_only:
        if not elements:
            raise ValueError("--context-only requires --osm-source or --download-context")
        # Preserve routing bytes, IDs, geometry and the original routing build timestamp.
        roads = json.loads((args.output / "roads.geojson").read_text(encoding="utf-8"))
        enrich_roads(roads, elements)
        _write_json(args.output / "roads.geojson", roads)
        _write_json(args.output / "context.geojson", context)
        manifest = json.loads((args.output / "metadata.json").read_text(encoding="utf-8"))
        manifest.update(roads_sha256=hashlib.sha256((args.output / "roads.geojson").read_bytes()).hexdigest(),
            context_sha256=hashlib.sha256((args.output / "context.geojson").read_bytes()).hexdigest(),
            cartography_counts=context["counts"],
            cartography_built_at_utc=datetime.now(timezone.utc).isoformat())
        _write_json(args.output / "metadata.json", manifest)
        print(json.dumps(context["counts"]))
        return
    graph = ox.graph.graph_from_point(
        (lat, lon), dist=radius, dist_type="bbox", network_type="drive",
        simplify=True, retain_all=config["retain_all"])
    routing, roads, metadata = build_export(graph, config)
    if metadata["haversine_edge_violations"]:
        raise ValueError(f"{metadata['haversine_edge_violations']} road edges violate the "
                         f"Haversine lower bound by > {HEURISTIC_TOLERANCE_M} m; "
                         f"maximum gap is {metadata['maximum_haversine_over_length_m']} m")
    write_export(args.output, routing, roads, metadata, context)
    print(json.dumps({"nodes": metadata["exported_nodes"],
                      "edges": metadata["exported_edges"],
                      "parallel_removed": metadata["parallel_edges_removed"]}))


if __name__ == "__main__":
    main()
