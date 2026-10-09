"""Validate frozen benchmark rows and render final, raw-data-traceable artifacts."""

import csv
import hashlib
import json
import math
import shutil
import statistics as st
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIG = HERE / "final-figures"
TABLES = HERE / "tables"
COHORTS = ("robot-local-benchmark", "robot-local-extension", "robot-local-final-extension")
plt.rcParams["svg.hashsalt"] = "academic-benchmark-final"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median(values):
    return st.median(values) if values else None


def mean(values):
    return st.mean(values) if values else None


def number(value):
    return float(value)


def true(value):
    return value is True or value == "True"


def fig(name, title, xlabel=None, ylabel=None):
    plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    plt.tight_layout()
    path = FIG / f"{name}.svg"
    plt.savefig(path, bbox_inches="tight", metadata={"Date": None})
    plt.close()
    # Matplotlib writes formatting spaces after multiline SVG path commands.
    # Normalize those without changing geometry or text for clean diffs.
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n",
                    encoding="utf-8")


def road():
    baseline = json.loads((HERE / "benchmark-manifest.json").read_text(encoding="utf-8"))
    graph_path = ROOT / "data/road/graph.json"
    assert digest(graph_path) == baseline["road"]["graph_sha256"]
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    rows = read_csv(HERE / "road-astar-dijkstra.csv")
    grouped = defaultdict(dict)
    for row in rows:
        key = int(row["pair_id"])
        assert row["algorithm"] not in grouped[key]
        grouped[key][row["algorithm"]] = row
    assert len(grouped) == 180 and len(rows) == 360
    pairs = []
    for pair_id in sorted(grouped):
        pair = grouped[pair_id]
        assert set(pair) == {"astar", "dijkstra"}
        a, d = pair["astar"], pair["dijkstra"]
        assert (a["start"], a["goal"], a["stratum"]) == (d["start"], d["goal"], d["stratum"])
        assert abs(number(a["cost_m"]) - number(d["cost_m"])) <= 1e-6
        assert abs(number(a["cost_m"]) - number(a["offline_cost_m"])) <= 1e-6
        pairs.append((a, d))
    assert Counter(a["stratum"] for a, _ in pairs) == {"short": 60, "medium": 60, "long": 60}
    expanded_ratio = [number(a["expanded_nodes"]) / number(d["expanded_nodes"]) for a, d in pairs]
    time_ratio = [number(a["median_search_us"]) / number(d["median_search_us"]) for a, d in pairs]
    results = {
        "pairs": 180,
        "equal_cost": 180,
        "astar_fewer_expansions": sum(x < 1 for x in expanded_ratio),
        "astar_faster": sum(x < 1 for x in time_ratio),
        "dijkstra_faster": sum(x > 1 for x in time_ratio),
        "median_paired_expansion_reduction_fraction": median([1-x for x in expanded_ratio]),
        "median_paired_search_time_ratio": median(time_ratio),
        "mean_paired_search_time_ratio": mean(time_ratio),
        "search_time_ratio_range": [min(time_ratio), max(time_ratio)],
        "worst_astar_time_ratio": {"pair_id": int(pairs[max(range(180), key=lambda i: time_ratio[i])][0]["pair_id"]),
                                   "ratio": max(time_ratio)},
        "strata": {},
    }
    for kind in ("short", "medium", "long"):
        group = [(a, d) for a, d in pairs if a["stratum"] == kind]
        results["strata"][kind] = {
            "n": len(group),
            "median_astar_expanded": median([int(a["expanded_nodes"]) for a, _ in group]),
            "median_dijkstra_expanded": median([int(d["expanded_nodes"]) for _, d in group]),
            "median_paired_expansion_reduction_fraction": median([1-int(a["expanded_nodes"])/int(d["expanded_nodes"]) for a,d in group]),
            "median_astar_search_us": median([number(a["median_search_us"]) for a, _ in group]),
            "median_dijkstra_search_us": median([number(d["median_search_us"]) for _, d in group]),
            "median_paired_time_ratio": median([number(a["median_search_us"])/number(d["median_search_us"]) for a,d in group]),
        }
    for field, title, label, name in (
        ("expanded_nodes", "Road search effort, 180 matched queries", "Expanded nodes", "road-expanded"),
        ("median_search_us", "Road search time, 180 matched queries", "Search time per call (µs)", "road-search-time"),
    ):
        plt.figure(figsize=(6.5, 5.5))
        for kind, color in (("short", "#2d7181"), ("medium", "#b4772d"), ("long", "#795889")):
            group = [(a,d) for a,d in pairs if a["stratum"] == kind]
            plt.scatter([number(d[field]) for _,d in group], [number(a[field]) for a,_ in group],
                        s=20, alpha=.75, color=color, label=f"{kind} (n=60)")
        bound = max(number(d[field]) for _, d in pairs) * 1.03
        plt.plot([0,bound],[0,bound],"--",color="#666",linewidth=1,label="equal")
        plt.xlim(0,bound); plt.ylim(0,bound); plt.legend(frameon=False)
        fig(name,title,f"Dijkstra {label}",f"A* {label}")
    plt.figure(figsize=(7,3.5))
    plt.scatter(range(180), [number(a["cost_m"])-number(d["cost_m"]) for a,d in pairs],s=10,color="#2d7181")
    plt.axhline(0,color="#555",linewidth=1)
    fig("road-cost-agreement","Optimal directed-road cost agreement","Frozen pair ID","A* − Dijkstra cost (m)")
    # The plotting runtime has Matplotlib (Python 3.14); the existing compiled
    # C++ extension is built for the project's Python 3.12 virtual environment.
    # Ask that unmodified extension for each plotted route, rather than
    # implementing a separate route algorithm inside the figure script.
    route_python = ROOT / ".venv/Scripts/python.exe"
    route_code = (
        "import json,sys;sys.path.insert(0,sys.argv[1]);import astar_core;"
        "e=astar_core.RoadEngine(sys.argv[2]);"
        "r=astar_core.road_compare(e,int(sys.argv[3]),int(sys.argv[4]),False);"
        "print(json.dumps(r,ensure_ascii=True))"
    )
    plt.figure(figsize=(8.5,7.0))
    for edge in graph["edges"]:
        geom=edge["geometry"]
        plt.plot([p[0] for p in geom],[p[1] for p in geom],color="#c5c9c8",linewidth=.25,alpha=.7)
    for idx,color in ((0,"#126582"),(60,"#b46a2b"),(120,"#783f8b")):
        a,_=pairs[idx]
        result=json.loads(subprocess.check_output([
            str(route_python),"-c",route_code,str(ROOT/"backend"),str(graph_path),
            a["start"],a["goal"]],text=True))
        assert result["same_optimal_cost"]
        geom=result["astar"]["route"]["geometry"]
        assert abs(result["astar"]["route"]["cost_m"]-number(a["cost_m"]))<1e-6
        plt.plot([p["lon"] for p in geom],[p["lat"] for p in geom],color=color,linewidth=2,
                 label=f"{a['stratum']} pair {idx}")
        plt.scatter([geom[0]["lon"],geom[-1]["lon"]],[geom[0]["lat"],geom[-1]["lat"]],color=color,s=17)
    plt.axis("equal");plt.legend(frameon=True,fontsize=8)
    fig("road-representative-routes","Representative routes on the directed road graph","Longitude (°)","Latitude (°)")
    return results


def robot():
    pooled=[]; cohorts={}; all_eligible=set()
    for cohort in COHORTS:
        folder=HERE/cohort
        manifest=json.loads((folder/"robot-local-benchmark-manifest.json").read_text())
        content=(folder/manifest["snapshot_file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest()==manifest["snapshot_sha256"]
        snaps=json.loads(content)["snapshots"]
        rows=read_csv(folder/"robot-local-asp-vs-astar.csv")
        summary=json.loads((folder/"robot-local-validation-summary.json").read_text())
        assert len(snaps)==manifest["captured_decisions"]==summary["captured"]
        assert len(rows)==manifest["eligible_decisions"]==summary["eligible"]
        assert {r["snapshot_id"] for r in rows}==set(manifest["eligible_ids"])
        assert all(len(s["skeleton_path"])>2 for s in snaps if s["snapshot_id"] in manifest["eligible_ids"])
        assert all(len(s["skeleton_path"])<=2 for s in snaps if s["snapshot_id"] not in manifest["eligible_ids"])
        assert all(r["snapshot_id"] not in all_eligible for r in rows)
        all_eligible.update(r["snapshot_id"] for r in rows)
        for row in rows:
            pooled.append({"cohort":cohort,**row})
        cohorts[cohort]={"captured":len(snaps),"eligible":len(rows),"excluded":len(snaps)-len(rows),
                         "source_goal_reached":sum(bool(o.get("reach_goal")) for o in manifest.get("episode_outcomes",[])),
                         "source_episodes":len(manifest.get("episode_outcomes",[])),
                         "validation":summary,
                         "snapshot_sha256":manifest["snapshot_sha256"]}
    assert len(pooled)==sum(v["eligible"] for v in cohorts.values())
    observed = HERE / "robot-local-final-extension/P01-_map_deadend-07-observed.png"
    assert observed.exists()
    shutil.copyfile(observed, FIG / "robot-observed-paths.png")
    path=HERE/"robot-local-final-paired.csv"
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=pooled[0].keys())
        writer.writeheader();writer.writerows(pooled)
    diffs=[number(r["astar_minus_asp_length"]) for r in pooled if r["asp_found"]==r["astar_found"]=="True"]
    turn_diffs=[int(r["astar_minus_asp_turns"]) for r in pooled if r["asp_found"]==r["astar_found"]=="True"]
    asp_core=[number(r["asp_core_median_ms"]) for r in pooled]
    build=[number(r["astar_build_median_ms"]) for r in pooled]
    search=[number(r["astar_core_median_ms"]) for r in pooled]
    results={
        "cohorts":cohorts,"captured":sum(v["captured"] for v in cohorts.values()),
        "eligible":len(pooled),"excluded":sum(v["excluded"] for v in cohorts.values()),
        "distinct_maps":sorted({r["source_map"] for r in pooled}),
        "both_found":len(diffs),"asp_failures":sum(not true(r["asp_found"]) for r in pooled),
        "astar_failures":sum(not true(r["astar_found"]) for r in pooled),
        "asp_shorter":sum(d>1e-7 for d in diffs),"astar_shorter":sum(d<-1e-7 for d in diffs),
        "equal_length":sum(abs(d)<=1e-7 for d in diffs),
        "paired_length_difference_astar_minus_asp":{"mean":mean(diffs),"median":median(diffs),"min":min(diffs),"max":max(diffs)},
        "paired_turn_difference_astar_minus_asp":{"mean":mean(turn_diffs),"median":median(turn_diffs)},
        "asp_interior_valid":sum(true(r["asp_interior_only_valid"]) for r in pooled),
        "astar_interior_valid":sum(true(r["astar_interior_only_valid"]) for r in pooled),
        "asp_strict_valid":sum(true(r["asp_strict_boundary_valid"]) for r in pooled),
        "astar_strict_valid":sum(true(r["astar_strict_boundary_valid"]) for r in pooled),
        "asp_radius_0_5_clearance_diagnostic":sum(true(r["asp_radius_0_5_clearance_valid"]) for r in pooled),
        "astar_radius_0_5_clearance_diagnostic":sum(true(r["astar_radius_0_5_clearance_valid"]) for r in pooled),
        "median_asp_core_ms":median(asp_core),"median_astar_graph_build_ms":median(build),
        "median_astar_cpp_binding_ms":median(search),
        "median_astar_build_plus_call_ms":median([a+b for a,b in zip(build,search)]),
        "worst_absolute_length_difference_snapshot":max(pooled,key=lambda r:abs(number(r["astar_minus_asp_length"])))["snapshot_id"],
    }
    labels=[r["snapshot_id"] for r in pooled]
    x=list(range(len(pooled)))
    for name,a_field,b_field,ylabel,title in (
        ("robot-paired-lengths","asp_planned_length","astar_planned_length","Planned length (world units)","Frozen local paths; identical endpoints and sights"),
        ("robot-paired-turns","asp_turns_over_15deg","astar_turns_over_15deg","Turns >15°","Geometric turns in frozen local plans"),
    ):
        plt.figure(figsize=(max(9,len(x)*.48),4.7))
        plt.bar([i-.18 for i in x],[number(r[a_field]) for r in pooled],.36,label="Authors' ASP",color="#b4772d")
        plt.bar([i+.18 for i in x],[number(r[b_field]) for r in pooled],.36,label="Our visibility A*",color="#2d7181")
        plt.xticks(x,labels,rotation=75,ha="right",fontsize=7);plt.legend(frameon=False)
        fig(name,title,"Frozen snapshot ID",ylabel)
    plt.figure(figsize=(6.5,4.5))
    positions=[0,1]
    plt.bar([p-.18 for p in positions],[results["asp_interior_valid"],results["asp_strict_valid"]],.36,label="Authors' ASP",color="#b4772d")
    plt.bar([p+.18 for p in positions],[results["astar_interior_valid"],results["astar_strict_valid"]],.36,label="Our visibility A*",color="#2d7181")
    plt.xticks(positions,["Interior-only point robot","Strict boundary avoidance"]);plt.ylim(0,len(pooled)+1);plt.legend(frameon=False)
    fig("robot-validity","Planned-path validity by explicit collision convention",ylabel="Valid paths (count)")
    plt.figure(figsize=(7,4.3))
    names=list(cohorts)
    eligible=[cohorts[c]["eligible"] for c in names]
    excluded=[cohorts[c]["excluded"] for c in names]
    plt.bar(names,eligible,label="Nontrivial bundle eligible",color="#2d7181")
    plt.bar(names,excluded,bottom=eligible,label="Direct local path excluded",color="#c5c9c8")
    plt.xticks(rotation=15,ha="right");plt.legend(frameon=False)
    fig("robot-eligibility","Prespecified source decisions and bundle eligibility",ylabel="Captured decisions")
    plt.figure(figsize=(max(9,len(x)*.48),4.7))
    plt.scatter(x,asp_core,label="Authors' Python ASP core",color="#b4772d",marker="o")
    plt.scatter(x,build,label="Our sight-link graph construction",color="#795889",marker="s")
    plt.scatter(x,search,label="Our C++ A* binding and search",color="#2d7181",marker="^")
    plt.yscale("log");plt.xticks(x,labels,rotation=75,ha="right",fontsize=7);plt.legend(frameon=False)
    fig("robot-runtime-components","Local planning component timings; different language and scope","Frozen snapshot ID","Per-snapshot median wall time (ms; log scale)")
    return results


def supporting():
    radar=read_csv(HERE/"exploration-ablation.csv")
    cache=read_csv(HERE/"frontier-cache.csv")
    sensor=read_csv(HERE/"sensor-robustness.csv")
    def group(rows,key,variant):
        grouped=defaultdict(dict)
        for row in rows:
            k=tuple(row[field] for field in key)
            assert row[variant] not in grouped[k]
            grouped[k][row[variant]]=row
        return grouped
    rp=group(radar,("case","radius"),"policy")
    cp=group(cache,("case","radius"),"variant")
    sp=group(sensor,("kind","case"),"radius")
    assert len(rp)==20 and len(cp)==20 and len(sp)==6
    assert all(set(p)=={"baseline","radar"} for p in rp.values())
    assert all(set(p)=={"full","cached"} and true(p["cached"]["equivalent_to_full"]) for p in cp.values())
    assert all(set(p)=={"5","7"} for p in sp.values())
    deltas=[number(p["radar"]["executed_distance"])-number(p["baseline"]["executed_distance"]) for p in rp.values()]
    result={"radar_pairs":20,"radar_shorter":sum(d<0 for d in deltas),"radar_longer":sum(d>0 for d in deltas),
            "radar_median_paired_distance_delta":median(deltas),
            "radar_largest_regression":max(deltas),
            "cache_pairs":20,"cache_equivalent":20,
            "cache_median_full_frontier_ms":median([number(p["full"]["frontier_total_ms"]) for p in cp.values()]),
            "cache_median_cached_frontier_ms":median([number(p["cached"]["frontier_total_ms"]) for p in cp.values()]),
            "sensor_episodes":12,"sensor_goal_success":sum(true(r["success"]) for r in sensor),
            "sensor_median_radius5_distance":median([number(p["5"]["executed_distance"]) for p in sp.values()]),
            "sensor_median_radius7_distance":median([number(p["7"]["executed_distance"]) for p in sp.values()])}
    plt.figure(figsize=(6.5,5))
    plt.scatter([number(p["baseline"]["executed_distance"]) for p in rp.values()],
                [number(p["radar"]["executed_distance"]) for p in rp.values()],color="#2d7181")
    bound=max(number(r["executed_distance"]) for r in radar)*1.05
    plt.plot([0,bound],[0,bound],"--",color="#555");plt.xlim(0,bound);plt.ylim(0,bound)
    fig("support-radar","Online exploration, 20 paired configurations","Legacy executed distance (world units)","Radar executed distance (world units)")
    plt.figure(figsize=(6.5,5))
    plt.scatter([number(p["full"]["frontier_total_ms"]) for p in cp.values()],
                [number(p["cached"]["frontier_total_ms"]) for p in cp.values()],color="#2d7181")
    bound=max(number(p["full"]["frontier_total_ms"]) for p in cp.values())*1.05
    plt.plot([0,bound],[0,bound],"--",color="#555");plt.xlim(0,bound);plt.ylim(0,bound)
    fig("support-frontier-cache","Frontier construction, identical playback in 20 pairs","Full frontier time (ms)","Cached frontier time (ms)")
    plt.figure(figsize=(8,4.4)); names=[f"{k[0]}:{k[1]}" for k in sp]; x=list(range(len(sp)))
    plt.bar([i-.18 for i in x],[number(p["5"]["executed_distance"]) for p in sp.values()],.36,label="Radius 5",color="#2d7181")
    plt.bar([i+.18 for i in x],[number(p["7"]["executed_distance"]) for p in sp.values()],.36,label="Radius 7",color="#b4772d")
    plt.xticks(x,names,rotation=25,ha="right");plt.legend(frameon=False)
    fig("support-sensor-radius","Six matched online-navigation scenarios","Scenario","Executed distance (world units)")
    returns=read_csv(ROOT/"docs/bar-indoor-radar-trace.csv")
    verified=[r for r in returns if true(r["bound_verified"]) and not true(r["fallback"])]
    assert verified
    chosen=verified[:8]
    plt.figure(figsize=(8,4));x=list(range(len(chosen)))
    plt.bar([i-.18 for i in x],[number(r["entry_length"]) for r in chosen],.36,label="Recorded entry",color="#b4772d")
    plt.bar([i+.18 for i in x],[number(r["executed_return_length"]) for r in chosen],.36,label="A*-planned executed return",color="#2d7181")
    plt.xticks(x,[f"{r['branch']}→{r['parent']}" for r in chosen],rotation=25,ha="right");plt.legend(frameon=False)
    fig("support-parent-return","Representative certified observed parent returns","Branch → observed parent","Geometric length (world units)")
    result["parent_trace_rows"]=len(returns)
    result["certified_nonfallback_returns"]=len(verified)
    return result


def write_tables(data):
    road_rows=[]
    for kind, value in data["road"]["strata"].items():
        road_rows.append(
            f"{kind.title()} & {value['n']} & {value['median_astar_expanded']:.1f} & "
            f"{value['median_dijkstra_expanded']:.1f} & "
            f"{100*value['median_paired_expansion_reduction_fraction']:.1f}\\% & "
            f"{value['median_astar_search_us']:.2f} & "
            f"{value['median_dijkstra_search_us']:.2f} & "
            f"{value['median_paired_time_ratio']:.3f} \\\\"
        )
    road_tex=(
        "\\begin{table}[t]\n\\centering\n\\caption{Frozen directed-road A* versus Dijkstra. "
        "Times are C++ search-call medians in microseconds; reductions and ratios are medians "
        "of paired values, so they need not equal ratios of column medians.}\n"
        "\\label{tab:road-final}\n"
        "\\begin{tabular}{lrrrrrrr}\n\\hline\n"
        "Stratum & $n$ & A* expanded & Dijkstra expanded & Paired reduction & "
        "A* $\\mu$s & Dijkstra $\\mu$s & Paired time ratio \\\\\n\\hline\n"
        +"\n".join(road_rows)+"\n\\hline\n\\end{tabular}\n\\end{table}\n"
    )
    (TABLES/"road-results.tex").write_text(road_tex,encoding="utf-8")
    robot_rows=[]
    for cohort, value in data["robot"]["cohorts"].items():
        v=value["validation"]
        robot_rows.append(
            f"{cohort.replace('_', r'\\_')} & {value['captured']} & {value['eligible']} & "
            f"{v['asp_shorter']} & {v['astar_shorter']} & "
            f"{v['asp_interior_valid']}/{v['astar_interior_valid']} & "
            f"{v['asp_strict_valid']}/{v['astar_strict_valid']} & "
            f"{v['median_astar_minus_asp_length']:.3f} \\\\"
        )
    robot_tex=(
        "\\begin{table}[t]\n\\centering\n\\caption{Frozen local planned paths from the authors' "
        "recorded sights. Validity counts are ASP/A*; the strict convention excludes "
        "obstacle-boundary contact. The methods use different planning graphs.}\n"
        "\\label{tab:robot-local-final}\n\\begin{tabular}{lrrrrrrr}\n\\hline\n"
        "Cohort & Captured & Eligible & ASP shorter & A* shorter & Interior-valid & "
        "Strict-valid & Median $\\Delta L$ \\\\\n\\hline\n"
        +"\n".join(robot_rows)+"\n\\hline\n\\end{tabular}\n"
        "\\footnotesize{$\\Delta L=L_{A*}-L_{ASP}$, in source world units. "
        "Equal-length cases are omitted from shorter counts.}\n\\end{table}\n"
    )
    (TABLES/"robot-local-results.tex").write_text(robot_tex,encoding="utf-8")
    s=data["supporting"]
    supporting_tex=(
        "\\begin{table}[t]\n\\centering\n\\caption{Internal online-navigation supporting studies. "
        "These are distinct from the frozen local ASP/A* path study.}\n"
        "\\label{tab:supporting-final}\n\\begin{tabular}{lrrl}\n\\hline\n"
        "Study & Configurations & Successful/equivalent & Descriptive result \\\\\n\\hline\n"
        f"Radar versus legacy & {s['radar_pairs']} & 20 & Radar shorter in {s['radar_shorter']}; "
        f"largest regression +{s['radar_largest_regression']:.2f} units \\\\\n"
        f"Cached frontier & {s['cache_pairs']} & {s['cache_equivalent']} & "
        f"Median frontier ms {s['cache_median_full_frontier_ms']:.2f} vs "
        f"{s['cache_median_cached_frontier_ms']:.2f} \\\\\n"
        f"Sensor radius & {s['sensor_episodes']} & {s['sensor_goal_success']} & "
        f"Median distance radius 5/7: {s['sensor_median_radius5_distance']:.2f}/"
        f"{s['sensor_median_radius7_distance']:.2f} \\\\\n"
        "\\hline\n\\end{tabular}\n\\end{table}\n"
    )
    (TABLES/"supporting-results.tex").write_text(supporting_tex,encoding="utf-8")


def main():
    FIG.mkdir(exist_ok=True);TABLES.mkdir(exist_ok=True)
    eligibility=json.loads((HERE/"robot-snapshot-eligibility-summary.json").read_text())
    audit=read_csv(HERE/"robot-snapshot-eligibility-audit.csv")
    assert len(audit)==351 and eligibility["original_two_cohorts"]["excluded"]==111
    assert eligibility["eligibility_checker_mismatches"]==0
    data={"road":road(),"robot":robot(),"supporting":supporting(),"initial_eligibility_audit":eligibility}
    (HERE/"benchmark-final-summary.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    write_tables(data)
    print(json.dumps({"road":data["road"],"robot":{k:v for k,v in data["robot"].items() if k!="cohorts"},"supporting":data["supporting"]},indent=2))


if __name__=="__main__":
    main()
