# Radar-informed exploration: implementation and validation

## Scope and root cause

The pre-change controller in `backend/app/services/bar_continuous.py` retained
frontier candidates at each exploration node, but Maze 3 ranked them by
`Area(sensor disk minus known FREE)`. This counted UNKNOWN behind already
observed walls as if it were visible. In the deterministic seed-23/radius-5
audit, seven distinct sibling probes near `(17.489, 15.823)` cost 30.397
units of motion while adding only 0.008099 units² of certified FREE area.
They were real movements, not duplicate target selection or a failed A* return.
The [prior audit](bar-dead-end-behavior-audit.md) and
[full baseline trace](bar-dead-end-decisions-full.csv) preserve the evidence.

## Small correction

`ContinuousPolicy` now optionally retains observed wall fragments alongside
its accumulated certified FREE region. Neither the world polygons, generator
topology, hidden door locations, nor a collision oracle enters the policy.
The API enables this mode for labyrinth and indoor scenarios; old polygon and
room-maze baselines retain their prior policy by default. The physical sensor
and C++ A* implementation are unchanged.

For a candidate viewpoint `p`, the estimate is built from the current
FREE/UNKNOWN boundary after subtracting observed wall fragments and the known
world boundary. Boundary pieces within sensing radius `R` are counted only
when the straight line from `p` to their midpoint lies in accumulated FREE.
For each visible piece of length `L` at midpoint distance `d`, the score adds
`L × (R − d) / 2`. This is an **opportunity proxy**, not a predicted sensor
area or guaranteed information gain. Unknown obstacles can reduce the real
view. The geometry and scores are cached until sensing changes the FREE region
or adds a new observed wall fragment. No candidate invokes the simulator's
full sensing operation.

Maze 3 ranks positive-score candidates by
`estimated_gain / Euclidean_travel_distance^0.25`, then by gain, goal distance,
and coordinates. Euclidean distance is a lower-bound travel estimate, not the
verified A* route length. The sublinear penalty avoids favoring tiny local
views purely because they are close. Indoor mode retains its established
goal-directed ordering among positive-score candidates. Both modes recompute
scores after observations. The previous `_candidate_valid` check and its
existing numeric tolerances remain; this change adds no permanent low-score
blacklist.

A zero-score candidate is **temporarily postponed** while another positive
frontier exists on the active branch or an ancestor. It remains in the node's
candidate list and transfers to a surviving ancestor during return. If no
positive candidate exists anywhere in the retained exploration stack, the
controller revisits postponed candidates under the legacy ranking. Thus a
small hidden door or a false-zero estimate is still eligible for exploration.
Graph-unreachable targets retain the separate existing defer-until-map-or-graph-
change rule. `temporarily_unavailable` is distinct from `exhausted` in the
hierarchy trace. A low score alone does not certify that a branch or physical
blind alley is exhausted.

When the local branch has no currently positive candidate and an ancestor does,
the controller returns to the **nearest viable ancestor**. The existing C++
A* plans the shortest route on the current certified visibility graph; every
edge and executed movement remains inside known FREE. Return execution stays
locked until the ancestor is reached. A verified reversed entry trail remains
the fallback if the graph route is absent, invalid, or longer than the entry
trajectory. Executed retreat length is checked against the recorded entry
length with matching endpoints. These are local conditional return guarantees,
not global shortest-path guarantees in an unknown environment.

## Reproducible comparison

From the repository root on Windows:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar_radar.py --output docs\bar-radar-comparison.csv
.venv\Scripts\python.exe scripts\audit_bar_radar_decisions.py --output docs\bar-radar-decisions.csv
.venv\Scripts\python.exe -m pytest -q tests\test_bar_radar.py
```

The [comparison CSV](bar-radar-comparison.csv) includes every baseline/radar
pair for four labyrinth configurations and three indoor layouts, each at radii
5 and 7. The same generator configuration, endpoints, sensing radius, 250
decision budget, physical collision checks, and C++ A* are used within each
pair. All 28 episodes reached the goal; all recorded returns met the executed
length bound. Representative rows (distance in world units, time in ms):

| Scenario, radius | Policy | Distance | Local audit probes | A* calls | Expanded | Sensing | Ranking | Total wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Blind-Alley seed 23, 5 | baseline | 139.32 | 7 | 45 | 90 | 481 | — | 693 |
| Blind-Alley seed 23, 5 | radar | 78.58 | 0 | 19 | 39 | 204 | 255 | 486 |
| Blind-Alley seed 23, 7 | baseline | 283.76 | — | 76 | 156 | 1,388 | — | 2,331 |
| Blind-Alley seed 23, 7 | radar | 139.93 | — | 24 | 49 | 841 | 1,019 | 1,983 |
| Complex labyrinth, 7 | baseline | 97.04 | — | 22 | 44 | 1,037 | — | 1,274 |
| Complex labyrinth, 7 | radar | 167.82 | — | 31 | 64 | 1,113 | 5,367 | 6,721 |
| Indoor office, 7 | baseline | 625.73 | — | 117 | 234 | 2,126 | — | 5,628 |
| Indoor office, 7 | radar | 238.54 | — | 48 | 96 | 551 | 890 | 1,831 |

These are single-run wall times on the local machine, not statistical runtime
estimates. Baseline ranking time was not instrumented separately. For the
seed-23/radius-5 run, the radar route *bypasses* the audited anchor, hence the
zero local probes and zero distance in that exact audit pocket; this is a route
change, not a replay from an identical local state. A separate counterfactual
test holds the original legacy trajectory fixed through the first eight
decisions and applies the new score at the first local sibling decision. At
that actual observed state, all local candidates have zero plausible visible
frontier score and the policy chooses ancestor return. The test uses only the
sensor observations accumulated along that fixed trajectory.

The [new decision trace](bar-radar-decisions.csv) shows 19 high-level decisions
and 63 playback frames. For example:

| Decision / frames | Action | Position → target | Estimated gain | Motion | New FREE | New wall fragments |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 3 / 7–9 | Explore | `(18.309,3.277)` → `(14.209,3.277)` | 6.469 | 4.100 | 9.674 | 23 |
| 4 / 10–12 | Explore | `(14.209,3.277)` → `(11.174,5.029)` | 7.802 | 3.505 | 5.988 | 18 |
| 5 / 13–19 | A* return | `(11.174,5.029)` → ancestor `(18.309,3.277)` | — | 7.605 | 0 | 0 |
| 6 / 20–22 | Explore sibling | `(18.309,3.277)` → `(18.309,7.377)` | 5.556 | 4.100 | 9.832 | 19 |

Decision 5 is labelled `occluded_frontier_deferred`, not a certified physical
BAR. It used A*, did not invoke the reversed-entry fallback, and then explored
a surviving sibling. `new_wall_fragments` counts first-seen quantized sensor
segments, not blocked area or unique physical wall length. FREE area alone
would miss useful wall observations. A decision is separate from its movement
segments and playback frames; the CSV records the frame span of each decision.

## Verification and limitations

Targeted tests cover the exact audited-state counterfactual, a resolved
terminal frontier, a hidden side doorway, an irregular corner, wall-only
observations, graph-blocked target preservation, sibling transfer, A* shortcut
return and reversed-entry fallback. Existing seeded labyrinth and indoor
episodes cover furniture, multiple doors, hallway cycles, two radii, collision
checks, and return bounds. All legacy grid, continuous, and Road Navigation
tests remain in the full regression suite.

The opportunity proxy can rank an ultimately obstructed frontier highly or
assign a real continuation zero because observed wall fragments and FREE
boundary geometry are approximate. The fallback eligibility rule protects
exploration completeness relative to the existing candidate generator, but
neither it nor the original controller proves complete exploration of all
continuous unknown space. The complex labyrinth at radius 7 is a measured
regression: 167.82 units and 6.72 s versus 97.04 units and 1.27 s. The
gain-focused choice reaches a different branch first; ranking itself costs
5.37 s there. The comparison is an engineering evaluation, not a claim of
uniformly better routes or globally optimal online navigation.

## Full regression commands and results

From the repository root, `.venv\Scripts\python.exe -m pytest -q` passed
**145 tests** (one existing Starlette `httpx` deprecation warning). The four
C++ executables `build-cpython\core_tests.exe`,
`build-cpython\reference_tests.exe`,
`build-cpython\road_tests.exe data\road\graph.json`, and
`build-cpython\edge_snap_tests.exe data\road\graph.json` all passed. In
`frontend`, `npm run test -- --run` passed **34 tests across eight files**;
`npm run build` and `npm run lint` passed. The first frontend run found an
unnecessary `debug_exploration: false` request field; that was corrected and
the full frontend suite was rerun successfully. C++/Road code and tests were
not changed.
