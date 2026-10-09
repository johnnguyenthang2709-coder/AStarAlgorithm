# Indoor radar/frontier-cache integration review

Reviewed on `codex/bar-frontier-performance`. The Git ancestry is
`b8c4f4c` (parent-aware return) → `88ab9f9` (indoor layouts, trace, API, UI)
→ `01ced69` (radar-informed exploration) → `4c12e37` (incremental frontier
mask). `codex/bar-indoor-hierarchical` still points to `88ab9f9`; the current
branch already contains all its changes. No cherry-pick, reset, or merge into
`main` is needed. Use the current branch for the integrated demonstration;
advance the indoor branch only through an explicit, reviewed fast-forward if
that branch name must remain the delivery name.

## Coverage and information boundary

`bar_indoor.py` builds three deterministic geometric floor plans with eight
nonuniform rooms each, doors, corridors, furniture, partitions, and storage
shelves. It validates connected polygonal free space, clear door apertures,
and valid start/goal positions. The hierarchy is an **observed exploration
anchor tree**, not semantic room recognition. Each completed exploration
movement creates a child anchor. The controller selects the nearest ancestor
with an available candidate when the active node has none. An unreachable
graph target is deferred until the known map/scan graph changes; a radar
zero-score frontier remains pending and may later be tried as a fallback.

The router retains the complete `IndoorLayout` only to construct the simulator
world and return its configuration. `simulate_continuous` instantiates
`ContinuousPolicy` with start, goal, bounds, and radius; the policy receives
only `SensorObservation` regions, candidates, and visible wall fragments.
Physical collision checks and sensing use the simulator's world outside the
policy. Tests verify that furniture occludes sensing, that the initial known
free area is smaller than ground-truth free space, and that API playback does
not serialize rooms, doors, or furniture. The known goal coordinate and world
bounds are intentional public inputs.

## Reproducible navigation evidence

`bar-indoor-radar-results.csv` runs the same radar ranking, complete frontier
route, and hierarchy flags as the API. The older `bar-indoor-results.csv` and
`bar-indoor-trace.csv` are pre-radar historical runs, not current UI results.
`benchmark_bar_indoor.py --policy legacy` reproduces that ranking. The
current-policy six presets at radii 5 and 7 all reach the goal. Their 13
returns use C++ A*, have no reversed-entry fallback, and satisfy the measured
executed-return bound. Apartment radius 5 shows three `exhausted_branch`
returns to the observed parent, each followed by a new sibling. Apartment
radius 7 also shows a return to ancestor 9 after a radar-pending frontier;
the A* path is 15.213 versus a 55.003 entry. This latter trigger is
`occluded_frontier_deferred`, **not** proof of branch exhaustion. The focused
test checks its A* path cost against C++ Dijkstra on exactly the same known
visibility graph. Challenge reaches the goal without returning at either
radius under the current ranking; use Apartment or Office to demonstrate
parent backtracking. The 12 additional layout/seed/radius pairs in
`bar-indoor-radar-heldout.csv` also reach the goal, without filtering failure
outcomes. These finite tests do not establish general completeness.

The existing 20-pair frontier benchmark includes all six current indoor
preset/radius pairs and reports identical full-reconstruction versus cached
playback, recoveries, status, and distance. Added tests compare complete
decision traces, candidate scores and eligibility, frontier geometry, and
exact episode frames for Apartment 5/7, Office 5/7, and Challenge 5. A
synthetic doorway test covers a FREE-only reveal followed by a new wall
fragment, repeated observations, and full-reconstruction fallback. Thus the
mask reuses only accumulated observed walls and invalidates on newly sensed
free space or walls; no hidden doorway geometry enters the score.

The production six-run results are:

| Layout | Radius | Goal | Distance | Returns | A* calls | Expanded |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Apartment | 5 | reached | 137.268 | 4 | 35 | 72 |
| Apartment | 7 | reached | 147.859 | 4 | 30 | 64 |
| Office | 5 | reached | 122.018 | 2 | 32 | 64 |
| Office | 7 | reached | 238.537 | 3 | 48 | 96 |
| Challenge | 5 | reached | 94.644 | 0 | 23 | 46 |
| Challenge | 7 | reached | 109.168 | 0 | 21 | 42 |

`bar-indoor-radar-trace.csv` records the Apartment radius-5 parent/next-sibling
sequence. The test also checks that successful exploration targets are not
selected twice in these six runs. Deferred targets are allowed to be retried
after new observations; that is different from repeatedly selecting an
obsolete completed target. All movement segments are physically checked in
the simulator and must be certified by the policy's discovered free space.

## Validation and readiness

From the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
build-cpython\core_tests.exe
build-cpython\reference_tests.exe
build-cpython\road_tests.exe data\road\graph.json
build-cpython\edge_snap_tests.exe data\road\graph.json
```

From `frontend/`:

```powershell
npm run test -- --run
npm run build
npm run lint
```

The full regression suite passed 164 Python tests, 34 frontend tests, the
frontend build and lint, and all four C++ executables. One existing
Starlette/httpx deprecation warning remains. The first frontend invocation
from the repository root failed because `package.json` is under `frontend/`;
the commands above passed in the correct directory.

The integrated branch is ready for a **bounded university demonstration** of
limited sensing, online geometric mapping, frontier exploration, repeated
C++ A*, observed-parent returns, and a locally verified retreat bound.
Select Apartment or Office when showing recovery. Do not claim semantic room
recognition, formal paper BAR classification, global optimality in an unknown
map, completeness for arbitrary seeds/radii, or shortest paths in continuous
free space: A* is shortest on the currently constructed visibility graph.
The point-robot, static-wall, exact-motion and finite-decision-budget
assumptions still apply. No navigation policy, C++ A*, Road Navigation, or
existing validated scenario was changed in this review.
