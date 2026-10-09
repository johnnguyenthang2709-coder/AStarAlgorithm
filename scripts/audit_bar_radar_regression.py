"""Read-only paired decision audit for Complex Irregular Labyrinth, radius 7.

Run: .venv/Scripts/python scripts/audit_bar_radar_regression.py
Writes CSV decision traces and first-divergence JSON into docs/. No navigation
policy or sensor implementation is changed; wrappers capture observations and
call the existing policy on its original state. Candidate A* probes use a
shallow policy copy with an independent verified-link set and counters.
"""

import copy
import csv
import json
import sys
from pathlib import Path
from time import perf_counter

from shapely.geometry import Point as ShapePoint, mapping
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app.services.bar_continuous as module
from app.services.bar_continuous import ContinuousPolicy, path_length, simulate_continuous
from app.services.bar_continuous_geometry import RAY_MARGIN, distance
from app.services.bar_information import possible_frontier, visible_frontier_gain, wall_key
from app.services.bar_labyrinth import COMPLEX, generate_labyrinth


def point(value):
    return (value["x"], value["y"])


def candidate_detail(policy, candidate, walls, frontier, prepared):
    disk = ShapePoint(candidate).buffer(policy.radius, quad_segs=12).intersection(policy.border)
    legacy_area = disk.difference(policy.known_free).area
    gain = visible_frontier_gain(candidate, policy.radius, prepared, frontier)
    travel_lb = distance(policy.current, candidate)
    probe = copy.copy(policy)
    probe.verified_links = set(policy.verified_links)
    probe.scan_positions = list(policy.scan_positions)
    result = probe.plan(candidate)
    return {
        "target": candidate,
        "key": policy.candidate_key(candidate),
        "legacy_disk_unknown_area": legacy_area,
        "radar_gain": gain,
        "radar_utility": gain / travel_lb ** .25 if travel_lb else None,
        "euclidean_travel_lower_bound": travel_lb,
        "astar_verified_cost": result["cost"] if result["found"] else None,
        "astar_nodes": result["nodes"],
        "astar_edges": result["edges"],
        "deferred": not policy.graph_changed_since(policy.deferred.get(policy.candidate_key(candidate))),
        "valid": policy._candidate_valid(candidate),
    }


def run(radar):
    world = generate_labyrinth(COMPLEX).world
    observed_walls = {}
    wall_deltas = {}
    decisions = []
    original_observe = ContinuousPolicy.observe
    original_select = ContinuousPolicy.select
    original_frontier = module.possible_frontier
    original_gain = module.visible_frontier_gain
    profile = {"frontier_ms": 0.0, "gain_ms": 0.0, "frontier_calls": 0,
               "gain_calls": 0, "frontier_detail": []}

    def observe(policy, observation, owner=None):
        before = len(observed_walls)
        for a, b in observation.edges:
            observed_walls[wall_key(a, b)] = (a, b)
        wall_deltas[policy.decision_index] = wall_deltas.get(policy.decision_index, 0) + len(observed_walls) - before
        return original_observe(policy, observation, owner)

    def timed_frontier(*args):
        before = perf_counter()
        result = original_frontier(*args)
        elapsed = (perf_counter() - before) * 1000
        profile["frontier_ms"] += elapsed
        profile["frontier_calls"] += 1
        profile["frontier_detail"].append({"walls": len(args[2]),
                                           "free_area": args[0].area, "ms": elapsed})
        return result

    def timed_gain(*args):
        before = perf_counter()
        result = original_gain(*args)
        profile["gain_ms"] += (perf_counter() - before) * 1000
        profile["gain_calls"] += 1
        return result

    def select(policy):
        number = len(decisions) + 1
        node = policy.stack[-1]
        record = {
            "decision": number, "position": policy.current,
            "parent_position": policy.stack[-2].position if len(policy.stack) > 1 else None,
            "stack_positions": [item.position for item in policy.stack],
            "stack_candidate_counts": [len(item.candidates) for item in policy.stack],
            "active_branch": node.branch_id, "parent_branch": node.parent_id,
            "known_free_area": policy.known_free.area,
            "unknown_area": policy.border.difference(policy.known_free).area,
            "observed_wall_fragments": len(observed_walls),
            "scan_count": len(policy.scan_positions),
            "current_candidates": list(node.candidates),
        }
        if number <= 2:
            frontier = possible_frontier(policy.known_free, policy.border,
                                         list(observed_walls.values()))
            prepared = prep(policy.known_free.buffer(2 * RAY_MARGIN))
            record["known_free_geometry"] = mapping(policy.known_free)
            record["observed_walls"] = list(observed_walls.values())
            record["candidates"] = [candidate_detail(policy, c, observed_walls, frontier, prepared)
                                    for c in node.candidates]
            record["frontier_length"] = frontier.length
        select_started = perf_counter()
        decision = original_select(policy)
        record["selection_ms"] = (perf_counter() - select_started) * 1000
        record["action"] = decision[0] if decision else "finish"
        record["target"] = (decision[1].position if decision and decision[0] == "recover"
                            else decision[1] if decision else None)
        record["reason"] = policy.last_decision.get("reason")
        record["eligible"] = policy.last_decision.get("eligible")
        record["estimated_gain"] = policy.last_decision.get("estimated_gain")
        record["estimated_travel"] = policy.last_decision.get("estimated_travel")
        decisions.append(record)
        return decision

    ContinuousPolicy.observe = observe
    ContinuousPolicy.select = select
    module.possible_frontier = timed_frontier
    module.visible_frontier_gain = timed_gain
    try:
        episode = simulate_continuous(world, 7, prefer_novelty=True,
                                      complete_frontier_route=True, radar_informed=radar,
                                      trace_decisions=True)
    finally:
        ContinuousPolicy.observe = original_observe
        ContinuousPolicy.select = original_select
        module.possible_frontier = original_frontier
        module.visible_frontier_gain = original_gain
    frames_by_decision = {}
    for frame_number, frame in enumerate(episode["frames"]):
        index = frame.get("decision_index", frame.get("decision", {}).get("index"))
        if index is not None:
            frames_by_decision.setdefault(index, []).append((frame_number, frame))
    for record in decisions:
        frames = frames_by_decision.get(record["decision"], [])
        record["frame_range"] = (f"{frames[0][0]}-{frames[-1][0]}" if frames else "")
        record["executed_distance"] = sum(frame["distance"] for _, frame in frames
                                          if frame["event"] == "move")
        record["new_free_area"] = sum(frame["new_area"] for _, frame in frames
                                      if frame["event"] == "sense")
        record["new_wall_fragments"] = wall_deltas.get(record["decision"], 0)
        plan = next((frame for _, frame in frames if frame["event"] == "plan"), None)
        record["planned_length"] = (path_length([point(p) for p in plan["path"]])
                                    if plan else None)
        record["return_trigger"] = next((frame.get("trigger") for _, frame in frames
                                         if frame["event"] == "recover_start"), None)
    return episode, decisions, profile


def write_trace(path, decisions):
    fields = ("decision", "frame_range", "position", "action", "target", "reason",
              "parent_position", "active_branch", "parent_branch", "known_free_area",
              "unknown_area", "observed_wall_fragments", "scan_count",
              "current_candidates", "stack_candidate_counts", "eligible",
              "estimated_gain", "estimated_travel", "planned_length", "selection_ms",
              "executed_distance", "new_free_area", "new_wall_fragments", "return_trigger")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for decision in decisions:
            writer.writerow({key: decision.get(key) for key in fields})


def main():
    baseline, baseline_decisions, baseline_profile = run(False)
    radar, radar_decisions, radar_profile = run(True)
    for name, decisions in (("baseline", baseline_decisions), ("radar", radar_decisions)):
        write_trace(ROOT / "docs" / f"bar-radar-regression-{name}-trace.csv", decisions)
    first = next((i for i, (a, b) in enumerate(zip(baseline_decisions, radar_decisions))
                  if a["action"] != b["action"] or a["target"] != b["target"]), None)
    assert first is not None, "no divergent decision"
    assert baseline_decisions[first]["position"] == radar_decisions[first]["position"]
    detail = {
        "config": vars(COMPLEX), "radius": 7,
        "start": generate_labyrinth(COMPLEX).world.start,
        "goal": generate_labyrinth(COMPLEX).world.goal,
        "first_divergence_decision": first + 1,
        "baseline": baseline_decisions[first], "radar": radar_decisions[first],
        "episode": {name: {"status": episode["status"], "metrics": episode["metrics"],
                            "recoveries": episode["recoveries"]}
                    for name, episode in (("baseline", baseline), ("radar", radar))},
        "ranking_profile": {"baseline": baseline_profile, "radar": radar_profile},
    }
    output = ROOT / "docs" / "bar-radar-first-divergence.json"
    output.write_text(json.dumps(detail, indent=2), encoding="utf-8")
    print(f"first divergence decision {first+1}: "
          f"{baseline_decisions[first]['target']} vs {radar_decisions[first]['target']}")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
