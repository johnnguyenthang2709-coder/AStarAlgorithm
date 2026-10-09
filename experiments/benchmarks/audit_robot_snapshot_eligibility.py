"""Audit every frozen robot decision against source-defined bundle eligibility."""

import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from collections import Counter

from shapely.geometry import LineString, Polygon

from robot_local_geometry import point_visible, segment_certified


HERE = Path(__file__).resolve().parent
PIN = "8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8"
DATASETS = ("robot-local-benchmark", "robot-local-extension", "robot-local-final-extension")


def map_polygons(path):
    groups, vertices = [], []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if row and row[0].lower() == "x":
                if vertices:
                    groups.append(vertices)
                vertices = []
            elif len(row) == 2:
                vertices.append((float(row[0]), float(row[1])))
    if vertices:
        groups.append(vertices)
    polygons = [Polygon(group) for group in groups]
    if not polygons or not all(p.is_valid and p.area > 0 for p in polygons):
        raise ValueError(f"invalid original map polygons: {path}")
    return polygons


def source_predicate(authors_dir, point, sight, radius):
    if str(authors_dir) not in sys.path:
        sys.path.insert(0, str(authors_dir))
    from Robot_sight_lib import inside_local_sights
    return bool(inside_local_sights(point, sight["center"], radius,
                                    sight["closed_sights"]))


def main():
    authors_dir = (HERE.parents[2] / "AStarAlgorithm-authors-benchmark").resolve()
    revision = subprocess.check_output(["git", "-C", str(authors_dir), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(authors_dir), "status", "--porcelain"], text=True).strip()
    if revision != PIN or status:
        raise ValueError(f"authors' checkout must be clean at {PIN}: {revision}, {status}")
    rows = []
    map_cache = {}
    for dataset in DATASETS:
        directory = HERE / dataset
        manifest = json.loads((directory / "robot-local-benchmark-manifest.json").read_text())
        content = (directory / manifest["snapshot_file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest["snapshot_sha256"]:
            raise ValueError(f"frozen snapshot hash mismatch: {dataset}")
        snapshots = json.loads(content)["snapshots"]
        if len(snapshots) != manifest["captured_decisions"]:
            raise ValueError(f"snapshot count mismatch: {dataset}")
        for snap in snapshots:
            map_name = snap["source_map"]
            if map_name not in map_cache:
                map_path = authors_dir / map_name
                if hashlib.sha256(map_path.read_bytes()).hexdigest() != snap["map_sha256"]:
                    raise ValueError(f"source map hash mismatch: {map_name}")
                map_cache[map_name] = map_polygons(map_path)
            start, target = tuple(snap["start"]), tuple(snap["target"])
            radius = snap["sensor_radius"]
            current = next((s for s in snap["sights"] if tuple(s["center"]) == start), None)
            data_complete = (current is not None and bool(snap["source_graph_edges"])
                             and bool(snap["skeleton_path"]) and bool(snap["asp_path"]))
            source_visible = (source_predicate(authors_dir, target, current, radius)
                              if current is not None else None)
            derived_visible = (point_visible(target, current, radius)
                               if current is not None else None)
            direct_certified = segment_certified(start, target, snap["sights"], radius)[0]
            at_range_boundary = abs(math.dist(start, target) - radius) <= 1e-7
            source_direct_graph_edge = any(
                {tuple(edge[0]), tuple(edge[1])} == {start, target}
                for edge in snap["source_graph_edges"])
            endpoints_match = (bool(snap["asp_path"]) and
                               math.dist(snap["asp_path"][0], start) < 1e-7 and
                               math.dist(snap["asp_path"][-1], target) < 1e-7)
            skeleton_vertices = len(snap["skeleton_path"])
            asp_vertices = len(snap["asp_path"])
            direct_line = LineString((start, target))
            direct_interior = any(direct_line.relate_pattern(p, "T********")
                                  for p in map_cache[map_name])
            direct_boundary = any(direct_line.intersects(p) and
                                  not direct_line.relate_pattern(p, "T********")
                                  for p in map_cache[map_name])
            eligible_by_rule = data_complete and endpoints_match and skeleton_vertices > 2
            listed_eligible = snap["snapshot_id"] in manifest["eligible_ids"]
            if not data_complete:
                reason = "missing_required_planning_data"
            elif not endpoints_match:
                reason = "invalid_planned_path_endpoints"
            elif skeleton_vertices > 2:
                reason = "eligible_nontrivial_bundle"
            elif skeleton_vertices == 2 and source_visible and direct_certified and asp_vertices == 2:
                reason = "direct_target_visible_no_bundle_refinement"
            elif (skeleton_vertices == 2 and at_range_boundary and direct_certified
                  and source_direct_graph_edge and asp_vertices == 2
                  and snap["asp_path"] == snap["skeleton_path"]):
                reason = "direct_target_at_range_boundary_no_bundle_refinement"
            else:
                reason = "other_two_vertex_or_empty_path_requires_review"
            rows.append({
                "dataset": dataset,
                "episode_id": snap.get("episode_id", snap["source_map"]),
                "source_map": snap["source_map"],
                "snapshot_id": snap["snapshot_id"],
                "decision_index_0based": snap["decision_index_0based"],
                "source_iteration": snap["source_iteration"],
                "authors_commit": PIN,
                "start": json.dumps(start), "target": json.dumps(target),
                "sensor_radius": radius,
                "sight_count": len(snap["sights"]),
                "closed_sight_count": sum(len(s["closed_sights"]) for s in snap["sights"]),
                "source_graph_nodes": snap["source_graph_nodes"],
                "source_graph_edges": len(snap["source_graph_edges"]),
                "skeleton_vertices": skeleton_vertices,
                "asp_vertices": asp_vertices,
                "start_target_distance": math.dist(start, target),
                "target_visible_original_predicate": source_visible,
                "target_visible_derived_predicate": derived_visible,
                "direct_segment_sight_certified": direct_certified,
                "target_at_sight_range_boundary": at_range_boundary,
                "source_graph_has_direct_edge": source_direct_graph_edge,
                "direct_line_ground_truth_interior_crossing_offline": direct_interior,
                "direct_line_ground_truth_boundary_contact_offline": direct_boundary,
                "asp_endpoints_match": endpoints_match,
                "data_complete": data_complete,
                "eligible_by_independent_rule": eligible_by_rule,
                "listed_eligible_in_frozen_manifest": listed_eligible,
                "eligibility_checker_mismatch": eligible_by_rule != listed_eligible,
                "primary_reason": reason,
                "secondary_reasons": (
                    "two_vertex_skeleton;two_vertex_asp;current_sight_target_visible"
                    if reason == "direct_target_visible_no_bundle_refinement" else
                    "two_vertex_skeleton;two_vertex_asp;source_direct_graph_edge;strict_radius_boundary"
                    if reason == "direct_target_at_range_boundary_no_bundle_refinement" else ""),
                "scientifically_comparable_as_direct_path": reason in (
                    "direct_target_visible_no_bundle_refinement",
                    "direct_target_at_range_boundary_no_bundle_refinement"),
                "excluded_by_predefined_nontrivial_protocol": (not listed_eligible),
                "source_episode_goal_reached": snap.get("source_episode_status", {}).get("reach_goal", ""),
            })
    if len({row["snapshot_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate frozen snapshot IDs")
    out = HERE / "robot-snapshot-eligibility-audit.csv"
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    reasons = Counter(row["primary_reason"] for row in rows)
    summary = {
        "authors_commit": PIN,
        "datasets": {name: {"captured": sum(row["dataset"] == name for row in rows),
                             "eligible": sum(row["dataset"] == name and row["eligible_by_independent_rule"] for row in rows),
                             "excluded": sum(row["dataset"] == name and not row["eligible_by_independent_rule"] for row in rows)}
                     for name in DATASETS},
        "original_two_cohorts": {
            "captured": sum(row["dataset"] != "robot-local-final-extension" for row in rows),
            "eligible": sum(row["dataset"] != "robot-local-final-extension" and
                            row["eligible_by_independent_rule"] for row in rows),
            "excluded": sum(row["dataset"] != "robot-local-final-extension" and
                            not row["eligible_by_independent_rule"] for row in rows),
            "primary_reasons": dict(sorted(Counter(row["primary_reason"] for row in rows
                                                   if row["dataset"] != "robot-local-final-extension").items())),
        },
        "captured": len(rows),
        "eligible": sum(row["eligible_by_independent_rule"] for row in rows),
        "excluded": sum(not row["eligible_by_independent_rule"] for row in rows),
        "primary_reasons": dict(sorted(reasons.items())),
        "source_derived_visibility_disagreements": sum(
            row["target_visible_original_predicate"] != row["target_visible_derived_predicate"] for row in rows),
        "disagreements_explained_by_strict_radius_boundary": sum(
            row["target_visible_original_predicate"] != row["target_visible_derived_predicate"]
            and row["primary_reason"] == "direct_target_at_range_boundary_no_bundle_refinement"
            for row in rows),
        "eligibility_checker_mismatches": sum(row["eligibility_checker_mismatch"] for row in rows),
        "missing_data": reasons["missing_required_planning_data"],
        "invalid_endpoints": reasons["invalid_planned_path_endpoints"],
        "geometry_or_information_incompatibility": reasons["other_two_vertex_or_empty_path_requires_review"],
        "excluded_but_direct_path_comparable": (
            reasons["direct_target_visible_no_bundle_refinement"] +
            reasons["direct_target_at_range_boundary_no_bundle_refinement"]),
        "excluded_direct_paths_with_ground_truth_interior_crossing": sum(
            not row["eligible_by_independent_rule"] and
            row["direct_line_ground_truth_interior_crossing_offline"] for row in rows),
        "excluded_direct_paths_with_ground_truth_boundary_contact": sum(
            not row["eligible_by_independent_rule"] and
            row["direct_line_ground_truth_boundary_contact_offline"] for row in rows),
        "selection_uses_method_outcome": False,
    }
    (HERE / "robot-snapshot-eligibility-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
