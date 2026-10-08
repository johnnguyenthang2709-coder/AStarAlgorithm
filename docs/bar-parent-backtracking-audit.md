# Maze 3 parent-aware backtracking audit

## Finding and correction

The controller already had the requested architecture: a stack of explored
sensing positions, nearest viable ancestor selection, C++ A* return planning
on certified visibility edges, and a reversed-entry fallback. The shortest
route claim applies to the **current constructed graph**, not to every
continuous path in the known polygon region. The C++ adapter assigns Euclidean
cost to each undirected verified edge and uses Euclidean distance to the return
anchor as its consistent heuristic.

Two edge cases needed correction in `backend/app/services/bar_continuous.py`:

1. A selected exploration candidate was removed and marked tried *before* its
   A* plan succeeded. A failed plan silently discarded the candidate. It is
   now recorded as `unreachable_target`, deferred until certified free area or
   graph scan positions grow, and kept when a child stack node is removed.
   A failed attempt is therefore distinguishable from an exhausted branch.
2. Sensing during the locked return was attached to the leaf node scheduled
   for removal. Newly observed candidate directions could be lost. Those
   observations now belong to the surviving ancestor. Sibling candidates
   already held by that ancestor remain in place.

No C++ core, geometric sensor, world topology, Road Navigation, or grid BAR
code changed. The historical benchmark CSV remains unchanged.

## Exact controller behavior

| Question | Verified behavior |
| --- | --- |
| Parents and branching points | `ExploreNode(position, history_index, candidates)` instances form a stack. A child is pushed only after actual exploration movement. A node with remaining valid candidates is a branching position. |
| Exhaustion | `_candidate_valid` requires a candidate outside prior scan neighborhoods, inside certified free space, near its boundary, and capable of exposing at least 0.1 square units of unknown space. `select()` looks first at the current node, then nearest ancestors. A graph-blocked candidate is deferred rather than counted as permanently tried. |
| Return target | The nearest ancestor with a currently selectable candidate is chosen. Empty intermediate parents can be skipped. If none exists, the run ends with `no_reachable_frontier`; no pointless return to start is required. |
| Return route | `plan(anchor)` builds visibility edges covered by accumulated known free space and invokes `astar_core.visibility_search(..., "astar")`. It returns a shortest route on that graph. Each route segment is checked against known free space and simulator collision geometry before execution. |
| Fallback | If A* finds no route, yields an invalid route, or its route exceeds the recorded entry length, the controller reverses the actual entry trajectory. Static walls, a point robot, reversible motion, and exact segment execution make this a verified bound fallback. |
| Siblings | Ancestor candidates persist on the stack. After the locked return, only descendants are removed; retreat observations and deferred candidate directions are assigned to the surviving ancestor. The next selection can explore a sibling. |
| Repetition | Exact selected targets are tracked at 0.001-world-unit coordinate precision; near-prior scan positions and candidates with no remaining unknown potential are rejected. New observations can legitimately produce a different nearby target, so the controller does not guarantee spatially non-redundant exploration. |

`recover_start.trigger` and the matching recovery record now distinguish
`exhausted_branch` from `graph_blocked_target`. The latter means A* could not
reach a selected candidate on the current planning graph. It is not a claim
that the surrounding continuous region is exhausted. In both cases, the
executed return length is checked against the recorded entry trajectory.

## Actual execution trace

Reproduce with:

```powershell
.venv\Scripts\python.exe scripts\audit_bar_backtracking.py --radius 5 | Set-Content docs\bar-parent-backtracking-trace.csv
```

The script runs the seeded Blind-Alley Labyrinth (`seed=23`, radius 5), uses
the emitted graph from each `recover_start` frame, and calls the **existing
C++ Dijkstra binding on that exact graph** as a cost baseline. It also checks
every return segment against the simulator's polygon collision model. The
[full 11-return trace](bar-parent-backtracking-trace.csv) shows no fallback:

| Return | Frame | Anchor | Entry | Executed A* return | Same-graph Dijkstra | Next exploration target |
| ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | 22 | (17.489, 15.823) | 2.910 | 2.910 | 2.910 | (16.325, 17.839) |
| 2 | 30 | (17.489, 15.823) | 2.328 | 2.328 | 2.328 | (18.510, 17.591) |
| 7 | 70 | (17.489, 11.723) | 31.909 | **2.588** | **2.588** | (16.452, 9.926) |

All 11 recorded return lengths equal the corresponding same-graph Dijkstra
cost within six decimal places, and all executed retreat bounds are verified.
The 33 exploration-plan targets in this episode are distinct. After return 1,
the controller plans to a different sibling target at the same anchor; after
return 7, it continues toward another branch. The run reaches the goal.

The focused tests cover failed-target deferral, retry after a new verified
graph waypoint, owner assignment for observations made during retreat,
goal-plan failure without a repeated planning loop, nearest viable ancestor
selection, same-graph optimality, collision-free returns, sibling continuation,
and the reversed-entry fallback.

Complete regression after the correction:

```powershell
.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure
.venv\Scripts\python.exe -m pytest -q tests
cd frontend
npm test
npm run build
npm run lint
```

Results: 4/4 C++ tests, 113/113 Python tests, 32/32 frontend tests, and
successful build/lint. Python emitted one existing Starlette/httpx deprecation
warning. Across the eight old-room and irregular preset/radius runs in
`scripts/benchmark_bar_labyrinth.py`, goal status, executed distance, recovery
count, A* calls, expanded nodes, turn count, and frame count matched the
previous frozen matrix. Timing and JSON bytes changed as expected between
runs and because return frames now carry a trigger label.

## Limits

The visibility graph consists of observed scan positions plus the current and
target positions; it is not a complete visibility graph of all discovered
polygon vertices. Thus A* optimality is relative to this graph. A failed
graph route can still correspond to a reachable point in the underlying free
space. Deferral waits for new certified area or a new verified scan position;
if neither can be obtained, bounded exploration can terminate. Sibling
candidates are revisited only while they remain useful under the current
discovered map. A finite sensor and deterministic frontier policy do not
guarantee goal discovery or globally minimal online distance.
