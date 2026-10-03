"""Small OSM-only display export; never changes the routing graph."""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import LineString, Polygon, mapping, shape
from shapely.ops import polygonize, unary_union

POI_TAGS = {"amenity": {"university", "school", "college", "hospital", "clinic", "parking", "fuel", "cafe"},
            "leisure": {"park"}, "highway": {"bus_stop"},
            "public_transport": {"platform", "station"}}
PRIORITY = {"university": 0, "hospital": 1, "park": 2, "college": 3,
            "school": 4, "clinic": 5, "station": 6, "bus_stop": 7,
            "platform": 7, "fuel": 8, "parking": 9, "cafe": 10}


def poi_category(tags: dict) -> str | None:
    for key, allowed in POI_TAGS.items():
        if tags.get(key) in allowed:
            return tags[key]
    return None


def osm_geometry(element: dict, nodes: dict) -> dict | None:
    """Only construct complete source rings; do not infer missing boundaries."""
    if element["type"] == "node":
        return {"type": "Point", "coordinates": [element["lon"], element["lat"]]}
    if element["type"] == "way":
        coords = [[p["lon"], p["lat"]] for p in element.get("geometry", [])]
        if not coords and all(n in nodes for n in element.get("nodes", [])):
            coords = [[nodes[n]["lon"], nodes[n]["lat"]] for n in element.get("nodes", [])]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            polygon = Polygon(coords)
            if polygon.is_valid and not polygon.is_empty:
                return mapping(polygon)
    if element["type"] == "relation":
        rings = {"outer": [], "inner": []}
        for member in element.get("members", []):
            points = member.get("geometry", [])
            role = member.get("role") or "outer"
            if member.get("type") == "way" and len(points) > 1 and role in rings:
                rings[role].append(LineString([(p["lon"], p["lat"]) for p in points]))
        outer = list(polygonize(rings["outer"]))
        if outer:
            polygon = unary_union(outer).difference(unary_union(list(polygonize(rings["inner"]))))
            if polygon.is_valid and polygon.geom_type in ("Polygon", "MultiPolygon"):
                return mapping(polygon)
    return None


def build_context(elements: list[dict], config: dict) -> dict:
    nodes = {x["id"]: x for x in elements if x["type"] == "node"}
    lat, lon = config["center_lat"], config["center_lon"]
    dy = config["radius_m"] / 111_195
    dx = dy / math.cos(math.radians(lat))
    buildings, candidates = [], []
    for element in elements:
        tags = element.get("tags", {})
        category = poi_category(tags)
        if not tags.get("building") and not category:
            continue
        geometry = osm_geometry(element, nodes)
        if not geometry:
            continue
        geom = shape(geometry)
        point = geom.representative_point()
        if abs(point.x - lon) > dx or abs(point.y - lat) > dy:
            continue
        identity = f"{element['type']}/{element['id']}"
        if tags.get("building") not in (None, "no") and geom.geom_type in ("Polygon", "MultiPolygon"):
            buildings.append({"type": "Feature", "geometry": geometry,
                              "properties": {"osm_id": identity, "building": tags["building"]}})
        if category:
            candidates.append({"type": "Feature", "geometry": mapping(point),
                "properties": {"osm_id": identity, "category": category, "name": tags.get("name")}})
    # Deterministic priority, named landmarks first, then distance. Avoid duplicate
    # representations of the same named place (e.g. node and enclosing polygon).
    candidates.sort(key=lambda f: (PRIORITY[f["properties"]["category"]],
        not bool(f["properties"]["name"]),
        sum((f["geometry"]["coordinates"][i] - [lon, lat][i]) ** 2 for i in range(2)),
        f["properties"]["osm_id"]))
    pois, seen = [], set()
    for feature in candidates:
        p = feature["properties"]
        identity = (p["category"], p["name"].casefold()) if p["name"] else (p["osm_id"],)
        if identity in seen:
            continue
        # Space less important landmarks apart by approximately 140m.
        xy = feature["geometry"]["coordinates"]
        if p["category"] not in ("university", "hospital", "park") and any(
            (xy[0] - f["geometry"]["coordinates"][0]) ** 2 +
            (xy[1] - f["geometry"]["coordinates"][1]) ** 2 < .00125 ** 2 for f in pois):
            continue
        seen.add(identity)
        pois.append(feature)
        if len(pois) == 25:
            break
    return {"schema_version": 1, "type": "FeatureCollection", "features": buildings + pois,
            "center": {"lat": lat, "lon": lon},
            "counts": {"buildings": len(buildings), "pois": len(pois)}}


def enrich_roads(roads: dict, elements: list[dict]) -> dict:
    tags = {x["id"]: x.get("tags", {}) for x in elements if x["type"] == "way"}
    for feature in roads["features"]:
        p = feature["properties"]
        ids = p["osmid"] if isinstance(p["osmid"], list) else [p["osmid"]]
        attributes = [tags[i] for i in ids if i in tags]
        if not attributes:
            continue
        types = sorted({t["highway"] for t in attributes if "highway" in t})
        p["highway"] = types
        flags = [t.get("oneway") in ("yes", "1", "true", "-1") or
                 (t.get("junction") == "roundabout" and t.get("oneway") != "no") for t in attributes]
        p["oneway"] = all(flags) if flags else None
    return roads


def read_elements(paths: list[Path]) -> list[dict]:
    found = {}
    for path in paths:
        for element in json.loads(path.read_text(encoding="utf-8"))["elements"]:
            found[(element["type"], element["id"])] = element
    return list(found.values())
