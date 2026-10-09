# Independent audit: authors' motion semantics and collision validity

**Scope:** read-only reproduction and diagnosis. Branch `codex/author-motion-validity-audit` starts from academic baseline `da96440aa16c27a719b2827931e47ec48444a2bb`. No production navigation code, prior benchmark artifact, or original authors' tracked file was changed. The 48-configuration comparison remains unexecuted.

## Executive finding

**Primary classification: B — execution-semantics mismatch (high confidence).** The [paper](https://doi.org/10.1016/j.robot.2025.105185), Algorithm 2, says to move from the current coordinate to the selected point **along DAP** and append DAP to the traveled path. In the pinned source, the robot computes an ASP/DAP-like polyline, appends it to `visited_paths` and `cost`, then sets the next state to the selected waypoint itself. At the next loop iteration, `Robot.update_coordinate` only assigns that coordinate. No code traverses the ASP vertices, interpolates motion, or checks the transition segment for collision. This is established by `Robot_run.py:90–150`, `Robot_class.py:77–96`, and `Robot_paths_lib.py:7–13`. The source therefore exposes **discrete coordinate transitions**, not a physical trajectory between them.

The old benchmark's straight segment between successive coordinates is an **explicit linear-interpolation assumption**. Under that assumption, the four reported dead-end transitions and one bugtrap transition genuinely cross obstacle interiors. An independent even/odd polygon calculation agrees with Shapely's DE-9IM interior predicate; the authors' own `Obstacles.check_linesegment_collision`, if called, returns true for every crossing. The bugtrap transition crosses **two** polygons, yielding two collision records for one transition. These are not boundary touches or sub-tolerance numerical artifacts. Confidence in the conditional geometric diagnosis is high. **The source does not prove that a physical robot actually drove those straight segments**, so the older wording “executed travel distance” should be read as the length of linear links between recorded states, not observed continuous odometry.

**Secondary footprint issue:** all 196 computed ASP line segments avoid polygon *interiors*, but 11 segments touch polygon boundaries (9 dead-end, 2 bugtrap), and 22 segment–polygon records violate 0.5-unit clearance (17 and 5). The dead-end goal `(70,90)` is only **0.3162** units from an obstacle, so a disk robot of radius 0.5 cannot even occupy that goal center without overlap. The source checks start/goal centers, not radius clearance; the configuration-space call is commented out (`Robot_run.py:45`, `Obstacles.py:102–109`). Thus these ASPs are **not validated radius-0.5 robot trajectories**, even though they avoid obstacle interiors as centerline polylines. This does not prove the paper's geometric algorithm invalid under its own assumptions.

**Gate decision:** retain the existing blocked 48-case end-to-end comparison. The blocker is better stated as *unestablished compatible continuous-motion and footprint semantics*, with demonstrated invalid straight-line transitions. It is not evidence that the published DAP theorem is wrong, nor evidence that a paper-aligned DAP-following simulator cannot be built.

## Exact source, paper, environment, and artifact provenance

| Item | Verified value |
| --- | --- |
| Our academic baseline | `da96440aa16c27a719b2827931e47ec48444a2bb`; initial working tree clean. Existing report, protocol, manifest, source-reproduction CSV/raw JSON, gated matrix, and figures read before analysis. |
| Authors' source | `D:/Project/AStarAlgorithm-authors-benchmark`, remote `https://github.com/ThanhBinhTran/autonomousRobot.git`, clean tracked tree at `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`. No source edits; temporary Python method wrappers are restored before return. |
| PDF | `D:/Downloads/2025-AnHAnhBinhHoai-Sequence-BlindAlleyRobotNavigation-RAS.pdf`, SHA-256 `8B9C99BABEDF9F2ADDC329C8BC26A1CA27448BDB6170139DED5607621F9C6B6B`. Sections 3, 4.5, 4.6, Algorithms 1–2, and 6.1–6.2 inspected. |
| System | Windows 11 Home build 26200; Python 3.14.2, NumPy 2.4.3, Matplotlib 3.10.8, pandas 3.0.1, OpenCV 5.0.0, Shapely 2.1.2. No upstream dependency lock is present. |
| Dead-end map | `_map_deadend.csv`, SHA-256 `7cd52d0bb87e1acfb649ee71f28fce8bd68e231bbda9be98b3fc1ac2185066ab`; one valid 339-vertex polygon; CSV rows 2–340. Start `(0,0)`, goal `(70,90)`. |
| Bugtrap map | `_map_bugtrap.csv`, SHA-256 `50d59ed7ff96cbd7e6c45912691c59bd2568f9e4e00a018a492ed1b005799cf8`; two valid polygons of 196 and 366 vertices; CSV rows 2–197 and 199–564. Start `(0,0)`, goal `(160,80)`. |
| Both source runs | Vision radius 20, robot radius 0.5, `Open_Arcs`, `neighbor_first`, `experiment=True`, `save_image=False`, `save_log=False`, iteration cap 60. `Robot_run.robot_main` returns after `robot.finish()` (goal within robot radius or `no_way_to_goal`) or iteration cap (`Robot_run.py:161–181`, `Robot_class.py:209–231`). Both ended `reach_goal=True`, `no_way_to_goal=False`, before cap. |

The audit's replay uses the same source entrypoint and exact parameters. The old [raw reproduction](author-reproduction-raw.json) and [summary CSV](author-reproduction.csv) were **read, never overwritten**. Every newly captured coordinate and every ASP vertex matched the old raw record exactly (`maximum_replay_position_delta=0`, `maximum_replay_asp_vertex_delta=0`), including all source transition indices. The 48×2 [blocked matrix](robot-authors-vs-astar.csv) remains untouched. The initial benchmark's geometry checker at `run_author_reproduction.py:29–46, 79–88` groups `x,y` CSV sections into polygons, checks `line.relate_pattern(poly,"T********")` for interior–interior intersection, and checks `<0.5−1e−7` for radius clearance. Its source `Robot.update_coordinate` hook records each new discrete coordinate (`run_author_reproduction.py:53–79`). The new audit deliberately uses an independently written CSV parser plus the authors' parser for coordinate-by-coordinate comparison.

## Paper-to-source control flow and trajectory meanings

| Stage | Paper's intended semantics | Pinned source semantics |
| --- | --- | --- |
| Local sensing | At current position, observe limited range and accumulate explored sight (Section 4.1, Section 4.6). | `Robot_run.py:98–114` calls `scan_around`; `Robot_sight_lib.py:745–756` reads original obstacle polygons or configuration-space obstacles if enabled. The latter is disabled here. `Sight.py:12–15` stores observations by center. |
| Target selection | Select ranked active open point `n` (Section 4.6, Algorithm 2). | `Robot_class.py:364–394` selects local or global ranked point; `Robot_run.py:116–117` assigns `next_point`. It is a selected navigation target, despite the initialization comment saying “for display only.” |
| Skeleton graph | Build a path in accumulated observed graph (Section 4.5–4.6). | `Robot_run.py:113–127` inserts local open points and calls `Graph.BFS_skeleton_path` except when target is goal. `Graph.py:16–25` adds bidirectional edges; `:38–54` uses cumulative Euclidean cost in a priority queue (Dijkstra-style search). |
| ASP/DAP | Algorithm 1 constructs a path joining current point and selected target; Algorithm 2 says “Make a move ... along DAP” (PDF printed pp. 4 and 7). | `Robot_paths_lib.py:29–43` converts skeleton to ASP where needed; `Robot_run.py:135–145` computes, totals, and appends that path. Every audited ASP begins at current coordinate and ends at selected `next_point`. |
| Movement | Selected target reached by following DAP; Algorithm 2 adds DAP to `P` (Section 4.6, Algorithm 2 lines after DAP call). | `Robot_run.py:147–150` assigns `next_coordinate = tuple(next_point)`; `:90–92` applies it next iteration; `Robot_class.py:77–78` merely assigns `coordinate`. `Robot_paths_lib.motion` also only returns the target (`:7–13`) and its call is commented out. No ASP vertex-by-vertex motion or segment collision check occurs. |
| Logging and display | “Traveled path” should represent path actually followed if Algorithm 2 semantics hold. | `Robot_class.py:86–96` appends ASP to `visited_paths` and accumulates **ASP path cost**. `Plotter.py:134–142` and `Plot_base_lib.py:72–82` draw these planned/logged polylines. They can look like a physically traveled trajectory although the state updated only to its terminal waypoint. There is no singular `robot.visited_path` field in this source; the real field is `visited_paths` plus `visited_path_directions`. |
| Termination | Reach goal or exhaust viable points. | `Robot_class.py:209–231` declares reach if center-to-goal distance is ≤`radius`; `Robot_run.py:161–163` also respects cap. It does not check the intervening transition for collision. |

`robot.coordinate` is the sampled simulator state. `robot.next_coordinate` is the next state assigned at loop entry. `robot.next_point` is the ranked target. `robot.skeleton_path` is a graph path from state to target. `robot.asp` is the geometric planned polyline. `robot.visited_paths` and `robot.cost` contain ASP-based logs, **not verified physically executed motion**. The source's `path_look_ahead_to_goal` is a separate initialized field and does not repair this gap (`Robot_class.py:30–58`). `Plotter` is visualization, not a motion integrator.

The experiment-specific `Robot_run_experiment_OUR_ASTAR_RRT_backward.py:252–349` repeats the direct `next_coordinate = tuple(next_point)` transition. It compares local ASP, a separate grid A* baseline, and RRT* only when `len(skeleton_path)>2` (`:304–341`); it then logs ASP path length/turns/time. On Windows, `enable_improve=False` (`:27–33`) and this experiment file calls `approximately_shortest_path_old` (`:304–307`); on Linux graph bridging is conditionally enabled (`:282–284`). Our two smoke runs used **`Robot_run.py`**, which calls `approximately_shortest_path`, so they are a faithful reproduction of that entrypoint, **not an exact reproduction of the paper's Section 6.2.1 experiment script or its reported tables**. Paper Section 6.1 distinguishes local path comparisons from end-to-end RRTX comparisons; no results here are substituted across those protocols.

## Independent geometric collision results

For every map, the audit parser's vertex sequence matched `Obstacles.read_csv` exactly (`Obstacles.py:54–85`). Shapely says all polygons are valid. The x/y ordering, closure, and obstacle group boundaries match the source; no raster inversion, scaling, buffer, or polygon repair was applied. The original source's `check_linesegment_collision` (`Obstacles.py:128–134`) returns **true** for each reported transition when called by the audit, but neither audited navigation loop calls it. Shapely's DE-9IM interior–interior relation and a separate even/odd ray-cast procedure with analytic segment–boundary splits agree. The independent positive interior lengths below are far above the 1e−8 analysis threshold. Boundary crossings and the original CSV edge-row coordinates are in [collision-details.json](author-motion-audit/collision-details.json).

| Map; collision ID | Source move / iteration | State transition `(x,y)` | Polygon | Independent interior length | Matching planned ASP |
| --- | --- | --- | ---: | ---: | --- |
| Dead-end C1 | Move 3, iteration 4→5 | `(26.158,38.432)` → `(19.636,−3.800)` | 1 | 22.936 | 25 vertices; 0 interior crossings |
| Dead-end C2 | Move 5, iteration 6→7 | `(29.781,13.435)` → `(−14.968,34.025)` | 1 | 13.598 | 22 vertices; 0 interior crossings |
| Dead-end C3 | Move 10, iteration 11→12 | `(40.519,43.860)` → `(14.679,46.570)` | 1 | 13.650 | 20 vertices; 0 interior crossings |
| Dead-end C4 | Move 11, iteration 12→13 | `(14.679,46.570)` → `(4.957,35.762)` | 1 | 8.230 | 13 vertices; 0 interior crossings |
| Bugtrap C1/C2 | **One** move 12, iteration 13→14 | `(153.868,116.768)` → `(74.814,−5.276)` | 1 and 2 | 25.954; 18.944 | 78 vertices; 0 interior crossings |

The exact endpoints, DE-9IM strings, each polygon's original CSV row range, the crossed edge coordinates/rows, and whether the source boundary-collision method would detect them are recorded per polygon in the JSON. The table deliberately counts **five transitions**, not six, because bugtrap move 12 intersects both polygons. The old baseline's 4/1 counts are therefore reproduced under its interpretation. All five transitions had skeleton paths of 4–11 vertices (`decision-trace.csv`), so they were the **remote-target cases** for which the source had computed ASP; they were not the paper's immediate-neighbor straight-move case.

## Planned ASP validity and discovered information

| Case | ASP paths / line segments | Segment interiors entering obstacles | Boundary-touch segments | Segments with <0.5 clearance | ASP interior sample coverage | Goal clearance |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Dead-end | 21 / 98 | 0 | 9 | 17 | 294/294 covered | 0.3162 |
| Bugtrap | 22 / 98 | 0 | 2 | 5 | 294/294 covered | 1.4142 |

The ASP paths are continuous vertex chains with no start/target mismatches, and their segment interiors avoid polygon interiors. Some paths touch obstacle boundaries; whether boundary contact is allowed for an ideal point robot depends on the collision convention. They are **not clearance-valid for a radius-0.5 disk**. `find_configuration_space(robot.radius)` is commented out in the audited runners. The dead-end goal itself fails 0.5 clearance, while both source goals pass the source's center-only validity check (`Obstacles.py:102–109`). These findings are independent of the earlier waypoint-jump crossing and prevent treating a simple “follow ASP” substitution as already valid for the recorded disk footprint.

For the explored-space question, the audit sampled each planned ASP segment at 25%, 50%, and 75% of its length at its **decision time**, before later observations. All 294 interior samples per case were inside the source's accumulated `inside_visited_sights` predicate (`Robot_sight_lib.py:416–439`) and independently had line of sight from at least one recorded prior sensor station within range 20 against the ground-truth polygons. This is strong sampled evidence for the planned centerlines lying in currently explored free space. It is **not a formal continuous containment proof**; the source stores sights rather than one certified explored-free polygon, and interval sampling can miss tiny gaps. The audit did not expose hidden geometry to either planner; ground truth was used only after the run for validation.

The old summary's “executed distance” 456.37/543.77 is the sum of distances between consecutive `update_coordinate` states. The ASP sums are 551.03/566.03 and equal `robot.cost`. Neither number proves the physical path length of an unmodeled continuous motion. A larger ASP sum alone would not prove a defect; here the code-level assignment and geometry provide the decisive evidence.

## Hypothesis assessment and limits

| Hypothesis | Verdict and evidence |
| --- | --- |
| A. Paper/source motion semantics differ | **Supported.** Algorithm 2 explicitly says to move along DAP; source jumps to `next_point` (`Robot_run.py:147–150`), and `Robot.update_coordinate` only assigns (`Robot_class.py:77–78`). |
| B. Intermediate motion is handled elsewhere | **Rejected for these entrypoints.** No movement integration occurs between the assignment and next scan; `motion` helper is unused and returns the destination unchanged. Plotting draws stored ASPs, not state updates. |
| C. Wrapper wrongly parsed coordinates or polygons | **Rejected for the conditional straight-line geometry.** Replay matches all old vertices exactly; audit CSV parser matches the authors' parser; DE-9IM, pure ray-cast, and source collision checker agree. |
| D. Source guarantees physically straight transitions | **Not established.** It stores jumps with no continuous dynamics; drawing a chord is an analysis convention. We cannot claim the robot physically cut through walls in reality. |
| E. Planned ASP itself enters obstacle interiors | **Rejected in these runs.** Zero interior-crossing ASP segments; 294/294 sampled interior points per map are observed-free by two checks. Boundary contacts and radius violations remain. |
| F. Radius-0.5 ASP is collision-safe | **Rejected in these runs.** 17 and 5 segment–polygon clearance violations; dead-end goal center has only 0.3162 clearance. |
| G. The source image/log is the executed trajectory | **Rejected.** `visited_paths` and `robot.cost` store ASP (`Robot_class.py:86–96`), and Plotter draws them; coordinate transitions are separate. |

## Benchmark validity gate and comparison options

| Rank | Option | Scientific validity and fidelity | Needed work, risk, and remaining incompatibility |
| ---: | --- | --- | --- |
| 1 | **Original-source reproduction, clearly diagnostic** | Faithful to pinned `Robot_run.py` state/log behavior. Can report selected states, ASP plans, their geometry, and source termination. | No source changes. Do **not** label inter-state chords as observed physical travel or compare them with collision-checked online trajectories. Paper-table reproduction still differs by runner, platform flags, dependencies, and full protocol. |
| 2 | **Frozen discovered-state local path study** | Most defensible next comparative experiment if the same accumulated source sights, start, target, obstacle knowledge, and robot-footprint rule can be supplied to both planners. It tests *planned* paths, matching paper Section 6.2.1 better than an invalid end-to-end comparison. | Extract immutable decision snapshots, keep each algorithm unchanged, audit endpoint/path feasibility and representation differences, label different planning graphs. Moderate effort; conversion of source sights to our visibility graph must not add hidden geometry or accidentally favor either method. |
| 3 | **Separately labeled paper-aligned execution adapter** | Potentially closer to Algorithm 2, but **adapted implementation**, not exact source reproduction. It could execute each computed ASP segment before rescanning at the target. | Must define collision and footprint model, handle ASP boundary contacts/clearance, decide whether sensing occurs along traversed DAP or only at targets, check path availability at each step, and reproduce stopping/turn metrics. The dead-end `(70,90)` case cannot use a radius-0.5 disk without changing goal/footprint assumptions. High effort and high risk of changing exploration decisions or giving one system extra information. |
| 4 | **Direct end-to-end comparison using current source jumps as travel** | **Invalid for a shared collision-checked physical path metric.** | The source has no continuous trajectory; straight interpolation crosses obstacles. The earlier 48 configurations stay blocked. |

**Recommendation:** retain the gate and correct the *interpretation* in future reporting: “sampled source states and hypothetical straight links” versus “planned ASP polylines.” If a further experiment is approved, first attempt a **shared-state local planned-path comparison** with an explicit common point/footprint convention. Consider a paper-aligned DAP execution adapter only as a separately labeled subsequent study after the clearance and sensing rules are settled. Do not silently reclassify the existing 96 unexecuted method slots as failures or successful comparisons.

## Diagnostic artifacts and reproduction

- [Audit script](audit_author_motion.py): reruns the exact pinned entrypoint with in-process wrappers on `Robot.update_coordinate`, `Robot.expand_visited_path`, and `Robot_run.scan_around`; all wrappers are restored in `finally`. It checks source SHA and a clean tracked checkout, then asserts exact agreement with the old raw reproduction. It writes only the new `author-motion-audit/` directory.
- [Full decision trace CSV](author-motion-audit/decision-trace.csv) and [raw JSON](author-motion-audit/decision-trace.json): selected target, source iteration, coordinates, skeleton/ASP vertices, sensing counts, status flags, full paths, and sampled visibility evidence.
- [Collision-by-polygon JSON](author-motion-audit/collision-details.json): exact endpoints, original map/row/edge references, independent interior length, source collision-function outcome, and matching ASP status.
- [Summary JSON](author-motion-audit/summary.json): replay matching, termination, path geometry, and visibility counts.
- Full-map diagnostics: [dead-end](author-motion-audit/deadend-full.png) and [bugtrap](author-motion-audit/bugtrap-full.png). Gray is **ground truth**, blue is source state-to-state *linear interpolation*, green is computed/logged ASP, red is an interior-crossing straight link, gold is its radius-0.5 swept footprint. These are offline diagnostics, not what the online planner knew.
- Close-ups: [dead-end C1](author-motion-audit/deadend-C1-zoom.png), [C2](author-motion-audit/deadend-C2-zoom.png), [C3](author-motion-audit/deadend-C3-zoom.png), [C4](author-motion-audit/deadend-C4-zoom.png); [bugtrap polygon 1](author-motion-audit/bugtrap-C1-zoom.png) and [polygon 2](author-motion-audit/bugtrap-C2-zoom.png). C1/C2 in bugtrap are the **same transition** against different polygons.

From the repository root, with the pinned authors' checkout present and the above Python environment:

```powershell
git -C D:\Project\AStarAlgorithm-authors-benchmark rev-parse HEAD
git -C D:\Project\AStarAlgorithm-authors-benchmark status --porcelain
python experiments\benchmarks\audit_author_motion.py --authors-dir D:\Project\AStarAlgorithm-authors-benchmark
python -m py_compile experiments\benchmarks\audit_author_motion.py
```

The script fails if the checkout SHA differs, tracked files are dirty, maps differ from the frozen manifest hashes, source parser coordinates differ, old and new runtime traces differ, or independently calculated point-interior crossings disagree with Shapely. It does not rerun or alter the blocked 48-case comparison.
