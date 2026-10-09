# Final benchmark summary for the university report

**Scope:** one frozen directed-road A* versus Dijkstra experiment, one frozen shared-state *local planned-path* comparison of the original authors' ASP/DAP and our continuous visibility-graph C++ A*, and three internal online-navigation supporting studies. [The full report](FINAL-BENCHMARK-REPORT.md) is the source for methods, limitations, and figure captions. [The final manifest](benchmark-final-manifest.json) records hashes and source revisions. The 48-case end-to-end authors-versus-our-robot validity gate remains in force.

| Result | Verified value |
| --- | --- |
| Road frozen directed pairs | 180: 60 short, 60 medium, 60 long |
| Road optimal cost agreement | 180/180 |
| Road A* fewer expansions | 180/180; median paired reduction 76.0% |
| Road lower A* search time | 173/180; median paired A*/Dijkstra ratio 0.338 |
| Initial + prior held-out robot decisions | 118 captured, 7 bundle-eligible, 111 direct-path exclusions |
| One prospectively frozen extension | 10 source episodes; 233 decisions, 14 eligible, 219 direct-path exclusions; 9 goals reached, 1 iteration cap |
| Final robot local sample | 351 decisions, 21 eligible pairs across five original map files |
| Local path length | ASP shorter 9, A* shorter 10, equal 2; paired median A*−ASP 0.000 source units |
| Primary interior-only point validity | ASP 21/21; A* 21/21 |
| Strict no-boundary-contact point validity | ASP 15/21; A* 21/21 |
| Strictly valid paired subset | 15 cases: ASP shorter 3, A* shorter 10, equal 2 |
| Median component timings over 21 states | Python ASP core 62.655 ms; A* observed-link build 42.102 ms; C++ binding/search 0.0263 ms; different scope and language |
| Radar vs legacy | 20 goal-success pairs; radar shorter 18, longer 2; largest regression +70.772 world units |
| Frontier cache | 20/20 equivalent playback pairs; median frontier time 639.166 ms full / 46.723 ms cached |
| Sensor study | 12/12 goal reached; radius-5/7 median executed distance 92.909/113.278 world units |

**All 111 earlier exclusions explained:** 61 source-visible direct two-vertex paths and 50 direct two-vertex paths whose target is at the strict sensing-range boundary. The original source graph has a direct edge in the boundary cases. Zero eligibility-checker mismatches, missing inputs, invalid endpoints, or geometry incompatibilities were found. The new extension's 219 exclusions follow the same precommitted nontrivial-bundle rule. Selection never uses a planner's result.

**Scientific interpretation:** these 21 local decisions compare two planners with the same frozen observed sights and endpoints but different graph representations. They do not measure full unknown-environment navigation, physical trajectory execution, finite-radius safety, or a universal algorithm speedup. A shorter boundary-touching route cannot be called strictly feasible. The source's unreconciled waypoint-transition and robot-footprint semantics still block direct end-to-end numerical comparison.

**Reproducibility:** selection freeze `71c5204`; prospective snapshot freeze `4aac5ef`; original source `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`. The source replay `--verify-only` reproduced the exact 233-decision committed snapshot hash. Road and supporting validators passed. The prospective local geometry validator reported zero source/derived membership disagreements in 116,500 samples, zero uncovered samples of 98,703 accepted graph-link points, 518/518 ASP segments sight-certified, and zero offline interior or boundary crossings among 997 accepted A* links. [The complete paired CSV](robot-local-final-paired.csv), [eligibility CSV](robot-snapshot-eligibility-audit.csv), [summary JSON](benchmark-final-summary.json), [data dictionary](benchmark-data-dictionary.md), [14 figures](final-figures/), and [LaTeX tables](tables/) are the reproducible package.

**Regression commands actually run:**

```text
.venv/Scripts/ctest.exe --test-dir build-cpython --output-on-failure     4/4 passed
.venv/Scripts/python.exe -m pytest -q tests                           169 passed, 1 existing Starlette/httpx deprecation warning
cd frontend; npm run test                                              34/34 passed
cd frontend; npm run build                                             passed, 85 modules transformed
cd frontend; npm run lint                                              passed
.venv/Scripts/python.exe experiments/benchmarks/validate_road.py      passed, 180 equal costs, zero heuristic edge violations
.venv/Scripts/python.exe experiments/benchmarks/validate_supporting.py passed, all paired matrices validated
py -3.14 experiments/benchmarks/validate_final_selection.py           passed, 10 valid source-map/endpoints
py -3.14 experiments/benchmarks/capture_robot_local_final_extension.py --verify-only --authors-dir D:/Project/AStarAlgorithm-authors-benchmark  passed, exact 233 snapshots
py -3.14 experiments/benchmarks/validate_final_benchmark.py           passed (final consistency gate)
```

The first attempt to invoke bare `ctest` failed because it was not on PATH; the explicit virtual-environment executable ran and passed all four C++ suites. No production algorithm, original authors' checkout, original frozen benchmark input, Road Navigation behavior, or end-to-end validity gate was changed. No branch was merged into main.
