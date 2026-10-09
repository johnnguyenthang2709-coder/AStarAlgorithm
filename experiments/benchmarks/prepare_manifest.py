"""Freeze reproducible road strata and author-world goal coordinates.

This is an offline protocol step, not a timed benchmark. Run before executing
the full matrix and commit benchmark-manifest.json separately from results.
"""

import hashlib
import json
import random
import sys
from pathlib import Path

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
import astar_core

AUTHOR_SHA = "8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8"
SEED = 20261009


def polygon_csv(path: Path) -> list[Polygon]:
    import csv
    groups, vertices = [], []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if row and row[0].strip().lower() == "x":
                if vertices:
                    groups.append(Polygon(vertices))
                vertices = []
            elif len(row) == 2:
                vertices.append((float(row[0]), float(row[1])))
    if vertices:
        groups.append(Polygon(vertices))
    if not groups or not all(poly.is_valid and poly.area > 0 for poly in groups):
        raise ValueError(f"invalid upstream polygon geometry: {path}")
    return groups


def author_world(source: Path, filename: str, size: int, step: int) -> dict:
    path = source / filename
    polygons = polygon_csv(path)
    obstacles = unary_union(polygons)
    # World border is outside the source's 0..size working coordinates so
    # start (0,0) has a nonzero boundary margin for a radius-0.5 robot.
    free = box(-2, -2, size + 2, size + 2).difference(obstacles.buffer(0.5))
    origin = Point(0, 0)
    component = next((part for part in (free.geoms if hasattr(free, "geoms") else [free])
                      if part.covers(origin)), None)
    if component is None:
        raise ValueError(f"upstream start lacks 0.5 clearance: {filename}")
    candidates = [(x, y) for x in range(20 + step, 20 + 10 * step, step)
                  for y in range(20 + step, 20 + 10 * step, step)
                  if x <= size and y <= size and component.contains(Point(x, y))]
    if len(candidates) < 8:
        raise ValueError(f"fewer than eight valid author goals: {filename}")
    # Goal choice uses only geometry and distance from start, never outcomes.
    ordered = sorted(candidates, key=lambda p: (p[0] * p[0] + p[1] * p[1], p))
    indices = [round(i * (len(ordered) - 1) / 7) for i in range(8)]
    goals = [list(ordered[i]) for i in indices]
    return {"file": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bounds": [-2, -2, size + 2, size + 2], "start": [0, 0],
            "valid_lattice_goals": len(candidates), "goals": goals,
            "radii": [10, 20, 30], "robot_radius": 0.5,
            "geometry_valid": True, "clearance_component_valid": True}


def road_pairs() -> dict:
    path = ROOT / "data/road/graph.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = len(data["nodes"])
    engine = astar_core.RoadEngine(str(path))
    rng = random.Random(SEED)
    candidates, used = [], set()
    while len(candidates) < 6000:
        pair = (rng.randrange(nodes), rng.randrange(nodes))
        if pair[0] == pair[1] or pair in used:
            continue
        used.add(pair)
        result = astar_core.road_search(engine, *pair, "dijkstra", False)
        candidates.append((pair, result["route"]["cost_m"] if result["found"] else None))
    reachable = sorted(cost for _, cost in candidates if cost is not None)
    if len(reachable) < 540:
        raise ValueError("insufficient reachable candidate pairs")
    q1, q2 = reachable[len(reachable) // 3], reachable[2 * len(reachable) // 3]
    selected = {"short": [], "medium": [], "long": []}
    for (start, goal), cost in candidates:
        if cost is None:
            continue
        label = "short" if cost <= q1 else "medium" if cost <= q2 else "long"
        if len(selected[label]) < 60:
            selected[label].append({"start": start, "goal": goal,
                                    "offline_distance_m": cost})
    if any(len(pairs) != 60 for pairs in selected.values()):
        raise ValueError("a distance stratum contains fewer than 60 pairs")
    edges = data["edges"]
    directed = {(edge["from"], edge["to"]) for edge in edges}
    one_way = next((edge for edge in edges
                    if (edge["to"], edge["from"]) not in directed), None)
    unreachable = next((pair for pair, cost in candidates if cost is None), None)
    snap_edge = next(edge for edge in edges if len(edge["geometry"]) >= 2)
    first, second = snap_edge["geometry"][:2]
    midpoint = [(first[1] + second[1]) / 2, (first[0] + second[0]) / 2]
    return {"graph_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "graph_nodes": nodes, "graph_directed_edges": len(edges),
            "sampling_seed": SEED, "candidate_pairs": len(candidates),
            "reachable_candidates": len(reachable),
            "quantile_definition": "rank floor(n/3), floor(2n/3) of 6000 sampled reachable directed-pair Dijkstra distances",
            "quantile_cutoffs_m": [q1, q2], "selected_pairs": selected,
            "edge_cases": {"start_equals_goal": [0, 0],
                           "one_way_directed_edge": [one_way["from"], one_way["to"]] if one_way else None,
                           "unreachable_pair": list(unreachable) if unreachable else None,
                           "nearest_edge_midpoint_lat_lon": midpoint}}


def main():
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT.parent / "AStarAlgorithm-authors-benchmark")
    output = HERE / "benchmark-manifest.json"
    payload = {"protocol_version": 1, "project_base_commit": "cb69fc65fb81f6cffdd3e0556f4dccd5892bdcdf",
               "authors_commit": AUTHOR_SHA, "authors_source_url": "https://github.com/ThanhBinhTran/autonomousRobot",
               "paper_doi": "10.1016/j.robot.2025.105185",
               "road": road_pairs(),
               "robot": {"status": "prespecified_but_gated_on_upstream_execution_collision_validity",
                         "episode_limit": 100, "radii": [10, 20, 30],
                         "worlds": [author_world(source, "_map_deadend.csv", 100, 10),
                                    author_world(source, "_map_bugtrap.csv", 200, 20)],
                         "expected_configurations": 48,
                         "method_episodes_if_gate_passes": 96},
               "road_timing": {"warmup_per_pair_per_method": 1, "batches": 7,
                               "batch_calls_by_stratum": {"short": 20, "medium": 10, "long": 5},
                               "clock": "C++ steady_clock", "trace": False,
                               "search_only": True},
               "robot_metric_rules": {"actual_distance": "sum Euclidean lengths of coordinate updates",
                                      "planned_asp_distance": "sum logged ASP polyline lengths, separate from actual",
                                      "turn_collinearity": "author inside_line_segment on each consecutive position triple",
                                      "turn_heading": "absolute wrapped heading change greater than 15 degrees",
                                      "collision": "each executed segment must avoid polygon interior and respect 0.5 clearance",
                                      "failure_policy": "retain every prespecified failed or timed-out episode"}}
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
