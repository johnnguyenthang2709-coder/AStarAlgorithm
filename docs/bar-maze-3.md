# Maze 3: seeded continuous Blind-Alley environments

Maze 3 is the default Blind Alley **continuous 2D** demonstration. It adds
geometric corridor maps without changing `include/astar/search.hpp`, the C++
visibility-graph binding, Road Navigation, the four-direction grid mode, the
original polygon importer, or the two fixed continuous polygon baselines.

## Generator design

`backend/app/services/bar_maze.py` builds an `N × N` room lattice with 5 world
units between room centers. A seed drives a randomized depth-first spanning
tree. Optional extra openings create loops while preserving some degree-one
rooms. Every degree-one room is a three-wall U-shaped cul-de-sac with one
entrance. This is a controlled **blind-alley-like fixture**, not a general
geometric BAR classifier or the original paper's bugtrap construction.

Each shared room boundary becomes one or two **polygon rectangles**. A closed
connection has a complete wall slab; an open connection has a centered doorway
of `corridor_width` world units. The robot is a point with continuous `(x,y)`
position and arbitrary heading. The lattice decides geometry; it does **not**
constrain robot movement to cells or lattice edges. Sensor rays, collision
checks, and C++ A* visibility links use the generated polygons. Every generated
opening and closed center-to-center connection is checked against the actual
polygon collision model. A spanning tree guarantees a route between all room
centers, including user-selected endpoints. Layout generation never runs the
navigation policy and never filters a seed because exploration failed.

Automatic endpoints maximize shortest-path distance on the generated room
graph among pairs whose Manhattan room separation is at least `N`. The API and
UI can specify both start and goal room indices (zero based); out-of-bounds or
too-close pairs are rejected explicitly.

| Parameter | Supported range | Meaning |
| --- | --- | --- |
| `seed` | 0–2,147,483,647 | Reproducible wall choices |
| `size` | 4–8 rooms per side | World is `5 × size` units square |
| `corridor_width` | 1.2–4.2 | Centered doorway width; wall thickness is 0.36 |
| `loop_rate` | 0–0.35 | Chance of opening each eligible non-tree connection; positive values retain at least one loop when compatible with traps |
| `dead_end_rate` | 0–1 | Chance to preserve a terminal room when considering extra openings |
| `trap_count` | 1–8 | Minimum number of terminal U-shaped rooms |
| `difficulty` | easy, normal, hard | Adjusts effective loop probability by +0.08, 0, or −0.05 |
| `start_cell`, `goal_cell` | optional `[row, col]` | Both supplied or neither; room separation at least `size` |

Impossible combinations raise a validation error. They are **not** replaced by
an easier layout. Walls are axis-aligned on purpose: the demonstration favors
readable corridors over decorative irregularity. The existing importer remains
available for non-orthogonal polygon maps.

The presets are **Basic Exploration Maze** (`seed=17`, `size=5`, width 3.2,
easy, 1 loop, 4 terminal rooms) and **Blind-Alley Recovery Maze** (`seed=431`,
`size=7`, width 2.3, hard, 2 loops, 8 terminal rooms). The third selection is
**Procedurally Generated Maze**, with editable parameters. Example seeded
cases are 17 and 23 at size 5. The UI defaults to sensing radius 5 for the
basic/seeded maze and 7 for the harder preset.

## Navigation and visualization

The simulator alone holds all walls. Its 360° sensor sends conservative
certified-free polygons, observed wall fragments, and candidate waypoints to
the existing continuous controller. The controller constructs visibility links
only through certified free space and runs the existing C++ A* with Euclidean
cost and heuristic. A* is shortest on each *constructed graph*. Exploration
targets are chosen by potential new sensing area for mazes; original fixed
polygon baselines retain their prior goal-biased policy and one-waypoint
episode protocol. Maze 3 executes the complete A* route to its chosen
waypoint, rather than treating an intermediate graph node as the waypoint.

An exhausted local branch triggers A* return to an ancestor. The return must
be certified and no longer than the recorded continuous entry trajectory;
otherwise the exact reversed entry path is used. The whole chosen route is
executed before exploration resumes, and actual Euclidean retreat length is
checked. These are **local branch recovery** metrics, not a proof for every
geometric blind-alley region.

The normal playback displays only currently sensed corridors and walls,
current robot and heading, sensing radius, A* route, recent executed path,
entry, and retreat. The full executed trail is available by checkbox; it is
hidden initially because accumulated detours created the apparent “graph”
scribble in the old view. Actual visibility graph links are a separate,
opt-in debug overlay requested on the next run. Debug links are derived from
the discovered free map; no hidden wall geometry is sent to the browser.
Fit, zoom, pan, speed, step, scrub, and next-recovery controls remain.

## Experiments

Run from the repository root in PowerShell after the normal Python/C++ setup:

```powershell
$env:PYTHONPATH = 'backend;build-cpython'
.venv\Scripts\python.exe scripts\benchmark_bar_maze.py --presets --seeds 17 23 --radii 5 7
```

The raw reproducible matrix is [bar-maze-3-results.csv](bar-maze-3-results.csv).
One Windows run on 2026-10-09 gave:

| Case | Radius | Goal | Distance | Returns verified / total | A* calls | Expanded | Turns | Wall seconds |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Showcase 17, 5×5 | 5 | yes | 213.231 | 11 / 11 | 56 | 112 | 50 | 0.946 |
| Showcase 17, 5×5 | 7 | yes | 354.685 | 25 / 25 | 78 | 159 | 75 | 2.123 |
| Hard 431, 7×7 | 5 | yes | 695.261 | 61 / 61 | 202 | 407 | 194 | 17.668 |
| Hard 431, 7×7 | 7 | yes | 540.275 | 28 / 28 | 126 | 257 | 123 | 6.816 |
| Seeded 17, 5×5 | 5 | yes | 96.519 | 3 / 3 | 27 | 54 | 20 | 0.308 |
| Seeded 17, 5×5 | 7 | yes | 136.189 | 5 / 5 | 31 | 62 | 30 | 0.483 |
| Seeded 23, 5×5 | 5 | yes | 435.749 | 46 / 46 | 129 | 258 | 125 | 4.094 |
| Seeded 23, 5×5 | 7 | yes | 321.697 | 23 / 23 | 77 | 154 | 71 | 1.796 |

The selected seeds all reached the goal, but the policy has no completeness
guarantee; `step_limit` and `no_reachable_frontier` are legitimate outcomes
for other parameter combinations. Larger sensing range need not reduce online
distance because the frontier policy can choose a different exploration order.
These continuous Euclidean distances must not be compared numerically with
legacy grid-cell benchmark distances or the original authors' experiments.

Profiling the hard radius-5 case found repeated geometric visibility checks.
Caching **already certified** links is sound because discovered free space
only grows; previously invalid links are rechecked after new observations.
Wall time dropped from about 68 to 17.7 seconds with identical trajectory,
distance, and recovery counts. Cumulative C++ A* time in that case was about
10.5 ms; sensing and Python geometry still dominate. The largest response in
this matrix is about 1.24 MB compact JSON and 734 frames; graph debug data
is omitted by default.

## Validation and limits

`tests/test_bar_maze.py` covers seed determinism, graph connectivity, loops,
dead ends, polygon validity, open/closed wall collision, narrow doors,
endpoint validation, limited sensing, hidden-world isolation, verified debug
links, different sensing radii, executed-distance accounting, BAR return
bounds, API response privacy, and disconnected geometry. Existing continuous,
grid, road, and reference A* tests remain part of the full regression run.

The point-robot model has no footprint clearance. The ray-fan sensor is
conservative but finite resolution can miss visible space. An axis-aligned
terminal room is a clear teaching analogue of a blind alley, not the paper's
full polygonal BAR definition. The exploration policy is deterministic and
bounded, not globally optimal or guaranteed to find a reachable goal for all
seeds. Timing depends on machine, Python/Shapely versions, and process load.

On 2026-10-09, the full regressions passed with these commands:

```powershell
.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure
$env:PYTHONPATH = 'backend;build-cpython'
.venv\Scripts\python.exe -m pytest -q tests
cd frontend
npm test
npm run build
npm run lint
```

The observed results were 4/4 C++ tests, 91/91 Python tests, 30/30 frontend
tests, and successful build/lint. Python emitted one existing Starlette/httpx
deprecation warning. The local UI was checked at the first and final frames;
the temporary servers were stopped afterward. The original fixed continuous
episode protocol remains separate: its U-map distances at radii 4 and 6 and
bugtrap distances at radii 4 and 6 were rechecked against the previous
benchmark. The generic A* core and Road Navigation files were not modified.
