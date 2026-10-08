"""Read-only decision trace for the Maze 3 narrow-terminal equivalent.

Monkeypatches select only while the simulation runs, then compares the emitted
frames with an uninstrumented run. No navigation state or search result changes.
"""

import csv
import json
import sys
from pathlib import Path

from shapely.geometry import Point as ShapePoint

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import ContinuousPolicy, path_length, simulate_continuous
from app.services.bar_labyrinth import BLIND_ALLEY, generate_labyrinth


def xy(value):
    return (value["x"], value["y"]) if isinstance(value, dict) else value


def candidate_snapshot(policy, node):
    rows = []
    for candidate in node.candidates:
        key = policy.candidate_key(candidate)
        potential = ShapePoint(candidate).buffer(policy.radius, quad_segs=12).intersection(policy.border)
        rows.append({"x": round(candidate[0], 6), "y": round(candidate[1], 6),
                     "valid": policy._candidate_valid(candidate),
                     "deferred": not policy.graph_changed_since(policy.deferred.get(key)),
                     "unknown_disk_area": round(potential.difference(policy.known_free).area, 6)})
    return rows


def main():
    world = generate_labyrinth(BLIND_ALLEY).world
    original = ContinuousPolicy.select
    original_plan = ContinuousPolicy.plan
    decisions = []

    def observed_select(policy):
        active = policy.stack[-1]
        stack = [{"x": round(node.position[0], 6), "y": round(node.position[1], 6),
                  "history_index": node.history_index, "candidate_count": len(node.candidates),
                  "available": sum(policy._candidate_valid(point) and
                                   policy.graph_changed_since(policy.deferred.get(policy.candidate_key(point)))
                                   for point in node.candidates)} for node in policy.stack]
        candidates = candidate_snapshot(policy, active)
        first_frame = len(policy.frames) - 1
        known_area = policy.known_free.area
        outcome = original(policy)
        action, value = outcome if outcome else ("terminate", None)
        decisions.append({"decision": len(decisions) + 1, "first_frame": first_frame,
                          "position": policy.current, "stack": stack,
                          "known_free_area": known_area,
                          "scan_count": len(policy.scan_positions),
                          "verified_links": len(policy.verified_links),
                          "active_candidates": candidates,
                          "action": action,
                          "target": value.position if action == "recover" else value})
        return outcome

    def observed_plan(policy, target):
        result = original_plan(policy, target)
        decisions[-1]["astar_found"] = result["found"]
        decisions[-1]["graph_nodes"] = result["nodes"]
        decisions[-1]["graph_edges"] = result["edges"]
        return result

    ContinuousPolicy.select = observed_select
    ContinuousPolicy.plan = observed_plan
    try:
        episode = simulate_continuous(world, 5, prefer_novelty=True,
                                      complete_frontier_route=True)
    finally:
        ContinuousPolicy.select = original
        ContinuousPolicy.plan = original_plan
    baseline = simulate_continuous(world, 5, prefer_novelty=True,
                                   complete_frontier_route=True)
    if episode["frames"] != baseline["frames"] or episode["status"] != baseline["status"]:
        raise AssertionError("audit instrumentation changed the navigation trace")

    frames = episode["frames"]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("decision", "frames", "position", "action", "selected_target",
                     "parent_anchor", "parent_available", "selected_return_anchor_available",
                     "ancestry", "stack_depth", "active_valid_candidates",
                     "active_candidate_details", "known_free_area", "scan_count",
                     "observed_wall_fragments_at_decision", "astar_found", "graph_nodes",
                     "graph_edges", "verified_link_change", "planned_length", "executed_distance",
                     "movement", "new_free_area_after_move", "new_scan_positions",
                     "return_trigger", "fallback", "episode_status"))
    for index, item in enumerate(decisions):
        start = item["first_frame"]
        end = (decisions[index + 1]["first_frame"] - 1
               if index + 1 < len(decisions) else len(frames) - 1)
        interval = frames[start:end + 1]
        plans = [frame for frame in interval if frame["event"] == "plan"]
        returns = [frame for frame in interval if frame["event"] == "recover_start"]
        moves = [frame for frame in interval if frame["event"] == "move"]
        next_sense = (frames[decisions[index + 1]["first_frame"]]
                      if index + 1 < len(decisions) else None)
        # The next loop's sense occurs after the preceding exploration move.
        gained = sum(frame.get("new_area", 0) for frame in interval[1:]
                     if frame["event"] == "sense")
        if moves and item["action"] == "explore" and next_sense:
            gained += next_sense.get("new_area", 0)
        plan = plans[0] if plans else None
        recovery = returns[0] if returns else None
        route = plan["path"] if plan else recovery["path"] if recovery else []
        prior_scan_count = item["scan_count"]
        next_scan_count = (decisions[index + 1]["scan_count"]
                           if index + 1 < len(decisions) else prior_scan_count)
        next_link_count = (decisions[index + 1]["verified_links"]
                           if index + 1 < len(decisions) else item["verified_links"])
        parent = item["stack"][-2] if len(item["stack"]) > 1 else None
        selected_ancestor = next((node for node in item["stack"]
                                  if item["action"] == "recover" and
                                  (node["x"], node["y"]) ==
                                  (round(item["target"][0], 6), round(item["target"][1], 6))), None)
        candidate_details = json.dumps(item["active_candidates"], separators=(",", ":"))
        writer.writerow((item["decision"], f"{start}-{end}",
                         json.dumps(item["position"]), item["action"],
                         json.dumps(item["target"]),
                         json.dumps((parent["x"], parent["y"])) if parent else "",
                         parent["available"] if parent else "",
                         selected_ancestor["available"] if selected_ancestor else "",
                         json.dumps(item["stack"], separators=(",", ":")),
                         len(item["stack"]),
                         sum(row["valid"] and not row["deferred"]
                             for row in item["active_candidates"]),
                         candidate_details, f"{item['known_free_area']:.6f}",
                         prior_scan_count,
                         len(frames[start].get("obstacle_edges", [])),
                         item.get("astar_found", ""), item.get("graph_nodes", ""),
                         item.get("graph_edges", ""), next_link_count - item["verified_links"],
                         f"{path_length([xy(p) for p in route]):.6f}" if route else "",
                         f"{sum(frame['distance'] for frame in moves):.6f}",
                         json.dumps([[xy(frame["from"]), xy(frame["position"]), frame["phase"]]
                                     for frame in moves], separators=(",", ":")),
                         f"{gained:.6f}" if moves else "",
                         next_scan_count - prior_scan_count,
                         recovery.get("trigger", "") if recovery else "",
                         recovery.get("fallback", "") if recovery else "",
                         episode["status"]))


if __name__ == "__main__":
    main()
