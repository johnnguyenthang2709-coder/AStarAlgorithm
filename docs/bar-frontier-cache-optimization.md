# Incremental frontier wall-mask optimization

Implementation branch: `codex/bar-frontier-performance`, based on radar
commit `01ced69`. The earlier comparative-audit files remain unchanged.
No target weights, candidate rules, C++ A*, sensing, Road Navigation, or UI
behavior were changed.

## Bottleneck and selected strategy

Before this change, `ContinuousPolicy.observe()` invalidated `_frontier`
after new FREE area or observed walls. The next `_frontier_gain()` called
`possible_frontier()`, which buffered a `MultiLineString` containing **every**
previously observed wall fragment. In the complex labyrinth at radius 7,
this full buffer and boundary subtraction was rebuilt 29 times as the wall
collection grew to hundreds of segments. The preceding audit measured
3,237 of 3,374 ranking milliseconds in this one helper.

The policy now maintains a buffered mask of observed walls. On each sensor
observation it buffers **only newly recorded fragments** and unions that
buffer into the existing mask. `possible_frontier()` still subtracts the
wall mask from the entire current known-FREE boundary and excludes the world
border. It still evaluates every eligible candidate. The original full
`MultiLineString(walls).buffer()` path remains available by passing no mask;
it is the authoritative reference and the fallback when an incremental mask
is invalid, an overlay raises `GEOSException`, or a restored policy state's
wall count does not match its mask. No hidden world geometry is read.

The cache rules are deliberately narrow:

| State change | Action | Why |
| --- | --- | --- |
| New sensed FREE area | Rebuild frontier and prepared-FREE geometry; retain wall mask | FREE/UNKNOWN boundary and visibility may change. |
| New observed wall fragments, even without FREE gain | Extend wall mask; rebuild frontier and scores | A formerly open boundary may now be observed BLOCKED. |
| Repeated observation with no geometry change | Reuse wall mask, frontier, and candidate scores | Inputs are unchanged. |
| New doorway or corridor revealed by sensing | Same FREE/wall invalidation | Its effect enters only through observed geometry. |
| New scan waypoint / graph connectivity | Recheck deferred candidates; geometric mask unchanged | Reachability changes in `available()`, not wall geometry. |
| Target completion or parent-stack transition | Recompute candidate availability on selection; retain geometric mask | Candidate ownership changes, while sensed geometry does not. |
| Mask invalid or out-of-band wall-count mismatch | Use full reconstruction | Avoid an incomplete cached frontier. |

Low-score targets remain postponed rather than discarded. Graph-blocked
targets still wait for a verified map/graph change. Ancestor return, C++ A*
planning, locked retreat, and reversed-entry fallback are unchanged.

## Semantic equivalence

The [benchmark CSV](bar-frontier-cache-benchmark.csv) compares a forced full
reconstruction against the production cache for the original 14
configuration/radius pairs plus held-out labyrinth seeds 41, 73, and 911 at
radii 5 and 7. Both variants run the **radar-informed policy** with identical
world, seed, sensing, start/goal, and 250-decision budget. Every one of the
20 pairs has exactly equal playback frames, recoveries, goal status, and
executed distance. The focused tests additionally compare stack and parent
state, deferred/pending targets, eligible counts, selected target, candidate
scores, and frontier geometry. The tested scenarios include audited seed 23,
complex/radius 7, indoor furniture, multi-door rooms, side-door/corner
geometry, siblings, graph-deferred targets, repeated observations, and both
FREE-only and wall-only geometry changes.

GEOS union order can cause negligible coordinate differences, so exact WKB
identity of frontier linework is **not** promised. Across the 29 observed
frontier states in the complex/radius-7 prototype, Hausdorff distance from
the full reconstruction was at most `6.1e-11`, and the largest candidate
score difference was `2.5e-10`; no zero-score eligibility threshold changed.
Regression tests require frontier Hausdorff distance `<1e-8`, score absolute
difference `≤1e-8`, identical positive/zero classification, and identical
decisions. A forced incremental-union exception also verifies fallback to
full reconstruction. Full-episode playback equality across all 20 pairs is a
stronger behavioral check. These tolerances describe floating-point overlay effects,
not permission to change target ranking.

## Before/after performance

The same-process paired benchmark reports the following for **Complex
Irregular Labyrinth, radius 7** (times in ms):

| Measure | Full reconstruction | Incremental mask |
| --- | ---: | ---: |
| Goal / distance | reached / 167.815890 | reached / 167.815890 |
| A* calls / expanded nodes | 31 / 64 | 31 / 64 |
| Frontier query calls | 29 | 29 |
| Full global wall reconstructions | 29 | 0 |
| Incremental mask updates | 0 | 31 |
| Frontier-query total | 2,813 | 54 |
| Frontier-query mean / p95 | 97.0 / 237.4 | 1.87 / 3.16 |
| Mask-update total / mean / p95 | — | 62.5 / 2.02 / 2.87 |
| Ranking time | 2,931 | 162 |
| Total simulation wall time | 3,484 | 782 |
| Candidate score calls / cache hits | 415 / 273 | 415 / 273 |
| Mean eligible candidates per decision | 3.71 | 3.71 |

Across **all 20 pairs**, frontier-query time totals 7,723 ms full versus
495 ms cached, plus 606 ms for incremental updates. The median paired
frontier-query time ratio is **0.098** and the median total simulation-time
ratio is **0.748**. The slowest relative total result is 0.996, so this set
contains no measured total-runtime regression. Full reconstructions fall
from 457 to zero; 497 incremental updates occur. There are 7,642 score calls
and 3,979 score-cache hits in either variant, confirming the candidate set
and scoring work were retained. Single-run wall times are sensitive to host
load and should not be interpreted as a statistical guarantee.

The extra native GEOS wall mask has a median final serialized WKB size of
47,673 bytes across these episodes and a maximum of 84,709 bytes. WKB size
is a reproducible geometry-size proxy, **not** total process RSS or a precise
native allocation measurement. The observed-wall dictionary already existed
and is retained by both variants.

## Reproduction and regression

Run from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_bar_frontier_cache.py -q
.venv\Scripts\python.exe scripts\benchmark_bar_frontier_cache.py
.venv\Scripts\python.exe -m pytest -q
```

The benchmark exits with an assertion if any paired playback or recovery
changes. `--cases lab_complex lab23 --radii 5 7` reproduces a faster focused
subset. The full Python suite passed **153 tests** (one pre-existing Starlette
`httpx` deprecation warning). Frontend tests passed **34/34**, production
build and lint passed, and the four C++ executables (`core_tests`,
`reference_tests`, `road_tests`, `edge_snap_tests`) passed. The source and
fixtures for the previous comparative audit were preserved.

## Remaining limits

Incremental union still processes the growing native wall-mask geometry, so
very large or adversarial maps may eventually make updates expensive. The
cached frontier still intersects the entire known-FREE boundary; only the
repeated **all-wall buffering** was removed. The mask fallback protects
correctness if GEOS rejects an update, but then performance returns to full
reconstruction for that policy instance. The prior complex/radius-7 **travel
distance** regression remains 167.816 versus the legacy ranking's 97.044:
this change deliberately addresses computation without altering online
exploration order.
