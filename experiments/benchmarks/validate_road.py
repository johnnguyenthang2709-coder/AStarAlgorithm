"""Validate the frozen road matrix and independent edge cases; write audit data."""

import csv
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
import astar_core


def haversine(a, b):
    radius = 6371008.8
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    delta_lat = lat2 - lat1
    delta_lon = math.radians(b[1] - a[1])
    z = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1, z)))


def main():
    manifest = json.loads((HERE / "benchmark-manifest.json").read_text(encoding="utf-8"))
    graph_file = ROOT / "data/road/graph.json"
    assert hashlib.sha256(graph_file.read_bytes()).hexdigest() == manifest["road"]["graph_sha256"]
    graph = json.loads(graph_file.read_text(encoding="utf-8"))
    nodes = {node["id"]: (node["lat"], node["lon"]) for node in graph["nodes"]}
    scale = min(1.0, *(edge["length_m"] / direct for edge in graph["edges"]
                       if (direct := haversine(nodes[edge["from"]], nodes[edge["to"]])) > 0))
    edge_violations = sum(scale * haversine(nodes[e["from"]], nodes[e["to"]]) > e["length_m"] + 1e-6
                          for e in graph["edges"])
    assert edge_violations == 0
    with (HERE / "road-astar-dijkstra.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    grouped = defaultdict(dict)
    for row in rows:
        grouped[int(row["pair_id"])][row["algorithm"]] = row
    assert len(rows) == 360 and len(grouped) == 180
    for key, pair in grouped.items():
        assert set(pair) == {"astar", "dijkstra"}, key
        a, d = pair["astar"], pair["dijkstra"]
        assert a["start"] == d["start"] and a["goal"] == d["goal"] and a["stratum"] == d["stratum"]
        assert a["found"] == d["found"] == "1"
        assert abs(float(a["cost_m"]) - float(d["cost_m"])) <= 1e-6
        assert abs(float(a["cost_m"]) - float(a["offline_cost_m"])) <= 1e-6
    by_stratum = {}
    for stratum in ("short", "medium", "long"):
        pairs = [pair for pair in grouped.values() if pair["astar"]["stratum"] == stratum]
        assert len(pairs) == 60
        by_stratum[stratum] = {
            "pairs": len(pairs),
            "median_cost_m": statistics.median(float(p["astar"]["cost_m"]) for p in pairs),
            "median_expanded_astar": statistics.median(int(p["astar"]["expanded_nodes"]) for p in pairs),
            "median_expanded_dijkstra": statistics.median(int(p["dijkstra"]["expanded_nodes"]) for p in pairs),
            "median_search_us_astar": statistics.median(float(p["astar"]["median_search_us"]) for p in pairs),
            "median_search_us_dijkstra": statistics.median(float(p["dijkstra"]["median_search_us"]) for p in pairs),
            "astar_fewer_expansions": sum(int(p["astar"]["expanded_nodes"]) < int(p["dijkstra"]["expanded_nodes"]) for p in pairs),
            "astar_faster": sum(float(p["astar"]["median_search_us"]) < float(p["dijkstra"]["median_search_us"]) for p in pairs),
        }
    engine = astar_core.RoadEngine(str(graph_file))
    edge_cases = []
    for name in ("start_equals_goal", "one_way_directed_edge", "unreachable_pair"):
        start, goal = manifest["road"]["edge_cases"][name]
        compared = astar_core.road_compare(engine, start, goal, False)
        assert compared["same_optimal_cost"]
        edge_cases.append({"case": name, "start": start, "goal": goal,
                           "found": compared["astar"]["found"],
                           "astar_cost_m": compared["astar"]["route"]["cost_m"] if compared["astar"]["found"] else "",
                           "dijkstra_cost_m": compared["dijkstra"]["route"]["cost_m"] if compared["dijkstra"]["found"] else ""})
    assert edge_cases[0]["found"] and edge_cases[0]["astar_cost_m"] == 0
    assert edge_cases[1]["found"] and not edge_cases[2]["found"]
    start = tuple(manifest["road"]["edge_cases"]["nearest_edge_midpoint_lat_lon"])
    destination = nodes[manifest["road"]["edge_cases"]["nearest_edge_goal_node"]]
    compared = astar_core.road_compare_coordinates(engine, start, destination, False)
    assert compared["same_optimal_cost"] and compared["astar"]["found"]
    assert compared["start_snap"]["snap_distance_m"] < 1e-6
    edge_cases.append({"case": "nearest_edge_midpoint", "start": start, "goal": destination,
                       "found": True, "astar_cost_m": compared["astar"]["route"]["cost_m"],
                       "dijkstra_cost_m": compared["dijkstra"]["route"]["cost_m"]})
    with (HERE / "road-edge-cases.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=edge_cases[0].keys())
        writer.writeheader()
        writer.writerows(edge_cases)
    report = {"matrix_pairs": len(grouped), "cost_equal_pairs": len(grouped),
              "graph_nodes": len(nodes), "graph_directed_edges": len(graph["edges"]),
              "haversine_scale": scale, "heuristic_edge_violations": edge_violations,
              "strata": by_stratum, "edge_cases": edge_cases,
              "timing_scope": "C++ search only; 7 batch medians per pair, not end-to-end API time"}
    (HERE / "road-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "edge_cases"}, indent=2))


if __name__ == "__main__":
    main()
