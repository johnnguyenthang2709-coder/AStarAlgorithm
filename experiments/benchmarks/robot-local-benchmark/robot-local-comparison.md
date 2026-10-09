# Frozen shared-state local robot path benchmark

## Scope and feasibility decision

**Feasible for a point robot under the stated interior-only convention.** This is a comparison of **planned local paths at frozen decisions**, not an end-to-end navigation, robot-motion, or isolated search-algorithm comparison. It does not lift the validity gate on the 48 matched end-to-end configurations in `robot-authors-vs-astar.csv`.

The [motion-validity audit](../author-motion-validity-audit.md) established why the direct end-to-end result was blocked. The present study uses the unchanged authors' bundle-based `approximately_shortest_path` (`Robot_paths_lib.py:29–43`) and unchanged C++ `astar_core.visibility_search` called with the current continuous adapter's scan-center vertices (`backend/app/services/bar_continuous.py:308–329`). It does **not** use the authors' separate grid A* baseline or reproduce the paper's Section 6.2.1 table. Sections 3 and 4.5–4.6 of the paper describe DAP/bundle shortening and online selection; Section 6.2.1 concerns explored-space local path comparison. The methods here have the **same observed information and endpoints but different planning graphs**.

## Frozen data and input equivalence

- Dedicated branch: `codex/robot-local-shared-state`; frozen input commit `23c3ba0147753354054e0e7d52d7f6e84ef81bb1`. It descends from motion-audit `0631f6c` and academic baseline `da96440`. Authors' clean checkout remains at `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`.
- [Manifest](robot-local-benchmark-manifest.json) fixed the selection and measurement rules **before the retained paired metrics**. [Snapshots](robot-local-snapshots.json) have SHA-256 `1bb3c927348e11bb2b7ccca151548b1da12ee5550284ccb7b60631d45a44aa9b`. They preserve all **43** source decisions from the two original smoke runs, including each current coordinate, selected target, full accumulated `visited_sights` (centers, closed and open sight records), source graph edges, original skeleton and ASP vertices, radius, source revision, and original map hash. Captured paths exactly match the previous motion-audit trace. The upstream checkout is never modified. Runtime timings were excluded from the frozen file; two independent captures produced the same hash.
- Eligibility was fixed as **skeleton path with more than two vertices**, which invokes bundle optimization. There are **six eligible** decisions (five dead-end, one bugtrap); their selected targets are not visible from the current sight. All **37 excluded** two-vertex decisions remain in the snapshot file and [geometry CSV](robot-local-geometry-validation.csv) with the reason `excluded_direct_two_vertex_path`. No eligible outcome was dropped.
- A single sight's free region is defined by its center/radius and visible blocking segments. A point is visible when its center-to-point ray meets no recorded blocker before the point. Our [geometry adapter](../robot_local_geometry.py) certifies a proposed graph link across the **entire** line, splitting it at circle, blocker, and blocker-endpoint-ray events. It reads only frozen sight records; it never reads the source map. This gives A* the same accumulated observed information that the authors' `inside_local_sights` and ASP use (`Robot_sight_lib.py:416–439`, `Robot_paths_lib.py:233–251`). It does not give the methods identical graphs: source skeleton graph nodes include open points, while our adapter uses accumulated scan centers plus common endpoints, as `ContinuousPolicy.plan` does. Unlike the application's Shapely `known_free` polygon, the frozen adapter uses an analytic sight-union segment certificate to avoid approximating away circular observed regions.
- Deterministic equivalence check: **0 disagreements in 21,500** fixed-seed point queries between the original `inside_local_sights` predicate and the derived visibility predicate, across all 43 snapshots. **9,801/9,801** sampled interior points of A* graph links were covered by the original source predicate. The event-based certificate checked all 99 accepted A* links continuously under the recorded straight-blocker and circular-range model. As an independent **offline** check after planning, all 99 links had zero intersections with original polygon interiors or boundaries. All 196 original ASP segments, including the direct cases, were certified by the recorded sights. These empirical checks do not constitute a general proof that the authors' sensor implementation is perfect for every map.

The source originally sensed each state from full obstacle data; that is how an online simulator works. Only the resulting recorded sight fragments entered the frozen local planners. Ground-truth polygons were loaded solely **after both methods had written their plans**, for path validity and validation figures. Some source states arose from its discrete coordinate jumps; this study compares local plans at those recorded states and makes no claim that the source robot physically reached every state along a collision-free continuous trajectory.

## Common geometry and measurements

The primary model is a **point center**. A path is primary-valid if its endpoints match within `1e-7`, every segment lies in the closure of the accumulated observed sight union, and no segment's interior enters a polygon interior. Obstacle-boundary tangency is permitted in this primary convention. A separately reported **strict** convention rejects any boundary contact. The world is limited by observed sights, not by an unobserved full-map rectangle. Numerical event tolerance is `1e-9`; straight paths were not smoothed, clipped, offset, or repaired. Clearance to the original obstacles is an offline diagnostic. These point-center results **do not validate a radius-0.5 robot**. The original dead-end scenario's final goal itself has less than 0.5 clearance, as documented in the motion audit.

Path length is the Euclidean sum of consecutive planned vertices. A geometric turn is a nonzero heading change above `1e-6` radians; a significant turn exceeds 15°. Tiny ASP polyline zigzags therefore count in the all-turn measure; the 15° measure is often more interpretable. A* expanded nodes are C++ search states, not comparable to ASP critical-line operations. Timings are median wall times after three warm-ups and 31 measured repetitions per snapshot. ASP ran in Python 3.14.2; the C++ A* binding ran in Python 3.12.10. A* observed-link construction and its core binding call are **separate columns**. Source skeleton generation, online sensing, and exploration are excluded from the local timing. Windows scheduling, different runtimes, and algorithmic representation differences preclude an algorithm-only speedup claim.

The authors' function returns critical-line construction and optimization times, which are retained in the paired CSV. It does **not** expose the number of optimization iterations; this benchmark records no invented iteration count. The C++ extension came from the existing CMake Release build with MSYS2 UCRT64 `g++`. The assigned paper was checked locally at `D:/Downloads/2025-AnHAnhBinhHoai-Sequence-BlindAlleyRobotNavigation-RAS.pdf` (SHA-256 `8b9c99babedf9f2addc329c8bc26a1ca27448bdb6170139ded5607621f9c6b6b`).

## Paired results

All six paths from **each** method had matching endpoints, were covered by the same observed-sight model, and avoided obstacle interiors. Both methods found every eligible local path. Values below are world units. `Turns` is all/significant (over 15°). Asterisk on strict status means obstacle-boundary contact invalidates the path under the strict convention.

| Snapshot | Authors' ASP length | Our A* length | ASP turns | A* turns | ASP strict | A* strict | Minimum clearance ASP / A* |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| Dead-end 03 | 58.17 | 80.00 | 5 / 5 | 3 / 3 | No* | Yes | 0 / 0.625 |
| Dead-end 05 | 64.02 | 77.17 | 4 / 2 | 2 / 2 | Yes | Yes | 0.340 / 2.186 |
| Dead-end 10 | 61.55 | 80.00 | 8 / 5 | 3 / 3 | No* | Yes | 0 / 1.273 |
| Dead-end 11 | 38.20 | 38.27 | 3 / 3 | 1 / 1 | Yes | Yes | 0.285 / 0.067 |
| Dead-end 12 | 43.50 | **38.27** | 2 / 1 | 0 / 0 | Yes | Yes | 2.453 / 0.142 |
| Bugtrap 12 | 167.67 | 169.33 | 58 / 5 | 4 / 4 | No* | Yes | 0 / 0.333 |

ASP is shorter in **five** primary-valid pairs; A* is shorter in **one**. The median paired `A* − ASP` length is **+7.403 world units**. This is largely a **graph-representation effect**: the ASP can bend through critical bundles while the current A* adapter's vertices are sparse scan centers. It does not establish that A* search is intrinsically worse at shortest paths. On the three pairs where **both** routes meet the strict no-boundary-contact rule, ASP is shorter in two and A* in one. We do not rank a shorter boundary-touch path as strict-valid. The source skeleton-to-ASP shortening is a separate within-method measurement in [the paired CSV](robot-local-asp-vs-astar.csv); it is not an A* comparison.

Within the authors' method alone, the original skeleton paths were shortened by **21.829, 15.982, 18.454, 21.798, 16.497, and 32.329** world units, respectively (median **20.126**). This measures bundle refinement against its own skeleton; it is separate from the A* comparison.

Median across the six rows: ASP length **59.86**, A* length **78.59**; ASP all-turn count **4.5**, A* **2.5**; significant turns **4.0** and **2.5**. Marginal medians need not describe any one pair. The bugtrap ASP has 58 very small heading changes but only five above 15°; this is a property of its returned 78-vertex polyline and the explicit turn definition, not evidence of 58 meaningful steering events.

### Timing and graph effort

| Snapshot | ASP core median (ms) | A* link build median (ms) | A* binding call median (ms) | A* nodes / links / expansions |
| --- | ---: | ---: | ---: | ---: |
| Dead-end 03 | 62.655 | 1.662 | 0.0041 | 5 / 4 / 5 |
| Dead-end 05 | 14.146 | 5.183 | 0.0060 | 7 / 7 / 4 |
| Dead-end 10 | 3.034 | 25.955 | 0.0226 | 12 / 15 / 5 |
| Dead-end 11 | 15.607 | 33.209 | 0.0181 | 13 / 17 / 3 |
| Dead-end 12 | 1.395 | 81.771 | 0.0296 | 14 / 24 / 2 |
| Bugtrap 12 | 552.048 | 89.114 | 0.0374 | 14 / 32 / 9 |

The six-row medians are **14.876 ms** ASP core, **29.582 ms** A* sight-link build, and **0.02035 ms** C++ binding call. The A* call is fast on these small sparse graphs, but its sight-link construction can dominate. The methods use different languages and representations, so dividing core times would be misleading. Raw 31-sample timings are retained in [authors-asp-timing.json](authors-asp-timing.json) and [astar-plans.json](astar-plans.json). Per-snapshot minimum, quartiles, median, and maximum are in the [timing-distribution CSV](robot-local-timing-distributions.csv) and [boxplot](robot-local-timing-distributions.png); they show run-to-run spread rather than an inferred algorithmic speedup.

## Figures, validation, and exclusions

- [Paired lengths](robot-local-paired-lengths.png), [turns](robot-local-paired-turns.png), [median timing](robot-local-paired-timing.png), and [timing distributions](robot-local-timing-distributions.png) show every eligible case.
- Representative maps: [dead-end observed state](deadend-03-observed.png), [bugtrap observed state](bugtrap-12-observed.png). Light blue sight footprints are **display-only radial approximations**; the planner used analytic segment certification. Dark lines are known blocker fragments. Hidden obstacle polygons are omitted from these planner-input views.
- Separate offline views: [dead-end original obstacles](deadend-03-ground-truth-validation.png), [bugtrap original obstacles](bugtrap-12-ground-truth-validation.png). Ground truth was used only for post-plan validation and is not an A* input.
- [Geometry validation CSV](robot-local-geometry-validation.csv) records all 37 exclusions and both methods' status on each eligible snapshot. [Validation summary](robot-local-validation-summary.json) gives the equivalence and coverage counts. The [paired CSV](robot-local-asp-vs-astar.csv) includes skeleton length, graph sizes, endpoint errors, interior and boundary checks, clearance, turns, timings, and A* expansions. There were **no planning failures** in this six-case eligible set; the scripts retain failure fields and would not silently drop a failed case.

## Reproduction

On Windows from repository root, with the clean pinned authors' checkout at `D:/Project/AStarAlgorithm-authors-benchmark`, the original snapshot is already frozen. The first command below recreates it and should reproduce its manifest hash exactly; it does not modify the authors' checkout.

```powershell
python experiments\benchmarks\capture_robot_local_snapshots.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark
python experiments\benchmarks\time_robot_local_asp.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark
.venv\Scripts\python.exe experiments\benchmarks\run_robot_local_astar.py
python experiments\benchmarks\finish_robot_local_benchmark.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark
```

The first command rewrites the frozen snapshot file and should be omitted when using the committed snapshot as-is. The first and second commands require the upstream Python dependencies available in the system Python 3.14 installation; the third uses the repository's Python 3.12 virtual environment and existing compiled `backend/astar_core.cp312-win_amd64.pyd`. Repeated timing runs can vary with host load, but paths, eligibility, geometry statuses, and static metric definitions are deterministic. Existing road and gated robot benchmark files are not overwritten by these commands. Inspect source and map hashes in the manifest before interpreting any new run.

Validation on this branch: `python -m py_compile` on all benchmark scripts passed; `.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure` passed **4/4** C++ suites; `.venv\Scripts\python.exe -m pytest -q tests` passed **169** tests (one pre-existing Starlette/httpx deprecation warning); `npm run test` in `frontend` passed **34/34** tests. The [five focused adapter tests](../../../tests/test_robot_local_geometry.py) cover blocker rejection, sight accumulation, unknown gaps, and both frozen manifest hashes. The dedicated finish commands passed all input-equivalence and path-geometry assertions. No production algorithm, UI, prior benchmark output, or authors' tracked file changed.

## Scientific limits and report guidance

These six cases come from **two prespecified source episodes**, not a broad random sample or the paper's full benchmark. A separately frozen [held-out extension](../robot-local-extension/robot-local-comparison.md) tested four more original maps and preserved all **75** decisions. Only **one** had a nontrivial skeleton, and that decision closely resembled the initial bugtrap case. It adds little independent path-topology evidence; the 74 direct cases remain disclosed. Their original source motion semantics remain unsuitable for a direct end-to-end physical-distance comparison. Point-valid and strict-valid counts differ, and neither implies radius-0.5 clearance. The known free model is based on recorded source sights; a different sensing method would create different shared states. The source skeleton and our scan-center graph are different, so the path-length difference is a system-level local-planning difference, not a pure A* versus bundle-optimizer theorem.

**Suitable LaTeX claim:** “On six frozen nontrivial local decisions from two reproduced author-source episodes, both planned-path methods found point-center, obstacle-interior-free paths from identical endpoints using the same accumulated observed sights. The authors' ASP was shorter in five cases and our sparse scan-center visibility A* in one; three ASP routes touched obstacle boundaries. This is a small descriptive local-path comparison under an explicitly stated point-robot model.” Include the exact table, selection rule, and timing caveat. Do **not** claim online navigation superiority, global shortest paths in an unknown world, a finite-radius comparison, or reproduction of the paper's original numerical tables.
