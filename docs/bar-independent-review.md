# Independent review: A* and blind-alley navigation

Review date: 2026-10-08. Local project HEAD at review: `ab0535d`; this review
examines the working tree, including uncommitted BAR files. Authors' source was
inspected at commit `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`.
Primary research source: Phan Thanh An et al., *The Sequences of Bundles of
Line Segments for Autonomous Robots with Limited Vision Range to Escape from
Blind Alley Regions*, Robotics and Autonomous Systems 195 (2026) 105185,
[DOI 10.1016/j.robot.2025.105185](https://doi.org/10.1016/j.robot.2025.105185).
The full 21-page paper was inspected locally. Source links below are pinned to
the authors' commit.

## 1. Original repository analysis

The paper studies online travel toward a known goal in an initially unknown,
static, polygonal obstacle environment with limited circular vision. A blind
alley is a region entered without a forward way through; its requirement is an
escape trajectory no longer than the entry trajectory, under the paper's
stated setting. The authors' primary method is **not A***. It extracts local
open and closed sight intervals, ranks candidate open points by goal direction
and distance (with optional ranking-tree variants), records visited sights and
builds a visibility graph, obtains a skeleton route by breadth-first search,
then forms critical line-segment bundles and approximates a shortest route
through them. Exploration continues from an open point when a new goal route
is not yet visible. The paper distinguishes a general procedure (Algorithm 2,
without a general convergence guarantee) from a special constrained procedure
(Algorithm 3 and Proposition 5.1, under assumptions (3) and (4)). Neither is
a proof that arbitrary unknown environments yield globally shortest travel.

The experiment runner is
[`Robot_run_experiment_OUR_ASTAR_RRT_backward.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Robot_run_experiment_OUR_ASTAR_RRT_backward.py):
scan, rank/select open points, extend the visibility graph, take a BFS skeleton
path, and optimize with `approximately_shortest_path_old`. The sensing and
state logic are in
[`Robot_sight_lib.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Robot_sight_lib.py)
and
[`Robot_class.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Robot_class.py);
polygon CSV loading/collision geometry is in
[`Obstacles.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Obstacles.py);
open-point ranking is in
[`Robot_ranking.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Robot_ranking.py);
and bundle path construction is in
[`Robot_paths_lib.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Robot_paths_lib.py).

The authors compare their approximate shortest subpaths with an
[`a_star.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/a_star.py)
baseline over *already explored* space between selected open points. That
baseline rasterizes unexplored points as obstacles, uses eight-direction moves
(cardinal cost 1 and diagonal cost sqrt(2)), Euclidean heuristic, a dictionary
OPEN set scanned for minimum `g+h`, and a CLOSED dictionary. It updates an
OPEN state's `g`/parent on improvement, but does not reopen CLOSED states.
With this consistent heuristic and static nonnegative costs that is acceptable
for its model. It is not the authors' online exploration policy. Its source
header acknowledges PythonRobotics contributors; we did not copy it.

The paper reports two polygonal BAR maps, varying goals and vision ranges,
and measures subpath length, time, and turns for its approximate path, A*, and
RRT* comparisons, alongside complete-trajectory comparisons. The runner has
hardcoded map selection and limits comparisons to early cases per execution;
the repository does not provide a locked environment or a clear repository
license. Therefore a source inspection and grid adaptation can be reproduced
here, but the full published numeric table cannot be claimed independently
reproduced from that source alone. No authors' code or map is bundled here.

## 2. Research-to-code mapping

| Topic | Paper / authors | This project |
| --- | --- | --- |
| World | Continuous polygons, finite robot radius in experiments | Finite occupancy grid, point robot, static cells |
| Sensing | Circular local sight and obstacle boundary geometry | Radius-limited cell centers with conservative ray occlusion |
| Knowledge | Visited sights, open points, visibility graph | Separate UNKNOWN/FREE/BLOCKED discovered grid |
| Exploration | Ranked local/global open points | Reachable informative FREE frontier, distance/goal ranking |
| Path planning | BFS skeleton then bundle-based geometric approximation | Repeated existing C++ A* over observed FREE cells |
| A* role | Baseline for explored-space subpaths | Main executed route planner, including return route |
| BAR response | Paper's geometric procedure and special-case proof | Autonomous exhausted **bridge** branch and locked retreat |
| Cost | Euclidean geometric trajectories | Four-direction unit edges; one unit per executed step |
| Evaluation | Two polygon map families and varied starts/goals/ranges | Six deterministic grid fixtures and separate external-map adaptation |

This is a valid A*-centered **restricted benchmark version** of the online
navigation problem: the robot must explore, replan, recover in recognized
branches, and reach a goal when possible in its finite grid model. It is not a
reimplementation of the paper's full continuous polygon method. The recovery
guarantee covers only a recognized branch, not every geometric BAR. It is more
than a standalone retreat subproblem because goal navigation and exploration
are executed end-to-end.

## 3. Critical gap analysis

- The A* core uses a heap, improves `g`, skips stale entries, and permits
  reopening. Manhattan is admissible and consistent for four-direction unit
  edges. No core correctness problem was found, so the C++ core was retained.
- The controller receives ground truth only for sensing and a physical collision
  assertion. Evaluation gate metadata is parsed outside the controller and
  applied only after the run. A gate-change regression checks identical planner
  frames. The UI previously displayed final evaluation metrics while earlier
  frames played; it now displays them at episode end.
- A topological bridge is sufficient to identify some exhausted side branches,
  but it is not necessary for a blind alley. A three-cell mouth fixture reaches
  the goal after entering and exiting the alley with **no certified retreat**.
  This is a measured coverage limit, not a failed A* path.
- The recovery length theorem depends on static reversible unit edges and a
  preserved actual entry history. The implementation locks retreat until the
  outside anchor is reached, uses reversed history if the A* return is invalid
  or longer, and checks **executed** length. It makes no analogous guarantee
  for unrecognized alleys, asymmetric costs, dynamic obstacles, or continuous
  collision clearance.
- The finite fixture set and ideal sensor do not cover noisy vision, moving
  obstacles, robot kinematics, or general polygon visibility. In particular,
  the authors' figures and published path lengths are not directly comparable
  to grid path lengths or four-direction turn counts.

## 4. Technical decision record

Retain the finite grid model and C++ A* core for this algorithms course. A*
plans the selected frontier and goal routes and attempts each retreat route;
the verified reversed-entry path is the retreat fallback. Score many candidate
frontiers in one BFS pass, which gives the same exact costs for unit edges;
then assert agreement with A* for the selected route. Retain the observed-map
bridge trigger, now implemented in one low-link DFS pass, and expose its
coverage limit explicitly. Keep benchmark gates as evaluation-only labels and
certify the gate bound only for a locked retreat crossing.

Alternatives considered: copying the authors' geometric/open-point system
would replace the A*-centered application, add substantial polygon and bundle
machinery, and raise source licensing questions. Treating any apparent dead
end or wide-mouth entry as a BAR would require an arbitrary, often hidden
entrance definition and could claim a false guarantee. A general cut or region
detector might broaden coverage but needs a defined topology/entry semantics
and substantially more validation. The focused bridge model is honest and
reproducible; the wide-mouth counterexample is retained in the benchmark.

## 5. Implementation changes from this review

- `backend/app/services/bar_service.py`: one exact frontier-distance BFS and
  one low-link bridge pass replace repeated A* candidate scoring and repeated
  graph traversals. The selected route and retreat still use C++ A*.
- `backend/app/services/bar_scenarios.py` and `bar_evaluation.py`: evaluation
  accepts one gate or a set of gate edges, and distinguishes no entry, no exit,
  uncertified exit, certified return, and bound failure.
- `data/bar/wide_mouth_alley.json`: original counterexample fixture.
- `data/bar/alley_shortcut.json`: a deterministic branch in which A* executes
  an eight-move return instead of reversing a ten-move entry at radius 2.
- BAR API types, frontend playback, tests, and benchmark were updated for that
  status. Final evaluation metrics are revealed only at the final frame.
- `scripts/evaluate_author_map.py` optionally reads an externally supplied
  authors' polygon CSV. Conservative rasterization removes cells incident to
  any colliding cardinal segment; every executed segment is checked again
  against the polygons and reported separately. It is an adaptation, not a
  replacement for the authors' continuous robot experiment.

No Road Navigation, generic A*, Robot Lab, or road preprocessing code changed.

## 6. Validation and reproducibility

Run the project regression commands in `README.md`, then:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar.py
.venv\Scripts\python.exe scripts\evaluate_author_map.py --map D:\path\to\_map_deadend.csv --cell-size 2 --sensor-range 20 --goal-x 70 --goal-y 90
.venv\Scripts\python.exe scripts\evaluate_author_map.py --map D:\path\to\_map_bugtrap.csv --cell-size 2 --sensor-range 20 --goal-x 160 --goal-y 80
```

The [checked-in matrix](bar-results.md) has 18 runs (six maps times three sensor
radii). The two original narrow-branch fixtures reach the goal and show certified
gate returns with entry and retreat lengths 7/7 and 9/9. A third fixture
demonstrates a shorter A* return: 10/8 at radii 2 and 3, and 20/8 at radius 1.
The wide-mouth fixture
also reaches the goal, but its exits are *uncertified* at every radius. The
open route reaches its goal without a BAR; the unreachable fixture ends with
no reachable informative frontier. In the fixed radius-2 runs, executed
distances are respectively 31, 41, 35, 37, 8, and 4 grid units. The CSV records
turns (changes in consecutive cardinal headings), C++ A* expanded nodes and
call count, and measured C++ binding wall time; timings vary by machine.

For the two externally supplied authors' map CSVs at pinned source commit,
cell size 2, sensing radius 20 world units, point robot, and chosen goals
`(70,90)` and `(160,80)`, the conservative grid adaptation reached both
goals with zero checked continuous segment collisions. The first run traveled
232 world units, made 75 turns, made 225 A* calls, expanded 1,144 nodes, and
recorded three autonomous recoveries. The second traveled 288 units, made 141
turns, made 288 A* calls, expanded 1,719 nodes, and recorded no recovery.
The input SHA-256 hashes are
`b996dcca108a22c249f4c9a3239c72e67cefdf7ce1189ce637a3cc5c408f5d91`
for `_map_deadend.csv` and
`fa564df538cbf3ecc6632062d102217277218e22158a660e7c8414a7f202d3a6`
for `_map_bugtrap.csv`. These outcomes depend on the stated raster, movement,
sensor, and goal choices.
The same two center-only coarse raster runs *did* permit geometric collisions;
those invalid runs motivated the conservative check and must not be reported
as successful continuous-space experiments. At cell size 5, the conservative
dead-end raster blocks the chosen goal. None of these runs recreates the
paper's robot radius, eight-direction baseline, subpath protocol, or published
aggregate results. No paper-result superiority claim follows.

## 7. Guidance for the university report

Accurate claim: “We implemented a limited-sensing four-neighbor grid
adaptation of blind-alley navigation. The robot builds an observed map,
explores informative frontiers, repeatedly uses C++ A* for movement, and
executes a locked A* return with a reversible-history fallback when an
exhausted branch is certified by an observed-graph bridge. Under static,
reversible unit edges, its executed return is no longer than the recorded
entry for those recognized branches.”

Also state the counterexample: a wider entrance is not recognized by this
bridge rule, although the robot can still explore and reach the goal. Do not
claim that this project implements the authors' bundle algorithm, detects all
BARs, obtains globally optimal travel in an unknown world, proves the paper's
general method, or outperforms the published experiment. Cite the paper for
its mathematical claims, and the authors' source for observed implementation
details; distinguish these from our engineering choices and tests.
