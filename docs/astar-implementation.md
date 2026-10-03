# How A* works in this project

This document explains the C++ A* implementation used by **Road Navigation** and **Robot Lab**. The executable algorithm is the `astar::search` template in [`include/astar/search.hpp`](../include/astar/search.hpp). The files in [`reference/2550216/`](../reference/2550216/) are the supplied historical reference and are exercised by a regression test; they are not the algorithm called by the application.

## 1. The idea

A* searches a graph for a minimum-cost path from `start` to `goal`. For a state `n`, it maintains:

| Value | Meaning in this project |
| --- | --- |
| `g(n)` | Lowest path cost found so far from `start` to `n`. |
| `h(n)` | Estimated remaining cost from `n` to `goal`. |
| `f(n) = g(n) + h(n)` | Priority used to select the next state to expand. |

`h` guides the search, but the returned `cost` is the accumulated **actual edge cost** `g(goal)`. With a finite, nonnegative, admissible heuristic and finite, nonnegative edge costs, A* returns an optimal path. The road and grid adapters below choose heuristics that are lower bounds for their cost models. Setting `h(n) = 0` makes the same search function behave as Dijkstra's algorithm.

The application path is:

```text
React UI → FastAPI → pybind11 binding → astar::search → problem adapter
                                              ├─ GridProblem
                                              ├─ RoadProblem (node-to-node)
                                              └─ EdgeSnappedRoadProblem (map coordinates)
```

The frontend displays routes and search events; it does not implement A*.

## 2. One C++ search, multiple problems

The template in [`search.hpp`](../include/astar/search.hpp) accepts a state type and a `Problem` object. Each problem supplies three operations:

```cpp
neighbors(state)           // outgoing Edge<State>{to, cost} values
heuristic(state, goal)     // estimated remaining cost
is_goal(state, goal)       // goal test
```

The core does not know whether a state is a road node ID, a temporary road position, or a grid cell. For road searches, `State` is `int`. For grid searches, it is `Cell{row, col}` with `CellHash` for the hash table. The problem chooses the graph representation and movement rules; the core owns the queue, best costs, parent links, and termination.

`search` is defined in a header because C++ must see the template definition when it instantiates the function for each problem and state type. The binding calls it with a road integer state or with a grid cell and its hash:

```cpp
astar::search<int>(road_problem, start_node, goal_node, true, trace);
astar::search<astar::Cell, astar::GridProblem, astar::CellHash>(
    grid_problem, start_cell, goal_cell, true, trace);
```

## 3. What the core stores

`std::unordered_map<State, Record>` stores the best known `g`, an optional parent, and the `g` at which that state was last expanded. There is no fixed-size array or 100-state limit.

`std::priority_queue<Entry, ..., Worse>` is the **OPEN** set. An entry contains its state, `g`, `h`, `f`, and a monotonically increasing insertion order. Lower `f` wins; when `f` ties, lower `h` wins; when both tie, earlier insertion wins. Given the same neighbor order and floating-point values, this makes selection deterministic.

There is no permanent CLOSED set. `expanded_g` records the cost of the last valid expansion. A state can be expanded again if a better path arrives later. This matters when an admissible heuristic is inconsistent.

## 4. Search loop, step by step

The following pseudocode follows the actual control flow in [`astar::search`](../include/astar/search.hpp):

```text
best[start] = { g: 0, parent: none }
push OPEN(start, g=0, h=h(start), f=h(start))

while OPEN is not empty:
    current = pop the lowest (f, h, insertion order)

    if current.g is worse than best[current.state].g:
        skip this stale queue entry
    if current.state was already expanded at this g or a lower g:
        skip this duplicate expansion

    mark current.state expanded at current.g

    if current.state is the goal:
        follow parent links backward, reverse the path, return it and current.g

    for each outgoing edge (current.state → next, cost):
        tentative = current.g + cost
        if tentative < best[next].g:
            best[next].g = tentative
            best[next].parent = current.state
            push a new OPEN entry for next with f = tentative + h(next)

return found = false, empty path, cost = infinity
```

The core validates that each edge cost and heuristic is finite and nonnegative, and rejects a path or priority calculation that overflows. It updates a state only for a **strictly smaller** `g`; an equal-cost alternative retains the existing parent. The goal check happens when a **valid** goal entry is popped, not when the goal is first discovered.

One queue push or pop costs `O(log Q)` for `Q` queued entries; expanding a state examines its outgoing edges. The hash table stores discovered-state records. Multiple improvements can create extra queue entries and, with an inconsistent heuristic, re-expansions. Trace memory grows with the number of recorded events; ordinary searches disable trace collection.

### Better paths, stale entries, and reopening

`std::priority_queue` does not decrease the priority of an existing entry. Instead, a better route pushes a second entry. When the older, more expensive entry reaches the top, the comparison with `best[state].g` discards it. If a state was expanded before the improvement, the new, lower `g` is allowed to expand it again. This is how duplicate states are handled without modifying the heap in place.

For example, if `start → A` costs `2.2`, but `start → B` costs `0.7` and `B → A` costs `0.7`, relaxation changes `g(A)` from `2.2` to `1.4` and changes `A`'s parent to `B`. The old `2.2` queue entry cannot replace that better record.

### Path and stopping cases

Each improvement records the predecessor. After the goal is popped, the core follows parents back to the start and reverses the sequence. If `start == goal`, the path is a single state with cost `0`. If OPEN empties first, `found` is false, the path is empty, and the cost remains infinity. Directed edges are followed only in the direction returned by `neighbors`.

## 5. Road Navigation

[`RoadGraph`](../include/astar/road_problem.hpp) loads the checked-in directed road graph. A `RoadNode` has an OSM ID and geographic coordinate. Each `RoadEdge` has a destination node, meter cost, OSM metadata, and an oriented polyline. The graph keeps routing adjacency as `Edge<int>{to, cost}` alongside geometry used to draw a route. Loading validates coordinates, costs, geometry endpoints, and unique directed endpoint pairs.

For a node-to-node query, [`RoadProblem`](../include/astar/road_problem.hpp) forwards outgoing adjacency to A* and uses:

```text
h(n) = graph.heuristic_scale() × Haversine(node[n], node[goal])
```

`heuristic_scale` starts at `1` and is reduced to the minimum `edge_cost / Haversine(edge endpoints)` across the loaded graph. Therefore the heuristic is a conservative geographic lower bound, even if an exported edge cost is slightly shorter than its endpoint Haversine distance. The search objective stays the sum of road-edge costs in meters.

### Map clicks: nearest road edge

The user-facing coordinate API uses [`EdgeSnappedRoadProblem`](../include/astar/edge_snapped_road_problem.hpp), implemented in [`src/edge_snapped_road_problem.cpp`](../src/edge_snapped_road_problem.cpp). It linearly scans the directed road polylines, projects each requested coordinate onto the nearest geometry, and measures a fraction `r` along that polyline. The fraction uses cumulative segment lengths; it is not the straight-line fraction between intersections.

For an edge `u → v` with cost `w` and a snapped point `P` at fraction `r`:

```text
cost(u → P) = r × w
cost(P → v) = (1 - r) × w
```

The two partial costs sum to `w`, within floating-point tolerance. A virtual start can leave toward `v`; a virtual goal can be reached from `u`. A matching reverse road permits travel in the other direction using that reverse edge's own cost and fraction. Two points on the same directed road get a direct partial edge only when the goal lies ahead of the start. A click exactly at an edge endpoint uses the existing graph node.

These virtual states and edges exist **only for one search request**. The shared `RoadGraph` is unchanged. The request-local heuristic is still scaled Haversine, with its scale reduced if a partial edge requires a smaller lower-bound factor. The result geometry slices the first and last road polylines at the snapped positions, retaining bends.

As a simple same-edge example, on a 400 m directed road, start at `r = 0.25` and goal at `r = 0.75` produce a direct route cost of `(0.75 - 0.25) × 400 = 200 m`. Reversing those points cannot use that directed shortcut; a valid reverse road or a longer legal route is needed.

## 6. Robot Lab grid

[`GridProblem`](../include/astar/grid_problem.hpp) represents free cells with `.` and obstacles with `#`. `Cell{row, col}` is the state. Neighbors are generated from a cell rather than stored as a separate graph:

| Movement | Edge cost | Heuristic to goal |
| --- | ---: | --- |
| Four directions | Cardinal move: `1` | Manhattan distance `|Δrow| + |Δcol|` |
| Eight directions | Cardinal move: `1`; diagonal move: `1.5` | `max(|Δrow|, |Δcol|) + 0.5 × min(|Δrow|, |Δcol|)` |

The eight-direction heuristic counts as many diagonal moves as possible, then remaining cardinal moves. A diagonal is allowed only if its destination and **both adjacent side cells** are free, so the robot cannot cut through a blocked corner. Start and goal must be traversable.

When obstacles are added during robot playback, [`grid_service.py`](../backend/app/services/grid_service.py) submits a **fresh** search from the robot's current cell on the updated grid. This is repeated A*, not a separate incremental pathfinding algorithm.

## 7. Dijkstra, trace, and application boundary

[`astar::dijkstra`](../include/astar/search.hpp) calls the same template with `use_heuristic = false`. The binding also exposes an `algorithm` choice that passes this flag to the shared search. Comparisons run A* and Dijkstra on the **same** problem instance and check equal reachability and costs within `1e-6 m` for road routes.

Optional trace recording emits `DISCOVER`, `EXPAND`, `UPDATE`, `CLOSE`, and `GOAL_FOUND` events with state, parent, `g`, `h`, and `f`. With `trace=false`, no event list is collected. `CLOSE` describes the end of one expansion; a later improvement can reopen that state. The returned metrics distinguish queue pushes, successful relaxations, examined edges, total expansions, and unique states.

[`backend/bindings.cpp`](../backend/bindings.cpp) instantiates the templates and exposes them through pybind11. FastAPI's [road service](../backend/app/services/road_service.py) and [grid service](../backend/app/services/grid_service.py) call those bindings. Road API responses include requested and snapped coordinates; the frontend receives route geometry and trace positions without needing to build virtual states itself.

## 8. Where to read and how to verify

| Purpose | Source or test |
| --- | --- |
| Shared A* loop and Dijkstra wrapper | [`include/astar/search.hpp`](../include/astar/search.hpp) |
| Grid neighbors, costs, and heuristics | [`include/astar/grid_problem.hpp`](../include/astar/grid_problem.hpp) |
| Base road graph and heuristic | [`include/astar/road_problem.hpp`](../include/astar/road_problem.hpp), [`src/road_problem.cpp`](../src/road_problem.cpp) |
| Coordinate snapping and temporary edges | [`include/astar/edge_snapped_road_problem.hpp`](../include/astar/edge_snapped_road_problem.hpp), [`src/edge_snapped_road_problem.cpp`](../src/edge_snapped_road_problem.cpp) |
| C++/Python entry points | [`backend/bindings.cpp`](../backend/bindings.cpp) |
| Queue, stale-entry, reopening, tie, path, and grid tests | [`tests/core_tests.cpp`](../tests/core_tests.cpp) |
| Road A*/Dijkstra regression | [`tests/road_tests.cpp`](../tests/road_tests.cpp) |
| Edge snapping, directionality, geometry, and equal-cost tests | [`tests/edge_snap_tests.cpp`](../tests/edge_snap_tests.cpp), [`tests/test_edge_snapping.py`](../tests/test_edge_snapping.py) |

After building with the steps in the [project README](../README.md), run the C++ tests from the repository root:

```powershell
.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure
```

The API and frontend tests in the README check that the C++ results are correctly delivered and visualized. The original reference implementation remains available for comparison, while both application modes execute the generalized C++ core.
