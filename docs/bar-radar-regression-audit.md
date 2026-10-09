# Comparative behavioral audit: radar-informed exploration

**Scope:** audit only. The navigation policy, C++ A*, sensor, scenario generator,
tests, and UI were not changed. The inspected branch is
`codex/bar-radar-informed-exploration` at `01ced69`. The artifacts below are
uncommitted audit outputs so that the committed implementation remains a fixed
comparison baseline.

## 1. Reproduction and method

The regression is **Complex Irregular Labyrinth** (`COMPLEX`: seed 2026, size
6, corridor width 2.05, loop rate 0.22, dead-end rate 0.6, trap count 4,
normal difficulty, irregularity 0.88), radius 7, start
`(27.170154,27.229055)`, goal `(2.752172,2.147292)`. Both policies use the
same generated geometry, 250-decision budget, limited 360° sensor, certified
visibility graph, C++ A*, and complete frontier route execution. Only the
`radar_informed` policy flag differs. The simulator has ground truth solely for
sensing and collision checks; the candidate audit uses `ContinuousPolicy`'s
discovered geometry and observed sensor fragments.

Run from the repository root:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar_radar.py --cases lab_complex --radii 7 --output docs\bar-radar-regression-reproduction.csv
.venv\Scripts\python.exe scripts\audit_bar_radar_regression.py
.venv\Scripts\python.exe scripts\audit_bar_radar_benchmark.py
```

The dedicated [reproduction CSV](bar-radar-regression-reproduction.csv)
confirms the deterministic distance and A* counts:

| Policy | Status | Executed distance | A* calls | Expanded | Returns | Sensing | Ranking / selection | Wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Legacy | goal reached | 97.044 | 22 | 44 | 3 | 448 ms | not separately instrumented | 553 ms |
| Radar | goal reached | 167.816 | 31 | 64 | 1 | 620 ms | 4,819 ms | 5,655 ms |

This is a new runtime measurement, not an exact repeat of the earlier 1.27 s
and 6.72 s times. A second fully instrumented paired run measured 1.054 s
versus 8.211 s; the route lengths, A* calls, status, and return counts were
identical. Wall times vary with machine conditions and instrumentation, while
the large ranking overhead repeats. Neither run hit the decision budget.

The read-only instrumentation wraps `observe()` and `select()`, restores them
after each episode, and probes candidate A* costs only on a shallow copy with
an independent verified-link set. It does not steer either policy. The
[legacy decision trace](bar-radar-regression-baseline-trace.csv) has 22
decisions; the [radar trace](bar-radar-regression-radar-trace.csv) has 31. Each
CSV separates decision index, playback frames, executed movement, and the
subsequent sensor observation. The [first-divergence JSON](bar-radar-first-divergence.json)
contains both policies' exact known-FREE GeoJSON, observed wall segments,
stack state, and all candidate scores at the common decision state.

## 2. First meaningful divergence: decision 2

Decision 1 is identical: both move from `(27.170154,27.229055)` to
`(21.430154,27.229055)`. At decision 2 their discovered FREE GeoJSON and
observed wall fragments are byte-for-byte equal. They know 29.448 units²
FREE; 870.552 units² of the 900-unit² world remains unverified. **BLOCKED**
information consists of 51 observed wall fragments, not a measured blocked
area. Geometry behind those fragments is UNKNOWN. The active exploration
branch is ID 1 with parent ID 0 at the start. The stack has one candidate at
the parent and four stored at the active node; one of the four is ineligible
because it is an already scanned position. Three candidates are eligible and
graph-reachable.

| Candidate | Legacy unknown-disk area | Radar frontier proxy | Radar utility | Euclidean lower bound | Verified A* cost | Eligible |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `(23.910,28.661)` | 68.470 | 0.242 | 0.186 | 2.863 | 2.863 | Yes |
| `(15.690,27.229)` | 96.336 | 18.119 | 11.706 | 5.740 | 5.740 | Yes |
| `(19.243,25.966)` | 104.445 | 5.082 | 4.031 | 2.526 | 2.526 | Yes |

The legacy policy selects `(19.243,25.966)` because its disk-based unknown
area is largest. Radar selects `(15.690,27.229)` because its visible-frontier
proxy divided by `travel^0.25` is largest. Both routes are direct certified A*
edges; there is no graph detour or Euclidean-versus-A* cost error at the
divergence. The next observation after legacy's 2.526-unit move adds 4.229
units² FREE and 23 newly recorded wall fragments. Radar's 5.740-unit move
adds 15.297 units² FREE and 27 fragments. These are actual observations, not
ground-truth claims about what lies farther down either branch. At this shared
state, the radar choice provides **more immediate measured information**.

The later motion explains the total distance difference. Radar continues
west along the upper corridor, later travels east through discovered space,
then explores toward the southern edge. Its one A* return at decision 25
travels 14.661 units to a verified ancestor before it continues west toward
the goal. Legacy takes a different central exploration sequence and reaches
the goal at decision 22. In the paired run, radar's extra 70.772 units split
into **+67.790 exploration**, **+4.545 retreat**, and **−1.563 final-goal
motion**. Thus the long return is a secondary contributor; most of the
regression is changed online exploration order. This conclusion uses executed
traces, not hidden map topology.

## 3. Runtime breakdown

The instrumented paired run measured:

| Work | Legacy | Radar | Radar minus legacy |
| --- | ---: | ---: | ---: |
| Sensing | 864 ms | 1,270 ms | +406 ms |
| Target selection | 88 ms | 6,648 ms | +6,560 ms |
| C++ A* search calls | 0.553 ms | 0.949 ms | +0.396 ms |
| Total wall | 1,054 ms | 8,211 ms | +7,158 ms |

The wall difference is dominated by target selection, not C++ A* or the
physical sensor. An independent profile of the radar run attributed **3,237
of 3,374 ranking milliseconds (96%)** to 29 calls of
`possible_frontier()`, versus 36 ms for 142 candidate gain evaluations.
The helper repeatedly buffers the entire growing set of observed wall
fragments and subtracts it from the full known-FREE boundary. The first call
with 17 fragments took 0.6 ms; late calls with roughly 700–816 fragments took
hundreds of milliseconds (up to 344 ms in that profile). Per-run timing varies,
but the growth pattern and dominant operation are reproducible. Cached scores
are invalidated after new FREE area or new wall fragments; this run made new
observations at essentially every exploration step, so the expensive frontier
is rebuilt 29 times.

## 4. Paired robustness audit

The [paired audit CSV](bar-radar-paired-audit.csv) reruns the original 14
configuration/radius pairs (28 episodes) and six **prespecified held-out
pairs**: default labyrinth seeds 41, 73, and 911 at radii 5 and 7. These seeds
were selected before running the audit and were not filtered for outcomes.
`revisits` counts executed movements ending exactly (within 1e-6) at any
previously reached waypoint; it is not a measure of overlapping sensor views.
Times are one local run per pair, not confidence intervals.

| Group | Pairs | Goal reached | Radar shorter | Median paired distance ratio | Worst distance ratio | Median paired wall-time ratio | Worst wall-time ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 14 | 28/28 episodes | 13/14 | 0.617 | 1.729 | 0.721 | 7.794 |
| Held-out | 6 | 12/12 episodes | 5/6 | 0.431 | 1.059 | 0.498 | 1.447 |
| Combined | 20 | 40/40 episodes | 18/20 | 0.571 | 1.729 | 0.670 | 7.794 |

The two radar distance regressions are complex/radius 7 (1.729× distance,
7.794× wall time) and held-out seed 911/radius 7 (1.059× distance, 1.447×
wall time). Across these 20 pairs, exact-waypoint revisit medians are 13 for
legacy and 2 for radar; total A* calls are 1,173 versus 511 and expanded
nodes 2,402 versus 1,059. Legacy made 324 recorded returns and radar 34;
all 358 returns were certified against their recorded entry trajectories and
none used reversed-entry fallback in these particular episodes. The audited
seed-23/radius-5 case still has seven versus zero probes from the documented
anchor. These are descriptive results on selected deterministic maps, not a
claim of statistical or worst-case superiority.

## 5. Competing explanations

| Hypothesis | Evidence and counterevidence | Verdict |
| --- | --- | --- |
| **A. Occlusion proxy underestimates useful candidates** | At the first shared decision, the chosen radar target has proxy 18.119 versus 5.082 for legacy's target and yields 15.297 versus 4.229 new FREE area. Later proxy/actual FREE gain is noisy, and wall discovery is another kind of information. This audit cannot certify scores for every unvisited frontier. | **Rejected as the first-divergence cause; unresolved globally.** |
| **B. Travel cost is underweighted** | Utility divides gain by distance^0.25, so the longer 5.740-unit candidate is only mildly penalized. Yet dividing by full distance still favors it (3.157 versus 2.012), and verified A* equals Euclidean cost for all three candidates at divergence. Across all 29 selected radar exploration routes here, no selected route has an A* detour over its Euclidean estimate. | **Plausible objective trade-off, not a demonstrated cost-estimation defect.** |
| **C. Delayed low-score frontiers cause long returns** | The sole radar return is triggered by `occluded_frontier_deferred` and is 14.661 units, versus 10.117 total legacy retreat. It is certified and A*-computed, with no fallback. The +4.545 retreat difference explains only a small part of +70.772 total distance. | **Secondary contributor, not primary cause.** |
| **D. Stale cached scores** | `observe()` clears frontier and scores on new FREE area or wall fragments; new sensing occurred through the exploration sequence. The profile records 29 frontier rebuilds for 29 explore decisions. Wall-only invalidation is also covered by the existing focused test. | **Rejected for this run.** |
| **E. Different valid exploration ordering** | First choice is based on identical online observations and immediately gains more information; later executed paths differ substantially. Both reach the goal without collision or budget exhaustion. | **Supported as the distance cause.** |
| **F. Additional visibility computation** | Target selection rises from 88 to 6,648 ms in the paired run; repeated global frontier construction is 96% of ranking in a separate profile. Sensing rises by only 406 ms, partly because radar makes more observations here. | **Confirmed computation cause.** |
| **G. Controller or graph fault** | Three first-divergence candidates are graph-reachable; selected routes have direct certified A* cost. No graph-unreachable target or fallback caused the divergence. The lone radar return is A*-computed and bound-certified. | **No fault found in this run.** |

## 6. Correction options and decision

1. **First priority: bound frontier construction without changing its
   geometry.** Cache or incrementally update the observed-wall buffer, or
   restrict exact wall processing to boundary-relevant fragments, then verify
   equality of candidate scores, hidden-door/corner tests, and full paired
   traces. The risk is geometric tolerance drift that suppresses a real
   frontier; optimization must preserve the current uncertain-candidate
   fallback. This addresses a confirmed cost, not the route-order trade-off.
2. **If route regressions remain unacceptable, compare a small number of
   preregistered gain/travel balances** on the same pairs and held-out maps.
   A stronger distance penalty or limited goal-progress term may select the
   shorter local move, but could lose the seed-23 improvement or delay useful
   hidden-door exploration. Do not choose a weight merely to fix seed 2026.
3. **Keep zero-score candidates provisional.** The existing transfer and
   fallback rule protects uncertain continuations. There is no evidence to
   mark these branches permanently EXHAUSTED or to alter A* recovery.

**Recommendation:** retain occlusion-aware sensing and the current committed
policy pending approval for a focused performance correction. Do not revert
the ranking based on this one route regression: it is a legitimate online
ordering trade-off in the observed state, and 18 of 20 paired configurations
travel less. Do not claim the current ranking is uniformly faster or shorter.
No algorithmic correction is implemented in this audit.
