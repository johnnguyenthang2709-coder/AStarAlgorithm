# Prespecified held-out local-path extension

This extension is separate from the [initial six-pair comparison](../robot-local-benchmark/robot-local-comparison.md). The first [selection](../robot-local-benchmark/robot-local-extension-selection.json) was committed at `f36a2ee` before execution. It yielded zero bundle-eligible decisions. A second [selection](../robot-local-benchmark/robot-local-extension-selection-2.json) was then disclosed and committed at `954fcb6` **before its source runs**. Both batches, including every direct case, are retained in [snapshots](robot-local-snapshots.json). The combined input was frozen at `d689af4` before the local planners were timed. The [manifest](robot-local-benchmark-manifest.json) contains its SHA-256 and all episode outcomes.

| Prespecified source episode | Source decisions | Bundle-eligible decisions | Source goal status |
| --- | ---: | ---: | --- |
| `_map_block.csv`, `(0,0)` → `(100,100)` | 12 | 0 | Reached |
| `_map_forest.csv`, `(0,0)` → `(100,100)` | 10 | 0 | Reached |
| `_map_blocks.csv`, `(0,0)` → `(300,300)` | 29 | 0 | Reached |
| `_map_bugtrap_1.csv`, `(0,0)` → `(160,80)` | 24 | 1 | Reached |
| **Total** | **75** | **1** | **4/4 reached** |

The selection rule was the same as the initial study: every original skeleton path with more than two vertices. The other **74 decisions** are recorded with exclusion reason `excluded_direct_or_empty_skeleton` in the [geometry CSV](robot-local-geometry-validation.csv); they are not missing or failed planning attempts. Both unchanged methods completed the one eligible local pair, `_map_bugtrap_1-12`, with identical endpoints and frozen sight input. ASP length was **167.670886**, our C++ A* length **169.325094** world units. Both avoided obstacle interiors; ASP made **two boundary contacts** and fails the strict boundary-excluding convention, whereas A* made none. Minimum obstacle clearance was **0** and **0.3329**, respectively, so neither is validated for a radius-0.5 robot. ASP had **58** nonzero heading changes but only **five** above 15°; A* had **four** under both definitions. The A* graph had **14 nodes, 32 links, and nine expansions**.

The geometry check found **0 differences in 37,500** fixed-seed source-versus-derived sight-membership samples and **0 uncovered samples among 3,168** points on accepted A* links. All **151** original ASP segments in the four episodes were sight-certified. The **32** A* links had zero ground-truth obstacle-interior crossings and zero boundary contacts on offline review. Original ASP was recomputed exactly from the frozen sight records; the source checkout was not changed. The paired [results CSV](robot-local-asp-vs-astar.csv), [validation summary](robot-local-validation-summary.json), [timing samples](authors-asp-timing.json), and [A* plan](astar-plans.json) retain the full evidence.

Median of 31 warmed calls for the one pair: authors' Python ASP core **563.698 ms**; our observed-link build **48.663 ms**; C++ A* binding call **0.0263 ms**. The [timing-distribution table](robot-local-timing-distributions.csv) and [figure](robot-local-timing-distributions.png) show quartiles and spread. Different languages, graph representations, and timing scope prohibit an algorithm-only speedup claim. [Paired length](robot-local-paired-lengths.png), [turn](robot-local-paired-turns.png), and [timing](robot-local-paired-timing.png) plots include this only eligible case. [Observed-space trajectory](bugtrap_1-12-observed.png) excludes hidden polygons; the [ground-truth view](bugtrap_1-12-ground-truth-validation.png) is offline validation only.

The eligible `_map_bugtrap_1-12` endpoints and skeleton match the initial `_map_bugtrap-12` pair, and its path-length results are nearly identical. The maps and full sight records differ, but this one pair adds **little independent topology diversity**. The extension should be reported as a prespecified coverage/eligibility check, not counted as independent evidence that one planner generally produces shorter routes. The initial six-pair inference remains descriptive.

Reproduce from the repository root with the pinned clean authors' checkout. The first command recreates the deterministic frozen input; omit it to use the committed snapshot unchanged.

```powershell
python experiments\benchmarks\capture_robot_local_extension.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark
python experiments\benchmarks\time_robot_local_asp.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark --dataset-dir experiments\benchmarks\robot-local-extension
.venv\Scripts\python.exe experiments\benchmarks\run_robot_local_astar.py --dataset-dir experiments\benchmarks\robot-local-extension
python experiments\benchmarks\finish_robot_local_benchmark.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark --dataset-dir experiments\benchmarks\robot-local-extension
```
