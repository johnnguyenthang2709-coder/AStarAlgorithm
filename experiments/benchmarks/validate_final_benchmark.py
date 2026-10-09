"""Independent consistency gate for the frozen final academic artifacts."""

import csv
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE.parents[2] / "AStarAlgorithm-authors-benchmark"


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def good(value):
    return value == "True"


def main():
    summary = json.loads((HERE / "benchmark-final-summary.json").read_text())
    eligibility = json.loads((HERE / "robot-snapshot-eligibility-summary.json").read_text())
    original = eligibility["original_two_cohorts"]
    audit = rows(HERE / "robot-snapshot-eligibility-audit.csv")
    assert (original["captured"], original["eligible"], original["excluded"]) == (118, 7, 111)
    assert original["primary_reasons"]["direct_target_visible_no_bundle_refinement"] == 61
    assert original["primary_reasons"]["direct_target_at_range_boundary_no_bundle_refinement"] == 50
    assert len(audit) == 351 and len({r["snapshot_id"] for r in audit}) == len(audit)
    assert not any(r["eligibility_checker_mismatch"] == "True" for r in audit)
    assert not any(r["primary_reason"].startswith("other_") for r in audit)
    assert not any(r["primary_reason"] in {"missing_required_planning_data", "invalid_planned_path_endpoints"} for r in audit)
    assert all(r["direct_segment_sight_certified"] == "True" for r in audit
               if r["primary_reason"].startswith("direct_target"))
    assert all(r["direct_line_ground_truth_interior_crossing_offline"] == "False" for r in audit
               if r["primary_reason"].startswith("direct_target"))
    assert summary["robot"]["captured"] == len(audit) == 351
    assert summary["robot"]["eligible"] == 21
    assert summary["robot"]["excluded"] == 330
    pairs = rows(HERE / "robot-local-final-paired.csv")
    assert len(pairs) == 21
    assert {r["snapshot_id"] for r in pairs} == {r["snapshot_id"] for r in audit
                                             if r["eligible_by_independent_rule"] == "True"}
    assert all(good(r["asp_found"]) and good(r["astar_found"]) for r in pairs)
    assert all(good(r["asp_interior_only_valid"]) and good(r["astar_interior_only_valid"]) for r in pairs)
    assert sum(good(r["asp_strict_boundary_valid"]) for r in pairs) == 15
    assert sum(good(r["astar_strict_boundary_valid"]) for r in pairs) == 21
    differences = [float(r["astar_planned_length"]) - float(r["asp_planned_length"]) for r in pairs]
    assert all(abs(delta - float(r["astar_minus_asp_length"])) < 1e-7 for delta, r in zip(differences,pairs))
    assert (sum(d>1e-7 for d in differences),sum(d<-1e-7 for d in differences),
            sum(abs(d)<=1e-7 for d in differences)) == (9,10,2)
    assert abs(statistics.median(differences) - summary["robot"]["paired_length_difference_astar_minus_asp"]["median"]) < 1e-9
    for cohort in ("robot-local-benchmark", "robot-local-extension", "robot-local-final-extension"):
        folder=HERE/cohort
        manifest=json.loads((folder/"robot-local-benchmark-manifest.json").read_text())
        assert sha(folder/manifest["snapshot_file"]) == manifest["snapshot_sha256"]
        assert set(manifest["eligible_ids"]) == {r["snapshot_id"] for r in pairs if r["cohort"]==cohort}
        validation=json.loads((folder/"robot-local-validation-summary.json").read_text())
        assert validation["graph_edge_interior_crossings"] == 0
        assert validation["original_asp_segments_uncertified"] == 0
        assert validation["geometry_equivalence"]["source_derived_membership_mismatches"] == 0
    road=rows(HERE/"road-astar-dijkstra.csv")
    assert len(road)==360 and summary["road"]["pairs"]==180
    assert summary["road"]["equal_cost"]==summary["road"]["astar_fewer_expansions"]==180
    assert summary["road"]["astar_faster"]+summary["road"]["dijkstra_faster"]==180
    road_validation=json.loads((HERE/"road-validation.json").read_text())
    assert road_validation["heuristic_edge_violations"]==0
    assert road_validation["cost_equal_pairs"]==180
    supporting=json.loads((HERE/"supporting-validation.json").read_text())
    assert supporting["ablation"]["radar_shorter"]==summary["supporting"]["radar_shorter"]==18
    assert supporting["cache"]["playback_equivalent"]==summary["supporting"]["cache_equivalent"]==20
    assert supporting["sensor"]["success"]==summary["supporting"]["sensor_goal_success"]==12
    assert subprocess.check_output(["git","-C",str(SOURCE),"rev-parse","HEAD"],text=True).strip()==eligibility["authors_commit"]
    assert not subprocess.check_output(["git","-C",str(SOURCE),"status","--porcelain"],text=True).strip()
    checked_links=0
    for doc_name in ("FINAL-BENCHMARK-REPORT.md", "FINAL-BENCHMARK-SUMMARY.md",
                     "benchmark-data-dictionary.md"):
        document=(HERE/doc_name).read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)]+)\)",document):
            if "://" not in link and not link.startswith("#"):
                assert (HERE/link).exists(), f"broken {doc_name} link: {link}"
                checked_links+=1
    figures=list((HERE/"final-figures").glob("*"))
    assert len(figures)==14 and all(path.stat().st_size>1000 for path in figures)
    assert all((HERE/"tables"/name).exists() for name in
               ("road-results.tex","robot-local-results.tex","supporting-results.tex"))
    road_tex=(HERE/"tables/road-results.tex").read_text(encoding="utf-8")
    for kind, values in summary["road"]["strata"].items():
        assert (f"{kind.title()} & {values['n']} & {values['median_astar_expanded']:.1f} & "
                f"{values['median_dijkstra_expanded']:.1f}") in road_tex
        assert f"{values['median_paired_time_ratio']:.3f}" in road_tex
    robot_tex=(HERE/"tables/robot-local-results.tex").read_text(encoding="utf-8")
    for cohort, values in summary["robot"]["cohorts"].items():
        v=values["validation"]
        assert (f"{cohort} & {values['captured']} & {values['eligible']} & "
                f"{v['asp_shorter']} & {v['astar_shorter']}") in robot_tex
    support_tex=(HERE/"tables/supporting-results.tex").read_text(encoding="utf-8")
    assert f"Radar shorter in {summary['supporting']['radar_shorter']}" in support_tex
    assert f"{summary['supporting']['cache_median_cached_frontier_ms']:.2f}" in support_tex
    manifest_path=HERE/"benchmark-final-manifest.json"
    if manifest_path.exists():
        final_manifest=json.loads(manifest_path.read_text())
        for rel, expected in final_manifest["artifact_sha256"].items():
            assert sha(HERE/rel)==expected, f"final artifact hash mismatch: {rel}"
    print(json.dumps({"status":"PASS","source_clean":True,"road_pairs":180,
                      "robot_snapshots":351,"robot_pairs":21,"figures":len(figures),
                      "local_document_links_checked":checked_links},indent=2))


if __name__=="__main__":
    main()
