# Hierarchical indoor exploration with A*

## Technical decision

The indoor mode reuses the continuous polygon sensor, collision oracle, online
`ContinuousPolicy`, and C++ visibility-graph A*. It adds a seeded **simulator
floor plan** and an optional trace of the policy's observed exploration-anchor
tree. The controller receives sensor wedges and visible wall fragments only.
Architectural room names, furniture polygons, complete doors, corridors, and
the generator's topology remain in `IndoorLayout`, outside the policy and API
playback. The UI renders only accumulated observations.

Reliable semantic room segmentation from these limited polygon scans would
require another inference system. The controller therefore calls its parent
nodes **observed branches**, not rooms. Every completed exploration movement
creates a child anchor; `branch_id` and `parent_id` expose this observed tree.
Cycles in physical free space remain legal: A* may return through any verified
visibility edge, rather than following tree edges. The tree decides *where* to
explore or return; A* decides the shortest route on the currently constructed
graph. Indoor mode uses the existing goal-directed local frontier order, not a
global best-frontier policy. This is strict nearest-viable-ancestor
backtracking when the active branch has no selectable candidate.

The controller distinguishes an exhausted branch from a graph-unreachable
target. A failed target is deferred until known free area or graph waypoints
grow. An ancestor with a viable sibling is selected; newly sensed options on
the locked return belong to that surviving ancestor. A* computes the return
route through certified free segments. If A* fails, gives an invalid route, or
would exceed the recorded entry length, the exact reversed entry trajectory is
used. Every executed return checks matching endpoints and the local
`return_length <= entry_length` bound. These are **local backtracking
certificates** under static obstacles, a point robot, and reversible exact
motion; they do not establish that every indoor dead end is a formal BAR under
the paper's definition.

## Generated layouts

`backend/app/services/bar_indoor.py` generates three deterministic polygon
layouts: Small Apartment (seed 41), Office Building (seed 73), and Indoor Maze
Challenge (seed 211). Eight irregularly sized rooms connect to a common
hallway, with auxiliary side hallways and multi-door rooms forming cycles.
Different room kinds receive sofas/tables, workstations, or staggered storage
shelves. The challenge adds partitions and deeper branches. A seed perturbs
door and furniture positions; it does not change the broad floor-plan
topology. A custom seed may be entered in the UI. Geometric free space is
validated as a single polygon, every door aperture is free, and start and goal
lie strictly in free space. No generator outcome is filtered by controller
success.

The robot remains a continuous, holonomic point robot with 360-degree,
range-limited, occlusion-aware sensing. The known goal coordinate and world
bounds are given to the policy. Ground-truth room labels and door coordinates
are not. Collision checking uses the simulator's actual polygon world, while
route planning uses only certified known-free segments.

## Reproduction and results

From the repository root on Windows:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar_indoor.py --radii 5 7 | Set-Content docs\bar-indoor-results.csv
.venv\Scripts\python.exe scripts\audit_bar_indoor_trace.py | Set-Content docs\bar-indoor-trace.csv
```

The [full results](bar-indoor-results.csv) and [parent-return trace](bar-indoor-trace.csv)
record actual executed distance, known free area, observed branches, A* calls,
expanded nodes, turns, planning time, return lengths, and status. Wall time
and planning milliseconds vary by machine; the geometric and count results
are deterministic for the pinned Python/Shapely/C++ environment.

| Preset | Radius | Status | Distance | Returns | A* calls | Expanded |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Apartment | 5 | goal reached | 189.246 | 11 | 50 | 102 |
| Apartment | 7 | goal reached | 248.374 | 13 | 50 | 101 |
| Office | 5 | goal reached | 181.356 | 11 | 51 | 102 |
| Office | 7 | goal reached | 625.729 | 36 | 117 | 234 |
| Challenge | 5 | goal reached | 129.957 | 6 | 35 | 70 |
| Challenge | 7 | goal reached | 137.893 | 3 | 27 | 54 |

All 80 recorded returns across these six runs used C++ A*, had no fallback,
and met their local executed-length bounds. Formal paper BAR certifications
are zero because no indoor region was classified against the paper's BAR
definition. In the apartment trace, branch 31
returns to observed parent 23 over 6.147 units after a 30.323-unit entry;
branch 32 is then explored. A focused test compares an indoor A* return with
C++ Dijkstra on the identical graph. The fallback remains covered by the
existing continuous-controller tests.

The larger sensing radius can increase travel, as Office shows: the set and
ranking of observed candidates changes, and goal-directed online exploration
is not globally distance optimal. These results must not be compared as
shortest-path quality against full-map plans or the authors' different
continuous BAR experiments.

## Comparison and limits

Irregular Labyrinth is a corridor network produced from a lattice topology;
indoor mode has varied rooms, doors, multiple entrances, furniture, and
interior shelves. Both use the same sensing, partial map, C++ A* graph,
parent-stack selection, collision checks, and conditional reversed-entry
fallback. Indoor mode adds observable branch IDs and benchmark metadata; it
does not alter the old Maze 3 presets or Road Navigation.

The visibility graph contains observed scan positions plus current and target
positions. A* is shortest on that graph, not among every continuous path in
the known polygonal region. Goal reaching is not guaranteed for arbitrary
seeds or sensor radii. `step_limit`, `no_reachable_frontier`, and `goal_reached`
are distinct outcomes. Branch IDs are anchor history, not reliable discovered
room segmentation. The simulated furniture and layouts are stylized; there is
no SLAM, robot body clearance, door state, or dynamic obstacle model.
