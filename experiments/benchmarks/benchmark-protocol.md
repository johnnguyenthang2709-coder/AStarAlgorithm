# Frozen academic benchmark protocol

This protocol is frozen before running the 180-pair road matrix. The selected
pairs and robot goal coordinates are in `benchmark-manifest.json`. The project
base is `cb69fc65fb81f6cffdd3e0556f4dccd5892bdcdf`, and the isolated
upstream checkout is `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8` from
<https://github.com/ThanhBinhTran/autonomousRobot>. No author code or maps
are copied into this repository. The upstream tree has no LICENSE/COPYING
file or pinned Python dependency manifest, so redistribution rights are not
inferred. Our wrapper runs in that external checkout without source patches.

## Questions and evidence classes

1. On the same directed road graph and weight objective, do C++ A* and
   Dijkstra agree on optimal cost, and how do search effort and time differ?
2. Can the paper's Python source be reproduced, and is its actual movement
   metrically and physically compatible with our continuous point robot?
3. How sensitive is our online exploration to ranking, wall-mask caching, and
   sensing radius?

The paper's Section 6.2.1 compares **local paths** on explored space among
improved ASP, a separate grid A* baseline, and RRT*. Section 6.2.2 compares
**end-to-end** navigation with RRTX. Neither section calls the proposed
bundle method Dijkstra. Upstream `Graph.BFS_skeleton_path` uses a priority
queue of cumulative Euclidean costs: it is Dijkstra-style skeleton routing,
followed by critical-line/bundle ASP processing. It is not the grid A*
baseline. `Robot_run.py` and the experiment script compute `robot.asp`,
record it as `visited_paths` and `robot.cost`, but set
`robot.next_coordinate = tuple(robot.next_point)`; the planned ASP polyline
is not physically traversed by that loop. Executed positions must therefore
be captured at `Robot.update_coordinate` and reported separately.

## Stage 1 validity gate

The unmodified `Robot_run.robot_main` was run for the paper's representative
`_map_deadend.csv`, start (0,0), goal (70,90), and `_map_bugtrap.csv`, start
(0,0), goal (160,80), at range 20, radius 0.5, Open_Arcs ranking and
neighbor-first selection, with a fixed 60-step cap. Both reach their goal,
but `run_author_reproduction.py` detects obstacle-interior crossings in
their **executed center-to-center segments** (4 and 1 respectively), with
6 and 3 radius-0.5 clearance violations. Planned ASP totals and actual
coordinate-update totals also differ. The upstream source therefore fails
the shared collision-validity gate. This is a source-code reproduction under
the documented Windows Python environment, **not** an exact paper-table
reproduction. We will not benchmark its collision-invalid center jumps
against collision-checked paths as if both were feasible robot trajectories.

The manifest still freezes 48 potential matched configurations before any
outcome-based selection: two pinned author polygons, eight valid lattice
goals per map selected by evenly spaced Euclidean-distance ranks among
radius-0.5-clearance reachable candidates, and radii 10, 20, 30. Start is
(0,0), broad world bounds include a two-unit margin, and each method would
use a 100-decision cap. Those 96 method episodes remain **unexecuted for
primary comparison** unless a later, separately approved and clearly labeled
collision-model adaptation passes the validity gate. No failed goal may be
silently removed. We will not force the upstream method onto our indoor maps.

The upstream source contains no dependency lock. The source smoke environment
is Windows 11, Python 3.14.2, NumPy 2.4.3, Matplotlib 3.10.8, pandas 3.0.1,
OpenCV 5.0.0, and Shapely 2.1.2; no Linux-only CGAL bridge is used on Windows.
These versions reproduce the source behavior, not necessarily the paper's
original runtime. Static polygon validity and coordinates are checked with
Shapely. A segment is collision-invalid when its interior intersects any
polygon interior; a radius-0.5 clearance violation occurs below 0.5 units.
The authored maps use x/y world coordinates; image-derived y-down maps are
not substituted.

## Road protocol

The checked-in graph has 2,986 nodes and 7,152 directed, weighted edges.
The preparer uses a fixed `random.Random(20261009)` to draw 6,000 distinct,
nonidentity directed pairs. Existing C++ Dijkstra computes offline costs;
unreachable pairs remain recorded as edge cases. The 1/3 and 2/3 order
statistics of reachable sampled costs define short, medium, and long bins.
The first 60 candidates in each bin become the frozen 180-pair matrix. This
is a reproducible **sample-frame quantile**, not an all-pairs graph quantile.
Both timed methods use identical start/goal IDs, RoadProblem neighbors and
meter weights, `trace=false`, and the same C++ search core. This primary
matrix is node-to-node, so snapping is irrelevant; nearest-edge snapping is
checked separately with the same augmentation for both methods.

`academic_road_benchmark` times only C++ `search`, excluding graph load and
Python binding/route serialization. Each pair/method has one unrecorded warmup,
then seven alternating-order timed batches; each short/medium/long batch
contains 20/10/5 calls. The median per-call microseconds across batches is
reported, along with batch minimum/maximum. Results include cost, path node
count, valid expansions, OPEN pushes (`generated_nodes`), unique discovered
states, examined edges, and relaxations. Generated/discovered counts are
logical search-memory proxies; allocator bytes or peak resident memory are
not inferred. Relative timings on this C++ implementation do not isolate the
heuristic's effect from graph topology or system noise. Failed cost agreement
above 1e-6 meter aborts the benchmark.

The Haversine heuristic uses the graph-wide minimum ratio
`edge_weight / Haversine(edge endpoints)`, capped at 1. For every directed
edge `(u,v)`, scale times Haversine(u,v) <= weight(u,v); the Haversine
triangle inequality then gives consistency and hence admissibility for this
distance objective. We validate all direct-edge inequalities and check the
runtime A*/Dijkstra result pairs. Start=goal, one-way and unreachable node
pairs, plus a midpoint nearest-edge query, are separate validations.

The road build is C++17 Release with MSYS2 UCRT64 g++, Windows 11, Intel Core
7 240H (16 logical processors), and about 15.7 GiB RAM. The report records
the final benchmark execution environment and does not claim portable timing
ratios.

## Supporting studies and reporting rules

The existing paired ablation matrix includes unfavorable Complex Labyrinth
radius 7; caching comparisons require identical frames and trajectories.
Sensor robustness uses prespecified Labyrinth/Indoor seeds and fixed 250
decisions at radii 5 and 7. Report failed and timed-out episodes and retain
status labels. Timing plots show distributions, not a single lucky run.
Any robot figure must say whether geometry is ground truth or discovered.
Figures for an invalid primary author/our comparison remain absent; a
diagnostic upstream executed-versus-planned trajectory figure may instead
show why the gate failed. Local ASP-versus-A* path comparison is also omitted
until equivalent frozen discovered information and endpoints can be supplied
without changing the upstream method's assumptions.

The paper PDF was available locally and read for Section 6.1–6.2; the
publisher abstract is <https://www.sciencedirect.com/science/article/pii/S0921889025002829>.
