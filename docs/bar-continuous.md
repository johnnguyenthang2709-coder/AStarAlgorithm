# Continuous 2D Blind Alley demonstration

This is a new, separate navigation model on the *polygon coordinates* of the
two independently authored `irregular_u` and `irregular_bugtrap` scenarios.
The older four-direction occupancy-grid mode and its frozen results are still
available through **Grid baseline**. Their distances and BAR labels must not be
compared as if they used the same robot or sensor model.

## Technical decision

The robot is a **holonomic point** (radius 0), with position `(x,y)` and a
heading aligned to each executed segment. Any straight-line direction is
allowed; turning has no motion cost. An episode's distance is the sum of
Euclidean lengths of the *executed* segments. A turn counts a nonzero heading
change between two consecutive executed segments. Boundaries and polygon
edges are treated as collision. The simulator performs an independent
ground-truth collision check before every executed segment.

The sensor has a 360° field of view and configurable radius. It casts 72
uniform rays plus rays around **visible** obstacle vertices. It accepts only
fan triangles that are inside the world bounds and disjoint from obstacles.
Their union is a conservative representation of certified free space.
Finite ray density can miss small visible regions; it cannot certify obstacle
interiors as free. A hidden vertex never contributes a ray angle. The controller
receives only the certified free region, ray-based candidate waypoints, and
observed boundary fragments. It never receives the polygon list or a
ground-truth collision oracle. The world bounds and goal coordinate are public.

The controller maintains the union of certified free observations. On each
replan it constructs a small visibility graph from prior sensing positions,
current position, and target. An undirected link exists only if the *entire*
segment is covered by this union. C++ `visibility_search` adapts these links
to the existing generic A* implementation. Edge cost is Euclidean length;
the straight-line goal distance is admissible and consistent by the triangle
inequality. Dijkstra uses the same graph and binding with a zero heuristic.
Search is shortest only **on this constructed graph**, not globally shortest
in the polygon world. The graph does not contain every obstacle vertex or every
continuous point.

Exploration picks a waypoint on a certified ray near the known-free boundary
that could reveal unknown area. It maintains a stack of visited sensing
positions. When a position has no useful candidate, it returns to the nearest
ancestor with one. The A* return path is accepted only if every segment is
certified and its Euclidean length does not exceed the *actual recorded entry*
length. Otherwise the controller reverses that executed entry trajectory.
The selected return is executed without changing target midway; its measured
length and final anchor are checked after execution. Under static obstacles,
reversible holonomic motion, exact segment execution, and a point robot, the
reverse path is feasible and equal in length to entry, so this local branch
retreat bound holds. This is an exhausted-branch trigger, **not a general
geometric blind-alley detector or the paper's BAR theorem**. Limited sensing
and a fixed 250-decision exploration limit mean goal success is not guaranteed
even when a continuous path exists.

## Implementation map

- `scripts/import_bar_polygon.py` exports `continuous_world` beside the
  unchanged grid rows and provenance. `backend/app/services/bar_continuous_geometry.py`
  owns ground truth, collision checks, and conservative sensing.
- `backend/app/services/bar_continuous.py` owns the observation-only policy,
  online exploration, repeated A*, executed trajectory, locked retreat, and
  metrics. `backend/bindings.cpp` adds only a visibility graph adapter;
  `include/astar/search.hpp` is unchanged.
- `POST /api/bar/continuous` returns observations and frames. Its polygon
  ground truth is never serialized. `frontend/src/robot/ContinuousBarPage.tsx`
  draws the accumulated observations and smoothly interpolates the robot
  between continuous waypoints. Zoom, pan, step, speed, scrub, and next recovery
  remain available.

## Reproduce

After installing `requirements-backend.txt` and building the CPython binding
per the root README, run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'backend;build-cpython'
.venv\Scripts\python.exe -m pytest -q tests\test_bar_continuous.py
.venv\Scripts\python.exe scripts\benchmark_bar_continuous.py
cd frontend
npm test -- --run src/test/barContinuous.test.tsx
```

The benchmark reports scenario, sensing radius, termination status, executed
distance, number of returns, maximum executed retreat/entry ratio, A* calls,
expanded nodes, turns, C++ planning time, overall Python wall time, frame count,
compact episode JSON bytes, and maximum graph size. Wall time and response size
vary by machine and serialization. Use the benchmark script for fresh values;
never substitute the legacy grid table or the original authors' experimental
distances. The imported polygons are independently authored format examples,
not the authors' benchmark maps. The reference research repository is
<https://github.com/ThanhBinhTran/autonomousRobot>.

One Windows run of the command above on 2026-10-09 produced the following
CSV-derived summary. `step_limit` means this run ended after 250 decisions; it
does **not** prove the goal unreachable. `max ratio` is the maximum *executed*
retreat length divided by recorded entry length among local recoveries.

| Map | Radius | Outcome | Executed units | Returns | Max ratio | A* calls | Expanded | Turns | A* ms | Wall s | Frames | Compact JSON bytes | Max graph nodes / edges |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Irregular U | 4 | goal reached | 397.336 | 37 | 1.000 | 125 | 253 | 112 | 13.537 | 4.464 | 453 | 621,144 | 89 / 2,359 |
| Irregular U | 6 | goal reached | 350.402 | 24 | 1.000 | 78 | 160 | 72 | 3.267 | 1.144 | 286 | 403,456 | 55 / 759 |
| Bugtrap | 4 | step limit | 747.503 | 100 | 1.000 | 250 | 502 | 234 | 35.904 | 23.038 | 951 | 1,439,804 | 149 / 4,954 |
| Bugtrap | 6 | goal reached | 690.422 | 58 | 1.000 | 158 | 318 | 146 | 10.646 | 5.736 | 594 | 917,295 | 101 / 1,577 |

The largest run takes most time in Python geometry and graph construction,
not C++ search (35.9 ms cumulative A* versus 23.0 seconds wall time). API
serialization adds overhead and response headers beyond the compact episode
size. This is a bounded offline playback, so the 1.44 MB episode remains
manageable without introducing a streaming service. The browser accumulates
observations through the selected frame; it never receives the complete
polygon world. Faster playback skips no decisions in the simulation itself.

## Scope limits

The zero-radius model does not provide clearance for a physical robot. The
ray-fan sensor is conservative and may leave visible space unexplored.
Candidate selection is deterministic but incomplete; 250 decisions is a
bounded simulation, not a proof of reachability or unreachability. A local
stack return can happen in a general branch rather than a formally identified
BAR. The UI shows only observed obstacle fragments, so incomplete boundaries
are expected. A* planning time excludes Python/Shapely graph construction,
sensing, JSON serialization, and frontend rendering.

## Validation on this branch

On 2026-10-09, `.venv\Scripts\cmake.exe --build build-cpython --parallel 4`
completed; `.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure`
passed 4/4; `PYTHONPATH=backend;build-cpython` with
`.venv\Scripts\python.exe -m pytest -q tests` passed 80/80. In `frontend`,
`npm test` passed 29/29, `npm run build` passed, and `npm run lint` passed.
Python emitted one pre-existing Starlette/httpx deprecation warning. A local
browser check loaded the continuous map, jumped to the final frame, showed
the episode metrics, and used the grid-mode switch. The temporary review
servers were stopped afterward.
