"""Render data-only academic benchmark figures from recorded CSV artifacts."""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def rows(name):
    with (HERE / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def finish(name):
    plt.tight_layout()
    plt.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    plt.close()


def road():
    paired = defaultdict(dict)
    for row in rows("road-astar-dijkstra.csv"):
        paired[row["pair_id"]][row["algorithm"]] = row
    ordered = [paired[k] for k in sorted(paired, key=int)]
    colors = {"short": "#387c86", "medium": "#b47b2a", "long": "#81558a"}
    for field, label, name in (("expanded_nodes", "Expanded nodes", "road-expanded.png"),
                               ("median_search_us", "Median search time per call (µs)", "road-time.png")):
        fig, ax = plt.subplots(figsize=(6.7, 5.5))
        for stratum in colors:
            group = [p for p in ordered if p["astar"]["stratum"] == stratum]
            ax.scatter([float(p["dijkstra"][field]) for p in group],
                       [float(p["astar"][field]) for p in group],
                       s=24, alpha=.75, label=f"{stratum} (n=60)", color=colors[stratum])
        values = [float(p[m][field]) for p in ordered for m in ("astar", "dijkstra")]
        bound = max(values) * 1.05
        ax.plot([0, bound], [0, bound], color="#555", linewidth=1, linestyle="--", label="equal")
        ax.set(xlabel=f"Dijkstra {label.lower()}", ylabel=f"A* {label.lower()}",
               xlim=(0, bound), ylim=(0, bound), title=f"Directed road graph: A* versus Dijkstra\n180 frozen node pairs")
        ax.legend(frameon=False)
        finish(name)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    differences = [float(p["astar"]["cost_m"]) - float(p["dijkstra"]["cost_m"]) for p in ordered]
    ax.scatter(range(len(differences)), differences, s=13, color="#387c86")
    ax.axhline(0, color="#555", linewidth=1)
    ax.set(xlabel="Frozen pair index", ylabel="A* cost − Dijkstra cost (m)",
           title="Optimal-cost agreement across 180 directed road queries")
    finish("road-cost-agreement.png")


def author_diagnostic():
    data = rows("author-reproduction.csv")
    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
    names = [r["map"].removeprefix("_map_").removesuffix(".csv") for r in data]
    x = list(range(len(data)))
    left.bar([i - .18 for i in x], [float(r["executed_distance"]) for r in data],
             .36, label="Executed center distance", color="#387c86")
    left.bar([i + .18 for i in x], [float(r["logged_planned_asp_distance"]) for r in data],
             .36, label="Logged planned ASP distance", color="#b47b2a")
    left.set(xticks=x, xticklabels=names, ylabel="Distance (source map units)",
             title="Upstream planned and executed differ")
    left.legend(frameon=False, fontsize=8)
    right.bar(x, [int(r["interior_collision_segments"]) for r in data],
              color="#a94c48", label="Interior crossing")
    right.set(xticks=x, xticklabels=names, ylabel="Executed invalid segments",
              title="Source reproduction collision gate")
    right.legend(frameon=False, fontsize=8)
    finish("author-validity-diagnostic.png")


def supporting():
    cache = rows("frontier-cache.csv")
    paired = defaultdict(dict)
    for r in cache:
        paired[(r["case"], r["radius"])][r["variant"]] = r
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter([float(p["full"]["frontier_total_ms"]) for p in paired.values()],
               [float(p["cached"]["frontier_total_ms"]) for p in paired.values()],
               color="#387c86", s=27)
    bound = max(float(p["full"]["frontier_total_ms"]) for p in paired.values()) * 1.05
    ax.plot([0, bound], [0, bound], "--", color="#555", linewidth=1)
    ax.set(xlabel="Full reconstruction frontier time (ms)",
           ylabel="Cached frontier time (ms)", title="Paired frontier construction; identical playback")
    finish("frontier-cache.png")

    sensor = rows("sensor-robustness.csv")
    paired = defaultdict(dict)
    for r in sensor:
        paired[(r["kind"], r["case"])][r["radius"]] = r
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    labels = [f"{kind}:{case}" for kind, case in paired]
    positions = range(len(labels))
    ax.bar([p - .18 for p in positions],
           [float(p["5"]["executed_distance"]) for p in paired.values()],
           width=.36, label="radius 5", color="#387c86")
    ax.bar([p + .18 for p in positions],
           [float(p["7"]["executed_distance"]) for p in paired.values()],
           width=.36, label="radius 7", color="#b47b2a")
    ax.set(xticks=list(positions), xticklabels=labels, ylabel="Executed distance (world units)",
           title="Prespecified online-navigation sensing cases")
    ax.tick_params(axis="x", labelrotation=28)
    ax.legend(frameon=False)
    finish("sensor-robustness.png")

    with (HERE.parent.parent / "docs" / "bar-indoor-radar-trace.csv").open(newline="", encoding="utf-8") as stream:
        returns = [row for row in csv.DictReader(stream) if row["bound_verified"] == "True"][:8]
    fig, ax = plt.subplots(figsize=(7, 4))
    pos = range(len(returns))
    ax.bar([p - .18 for p in pos], [float(r["entry_length"]) for r in returns],
           .36, color="#b47b2a", label="Recorded entry")
    ax.bar([p + .18 for p in pos], [float(r["executed_return_length"]) for r in returns],
           .36, color="#387c86", label="Executed parent return")
    ax.set(xticks=list(pos), xticklabels=[f"{r['branch']}→{r['parent']}" for r in returns],
           xlabel="Observed branch → parent ID", ylabel="World units",
           title="Representative certified parent returns (indoor trace)")
    ax.legend(frameon=False)
    finish("parent-return.png")


if __name__ == "__main__":
    road()
    author_diagnostic()
    if (HERE / "frontier-cache.csv").exists() and (HERE / "sensor-robustness.csv").exists():
        supporting()
