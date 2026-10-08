# Application 1: Blind-Alley Robot Navigation

## Scope and implementation

This is a deterministic **grid adaptation** of limited-sensing BAR navigation for
the A* coursework. It does not reproduce the paper's continuous polygon geometry,
line-segment bundles, or DAP optimization. The same C++17 A* in
`include/astar/search.hpp` is called through `astar_core.grid_search` with
`movement=4`, `algorithm="astar"`, and `trace=false`. Every cardinal move costs
one unit, so path cost equals cell-center geometric travel distance.

The controller's inputs are the fixture's obstacle rows, start and goal cells,
and sensor radius. Only `sense()` consults the obstacle rows to create
observations; `move()` checks physical collision as a simulator assertion.
The planner receives a separate UNKNOWN/FREE/BLOCKED map. It converts observed
FREE to binary 0 and both UNKNOWN and BLOCKED to binary 1 before calling C++.
The goal coordinate is known; occupancy and the route to it are not assumed.

At each position the robot senses cell centers inside the radius with
conservative supercover-ray occlusion. A blocked cell is visible on its own ray;
cells behind a blocker are not. The sensor is perfect and deterministic. The
robot is a point at a unit-cell center in a static environment, with no
uncertainty, clearance radius, or nonholonomic motion constraint.

If the goal has a verified FREE route, the controller takes one step along it.
Otherwise it chooses a reachable observed-FREE frontier next to UNKNOWN.
Frontier candidates are ranked by `(discovered-map travel cost + 0.75 * Manhattan
distance to goal, discovered-map travel cost, row, column)`. One breadth-first
pass computes candidate costs exactly because all discovered four-neighbor edges
have unit cost. The selected route is then planned by the existing C++ A*; an
assertion checks that its cost agrees. This ranking is an exploration policy,
not an optimality guarantee for the full online journey. The reported A* count
and expanded nodes include only actual A* searches. A frontier that
yields no observation is skipped until the map changes. The episode ends on
goal arrival, no reachable informative frontier, or a defensive step limit.

## Autonomous branch recovery and benchmark labels

The exact trigger is specified in [bar-recovery-trigger.md](bar-recovery-trigger.md).
It uses only the discovered FREE graph and executed movement history to find an
exhausted branch behind a known bridge. The controller is not given the
`evaluation_gate` or `evaluation_gate_edges` fields. A separate evaluator reads
those fields only after the
episode is complete, labeling gate crossings and measuring benchmark entry and
retreat lengths. Changing the gate changes evaluation labels but not navigation
frames; a regression test checks this separation.

Once recovery starts, the controller records the actual entry history suffix,
plans a return to the bridge's outside endpoint with C++ A*, and executes that
entire route without exploration decisions. It continues sensing, but those
observations cannot interrupt the locked return. If A* fails or its proposed
route is invalid or longer than the recorded entry, the controller uses the
exactly reversed entry history.
It checks the **executed** retreat length afterward.

Under a static map, reversible four-neighbor movement, correct observations,
and unit geometric edge length, the reversed entry path is feasible and has
length `L_entry`. Manhattan is admissible and consistent on that graph, so
optimal A* gives `L_retreat <= L_entry`. The test uses tolerance `1e-9`. This
does not establish shortest total exploration travel, nor recognition of every
blind alley in arbitrary geometry. The old eight-direction grid cost of 1.5 is
unchanged and is not used in this application.

## Reproduce the experiment

After building the existing binding, run:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar.py
```

The script runs six checked-in maps at radii 1, 2, and 3 and prints CSV.
It records goal success, executed distance, gate entry/retreat lengths and ratio,
total A* expanded nodes, A* call count (`replanning_count`), planning time,
and turns. A **turn** is a change between consecutive executed cardinal-move
headings, including transitions into or out of retreat. Initial orientation is
not counted. `planning_time_ms` sums wall-clock time spent in C++ binding calls;
its exact value varies by machine and load. All map and path metrics are
deterministic. There is no random seed or stochastic sensing.

The [frozen benchmark table](bar-results.md) includes full-map shortest-path
costs for comparison with actual online distance. The full map is used only by
the benchmark script, never by the navigation policy. Its new shortcut fixture
verifies an A*-computed return that is shorter than the actual entry path.

The wide-mouth map deliberately exposes the bridge detector's coverage limit:
the robot may exit and reach the goal without a certified locked retreat. The
maps are grid benchmarks, not geometric reproductions of the paper's maps;
their numerical results must not be compared directly with the paper's table.
See [the independent research review](bar-independent-review.md) for the
paper/source comparison, authors-map adaptation protocol, and report claims.
