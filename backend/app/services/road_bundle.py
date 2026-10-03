"""Validate routing and visualization files as one generated road bundle."""

import hashlib
import json
from pathlib import Path

import astar_core


def load_bundle(graph_path: Path) -> tuple[astar_core.RoadEngine, bytes, bytes | None]:
    directory = graph_path.parent
    manifest = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    graph_bytes = graph_path.read_bytes()
    roads_bytes = (directory / "roads.geojson").read_bytes()
    for label, payload in (("graph", graph_bytes), ("roads", roads_bytes)):
        actual = hashlib.sha256(payload).hexdigest()
        if manifest.get(f"{label}_sha256") != actual:
            raise ValueError(f"road bundle {label} checksum mismatch")
    engine = astar_core.RoadEngine(str(graph_path))
    if (engine.node_count != manifest.get("exported_nodes") or
            engine.edge_count != manifest.get("exported_edges")):
        raise ValueError("road bundle graph count mismatch")
    features = json.loads(roads_bytes)["features"]
    if len(features) != engine.edge_count:
        raise ValueError("road bundle geometry count mismatch")
    context_bytes = None
    if manifest.get("context_sha256"):
        context_bytes = (directory / "context.geojson").read_bytes()
        if hashlib.sha256(context_bytes).hexdigest() != manifest["context_sha256"]:
            raise ValueError("road bundle context checksum mismatch")
        context = json.loads(context_bytes)
        if context.get("counts") != manifest.get("cartography_counts"):
            raise ValueError("road bundle context count mismatch")
        actual_counts = {"buildings": sum(bool(f["properties"].get("building")) for f in context["features"]),
                         "pois": sum(bool(f["properties"].get("category")) for f in context["features"])}
        if context["counts"] != actual_counts:
            raise ValueError("road bundle context feature count mismatch")
        if context.get("center") != {"lat": manifest["center_lat"], "lon": manifest["center_lon"]}:
            raise ValueError("road bundle context center mismatch")
    return engine, roads_bytes, context_bytes
