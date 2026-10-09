# Academic benchmark: reproducible evidence and validity boundary

## Research questions and outcome

1. **Road search:** On the same directed weighted graph, does the existing C++ A* preserve Dijkstra's optimal route cost while changing search effort? **Yes for all 180 frozen queries.** A* had fewer valid expansions on every pair and a lower measured median search time on 173 pairs. This is evidence about this implementation, graph, sample, and machine, not universal algorithm superiority.
2. **Continuous robot navigation:** Can the original authors' proposed bundle/ASP system and our continuous C++ A* system be compared fairly on identical polygon worlds? **Not under the source's executed-motion collision semantics.** Two representative upstream source runs reached their goals but their coordinate-update segments crossed obstacle interiors. The planned ASP polyline was logged rather than executed by the navigation loop. Accordingly, the 48 matched configurations (96 method slots) are frozen but **not run as a primary comparison**. No robot distance, turn, success, or runtime superiority is claimed.
3. **Supporting sensitivity:** How do radar ranking, frontier caching, and sensing radius affect our own controller on fixed configurations? These are internal paired/descriptive studies, not comparisons to the paper's method.

## Provenance and paper-to-source mapping

| Component | Pinned evidence | Meaning |
| --- | --- | --- |
| Our project baseline | `cb69fc65fb81f6cffdd3e0556f4dccd5892bdcdf` | Production algorithms and previously validated application before this research branch. No production algorithm was changed. |
| Academic protocol | `f0e8a85` and supporting addendum `d682d8d` | Road and robot selections fixed before broad execution; supporting cases fixed before supporting runs. The addendum did not change road pairs or robot configurations. |
| Authors' upstream | `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8` from [autonomousRobot](https://github.com/ThanhBinhTran/autonomousRobot) | Isolated checkout at `D:/Project/AStarAlgorithm-authors-benchmark`; no source patch or copied map. No license/COPYING file or dependency lock found at this commit. |
| Paper | [DOI 10.1016/j.robot.2025.105185](https://doi.org/10.1016/j.robot.2025.105185), Sections 6.1–6.2 | Section 6.2.1 compares **local explored-space paths** (improved ASP, separate grid A*, RRT*). Section 6.2.2 compares **end-to-end** navigation against RRTX. Neither is an authors' bundle-versus-our-C++ experiment. |

The authors' `Graph.BFS_skeleton_path` orders a priority queue by accumulated Euclidean edge cost, a Dijkstra-style skeleton search. Geometric critical-line/bundle processing then produces the approximate shortest path (ASP). Their separate `a_star.py` is the grid A* baseline in the paper's local-path experiment. `Robot_run.py` computes `robot.asp`, appends it to `visited_paths`/`robot.cost`, and assigns `robot.next_coordinate` from `robot.next_point`. Our read-only wrapper observes actual `Robot.update_coordinate` calls, so planned ASP distance and executed coordinate distance remain distinct.

The upstream source reproduction is **not an exact paper-table reproduction**. The code has no pinned dependency environment, the original hardware and some reported table settings are unavailable, and the wrapper uses two explicit representative map/start/goal cases. Its outcomes should not be compared numerically with published tables as though protocol and collision model matched.

## Experimental setup and metric definitions

Full selection rules, source/map hashes, goal coordinates, timing batches, fixed budgets, and exclusion policy are in [benchmark-protocol.md](benchmark-protocol.md) and [benchmark-manifest.json](benchmark-manifest.json). The road graph has 2,986 nodes and 7,152 directed edges with meter weights. A fixed Python seed generated 6,000 distinct, nonidentity directed candidates; Dijkstra found 5,965 reachable. Reachable sampled Dijkstra cost order statistics at one-third and two-thirds (2,086.9774 m; 3,273.4354 m) defined the short/medium/long strata. The first 60 sampled candidates per stratum formed **180 distinct, reachable, directed node pairs**. These are sample-frame quantiles, not exhaustive all-pairs quantiles.

Road methods share the exact graph, directed neighbors, weights, endpoints, C++ search core, and `trace=false` setting. The primary matrix uses nodes, so it does not invoke snapping. A separate midpoint query checks that nearest-edge augmentation is shared by A* and Dijkstra. Search time is C++ `std::chrono::steady_clock` time **inside search only**, excluding graph load, Python binding, API serialization, and rendering. Each method/pair had one untimed warm-up, then seven alternating-order batches; short/medium/long batches used 20/10/5 repeated calls, respectively. The reported per-pair time is the median batch time per call. Valid expansions exclude stale OPEN entries; `generated_nodes` counts OPEN pushes and `unique_discovered` is a logical state count. Exact queue-pop count and allocated/peak bytes are not exposed by the unchanged core, so neither is invented. Logical counts are **not byte-accurate search memory**.

The road binary was compiled in C++17 **Release** with MSYS2 UCRT64 `g++` on Windows 11, Intel Core 7 240H (16 logical processors), 16,866,033,664 bytes RAM. No CPU pinning or scheduler isolation was used. Timing ratios are machine- and implementation-specific.

The authors' smoke source used Windows Python 3.14.2, NumPy 2.4.3, Matplotlib 3.10.8, pandas 3.0.1, OpenCV 5.0.0, and Shapely 2.1.2. Original polygons are x/y world coordinates; no pixel-to-world remapping was made. The diagnostic checks polygon validity, center-line obstacle-interior intersection, and 0.5-unit radius clearance. The latter is stricter than point-robot collision and is reported separately. A valid shared comparison would additionally need equal sensing, footprint, stopping, and world-scale rules; the executed-motion blocker is already sufficient to stop this matrix.

For our robot supporting runs, `executed_distance` sums actual continuous movement lengths. `turn_count` increments when consecutive nonzero movement headings differ by more than 1e-6 radians (wrapped angular difference); it is not asserted equivalent to the authors' collinearity count or the separate >15° diagnostic count. A* calls are `replanning_count`; planning time is measured within the controller. Sensor `decisions` count calls to `ContinuousPolicy.select`, and `observations` count calls to `world.sense`, including observations on locked retreats. Wall time includes Python sensing, ranking, graph construction, search, and in-memory frame construction. The supporting cases retain unsuccessful/step-limit outcomes. An initial concurrent ablation/cache run was replaced by **sequential standalone reruns** for the retained CSVs. The cache harness compares its two variants serially within each pair, and exact playback equivalence is the primary result. These wall times remain descriptive because Windows scheduling and Python/geometry-library behavior were not isolated.

## Experiment I: road A* versus Dijkstra

| Stratum | Pairs | Median optimal cost (m) | Median expanded A* / Dijkstra | Median search time A* / Dijkstra (µs) | A* fewer expansions | A* faster |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Short | 60 | 1,420.37 | 101 / 505 | 44.95 / 128.09 | 60 | 58 |
| Medium | 60 | 2,743.00 | 301 / 1,592 | 282.95 / 1,117.24 | 60 | 60 |
| Long | 60 | 4,279.97 | 714.5 / 2,588.5 | 771.46 / 1,883.19 | 60 | 55 |
| All pairs | 180 | — | 303.5 / 1,558 | 268.90 / 1,069.46 | 180 | 173 |

All 180 pairs were reachable and had **exactly equal recorded A*/Dijkstra costs** (maximum absolute CSV difference 0 m; validation threshold 1e-6 m). Search effort is paired at the query level; the table medians are marginal medians, so dividing them is not a paired speedup estimate. [Raw paired rows](road-astar-dijkstra.csv), [validation details](road-validation.json), [expanded-node figure](figures/road-expanded.png), [runtime figure](figures/road-time.png), [cost-agreement figure](figures/road-cost-agreement.png).

The loaded graph's heuristic scale was 1.0 and all 7,152 directed edges passed `scale × Haversine(u,v) ≤ weight(u,v) + 1e-6 m`. Because Haversine distance obeys the triangle inequality, this edge inequality gives a consistent, hence admissible, goal heuristic for the road cost objective. Start=goal returned zero; the frozen one-way directed edge routed in its allowed direction; the unreachable pair remained unreachable for both methods; the nearest-edge midpoint query returned equal costs. [Edge-case results](road-edge-cases.csv). These checks support correctness for this graph and implementation, not every possible road dataset.

## Experiment II: original-source reproduction and comparison gate

| Original source map and fixed run | Source goal status | Executed distance | Logged planned ASP distance | Turns: collinearity / heading >15° | Executed interior crossings | 0.5-clearance violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `_map_deadend.csv`, (0,0)→(70,90), radius 20 | Goal reached | 456.37 | 551.03 | 19 / 18 | 4 | 6 |
| `_map_bugtrap.csv`, (0,0)→(160,80), radius 20 | Goal reached | 543.77 | 566.03 | 20 / 15 | 1 | 3 |

Both runs used robot radius 0.5, Open_Arcs ranking, neighbor-first selection, and a 60-iteration cap. Source-map hashes, actual coordinate sequences, planned ASP records, collision-segment indices, and timing are retained in [author-reproduction.csv](author-reproduction.csv) and [raw diagnostic JSON](author-reproduction-raw.json). [Diagnostic figure](figures/author-validity-diagnostic.png) displays scalar source measurements only; it does **not** depict a shared-map comparative trajectory.

**Validity decision:** The authors' executed center-to-center movement is not collision-feasible even for a point robot in these cases. Their logged ASP distance is not the distance executed by `Robot.update_coordinate`. Altering the authors' movement to follow ASP, or silently repairing collisions, would change the method under test. Running our collision-checked continuous controller against those invalid trajectories would conflate collision semantics with algorithm quality. We therefore did **not** execute either method on the frozen 48-case primary matrix. [All 96 blocked method slots](robot-authors-vs-astar.csv) are explicitly marked `not_run_validity_gate`, with blank outcome metrics. This is **not** 96 failures or timeouts; it is 96 unexecuted slots. The two source smokes are separate diagnostics, not sampled primary episodes.

The same information-state and endpoint equivalence needed for a local ASP-versus-visibility-A* path study was not established. `robot-local-paths.csv` and the requested authors/our trajectory, travel, turn, and success comparison figures are omitted rather than filled with invalid or synthetic results. No claim about relative robot-system performance is justified. The source-code reproduction also cannot establish the paper's published feasible-path counts or runtimes under its original setup.

## Supporting experiments

The paired ablation, frontier-cache validation, and sensor matrix below are independent of the blocked authors/our comparison. Their raw data are [exploration-ablation.csv](exploration-ablation.csv), [frontier-cache.csv](frontier-cache.csv), and [sensor-robustness.csv](sensor-robustness.csv). The ablation includes the previously unfavorable Complex Irregular Labyrinth radius-7 case and all held-out seeds; no outcome was dropped. Cache runs require frame, recovery, terminal-status, and executed-distance equality for each paired case. A representative earlier indoor hierarchy trace supplies observed branch IDs, A*-planned return lengths, fallback flags, and executed return bounds; its [figure](figures/parent-return.png) is a **metric plot**, not a discovered-space or ground-truth trajectory drawing.

| Supporting matrix | Complete result | Interpretation |
| --- | --- | --- |
| Legacy versus radar exploration | 20 paired configurations, 40 episodes; **40/40 goal reached**. Radar traveled less on 18 pairs and more on 2; median paired radar-minus-legacy distance **−95.42 world units**. | Ranking changes navigation order, not just execution speed. In Complex Irregular Labyrinth radius 7, radar traveled **167.82** versus legacy **97.04** (+70.77); held-out seed 911 radius 7 also regressed by 5.75. No universal distance improvement is claimed. |
| Full versus cached frontier | 20 paired configurations, 40 episodes; **20/20 exact eligible-candidate, playback, recovery, status, and distance matches**. Median per-episode frontier construction time 639.17 ms full versus 46.72 ms cached; cached time lower in all 20. | The optimization preserved measured decisions and trajectories in this matrix. Timings include load variation and should not be interpreted as a hardware-independent speedup. Median final cached wall-mask WKB size was 47,673 bytes, a partial storage proxy rather than process-memory measurement. |
| Sensor radius 5 versus 7 | 6 prespecified worlds × 2 radii = **12 episodes, 12 goal reached**. Median executed distances are 92.91 and 113.28 world units, respectively. | Different radius can change target order; the medians mix three labyrinth and three indoor worlds and do not imply radius 7 is generally worse. Each paired case, status, turn count, A* calls, expansions, sensing time, and return count is in the raw CSV. |

The ablation and cache CSVs are retained **standalone reruns** after earlier overlapping runs were discarded. The ablation's median wall times were 1,808.63 ms legacy and 1,202.02 ms radar, but this mixes different paths and numbers of decisions, so it cannot isolate ranking overhead or prove an algorithm-level runtime advantage. The cache's two variants were run sequentially for each case; eligible candidate lists were captured at every `available` call and compared exactly. Even there, wall times depend on host load, so the strongest evidence is 20 exact behavioral matches and consistently lower frontier construction times. The sensor matrix was rerun in full after an interrupted run distorted one wall-time sample; the complete final CSV is the retained result. The aggregate checks are machine-readable in [supporting-validation.json](supporting-validation.json). [Sensor-radius figure](figures/sensor-robustness.png) and [frontier-cache figure](figures/frontier-cache.png) are report-ready data plots. Neither depicts a map or hidden geometry. The [parent-return metric plot](figures/parent-return.png) derives from the previously committed indoor trace; it does not assert a new trajectory or source-map comparison.

## Threats, interpretation, and reproducibility

- The road sample comprises 180 deterministic pairs from one Ho Chi Minh City OSM-derived graph. It is not a random sample of all world road networks or all node pairs. The objective is edge distance, with no traffic or turn restrictions.
- The edge-cost check establishes Haversine consistency on the loaded graph. Nearest-edge virtual-node correctness remains separately covered by existing regression tests; the primary 180-pair matrix is node-to-node.
- `median_search_us` is a batch median, not full API latency. The shortest calls are particularly sensitive to timer and scheduler noise; one warm-up and batching reduce but cannot remove that variability. No inference about equal paths is made from equal costs; multiple optimal paths can exist.
- The authors' code has no locked dependency manifest or license declaration at the pinned commit. The wrapper depends on current libraries and reports source behavior only. Their source's logged planned ASP route and executed motion have different meanings. The original paper's full experimental table was not reproduced.
- Internal online robot distances are not full-map shortest-path lengths. Sensing radius changes information availability and exploration order; a larger radius need not monotonically reduce travel. Recovery certification applies to specific measured entry/return events, not globally optimal exploration.
- We do not attach confidence intervals to the deterministic, intentionally stratified road matrix or small fixed supporting matrices. They are complete descriptive results for the frozen cases. Broad population claims would require a separately defined sampling population and replication protocol.

### Reproduction commands (PowerShell, repository root)

```powershell
# Environment: existing .venv and CMake Release build configured as in README.
.venv\Scripts\python.exe experiments\benchmarks\prepare_manifest.py D:\Project\AStarAlgorithm-authors-benchmark
.venv\Scripts\cmake.exe --build build-cpython --target academic_road_benchmark --parallel 4
build-cpython\academic_road_benchmark.exe data\road\graph.json experiments\benchmarks\benchmark-manifest.json experiments\benchmarks\road-astar-dijkstra.csv
.venv\Scripts\python.exe experiments\benchmarks\validate_road.py
python experiments\benchmarks\run_author_reproduction.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark
.venv\Scripts\python.exe experiments\benchmarks\write_gated_matrix.py
.venv\Scripts\python.exe scripts\audit_bar_radar_benchmark.py --output experiments\benchmarks\exploration-ablation.csv
.venv\Scripts\python.exe scripts\benchmark_bar_frontier_cache.py --output experiments\benchmarks\frontier-cache.csv
.venv\Scripts\python.exe experiments\benchmarks\sensor_robustness.py
.venv\Scripts\python.exe experiments\benchmarks\validate_supporting.py
python experiments\benchmarks\make_figures.py
```

The source clone is separate from this repository, and the scripts do not delete it. Re-running a timing experiment overwrites its CSV, so preserve committed artifacts for exact audit. The source smoke depends on the upstream CSV maps at the pinned commit. A different current GitHub revision or package stack is a different reproduction environment.

### Regression commands and observed outcomes

| Command | Observed result |
| --- | --- |
| `.venv\Scripts\cmake.exe --build build-cpython --parallel 4` | Exit 0; Release build up to date. The `academic_road_benchmark` target was compiled before the full road run. |
| `.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure` | **4/4 C++ suites passed**: core, road, reference, edge_snap. |
| `.venv\Scripts\python.exe -m pytest -q tests` | **164 passed**, one Starlette/httpx TestClient deprecation warning, exit 0 (261.86 s). |
| `npm run test` in `frontend` | **34/34 tests**, 8 files, exit 0. |
| `npm run build` in `frontend` | TypeScript and Vite production build passed, exit 0. |
| `npm run lint` in `frontend` | `oxlint` passed, exit 0. |
| `.venv\Scripts\python.exe experiments\benchmarks\validate_road.py` | 180 paired costs and 7,152 heuristic inequalities verified; edge cases passed, exit 0. |
| `.venv\Scripts\python.exe experiments\benchmarks\validate_supporting.py` | 20 ablation pairs, 20 cache pairs with exact playback equivalence, 12 sensor episodes verified, exit 0. |

No Road Navigation, Robot Lab controller, generic C++ A* core, or original author checkout files were modified for this benchmark. This branch is an unmerged, report-ready road and internal-sensitivity baseline. It is **not** a valid numerical authors-versus-our-robot result for a LaTeX comparison table; that portion is blocked as explained above.
