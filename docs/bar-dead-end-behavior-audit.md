# Behavioral audit: short movements near a Maze 3 dead end

**Scope:** diagnosis only. No navigation policy, sensing, graph, A*, budget,
frontend, or test behavior was changed. Repository inspected on branch
`codex/bar-indoor-hierarchical` at `88ab9f9` (which contains parent-backtracking
commit `b8c4f4c`). The working tree was clean before this audit.

## 1. Reproduction and method

The original UI playback could not be uniquely identified from the request.
This is a **deterministic equivalent, not a claimed replay of that exact
incident**: Maze 3 Blind-Alley Labyrinth (`lab_alley`, `BLIND_ALLEY`, seed 23,
size 5, corridor width 2.4, loop rate 0.09, dead-end rate 0.8, trap count 3,
difficulty `hard`, irregularity 0.72), radius 5, start
`(22.409074, 7.376977)`, goal `(2.695563, 2.224511)`. The router uses
`prefer_novelty=True`, `complete_frontier_route=True`, the default 250-decision
limit, and no graph-debug or hierarchy frames. The generator's topology labels
the nearby cell `(3,3)` a dead end; that label is **auditor-only metadata** and
is not available to the controller.

Run from the repository root:

```powershell
.venv\Scripts\python.exe scripts\audit_bar_dead_end_decisions.py | Set-Content docs\bar-dead-end-decisions-full.csv
.venv\Scripts\python.exe -m pytest -q tests/test_bar_labyrinth.py tests/test_bar_continuous.py
```

The [full 45-decision CSV](bar-dead-end-decisions-full.csv) records the stack,
candidate coordinates/eligibility, a disk-based unknown-area score, current
known-free area, observed wall-fragment count, A* graph size, planned length,
actual movement, next sensor gain, graph-link changes, and return trigger.
The script temporarily wraps `select()` and `plan()` for **read-only** state
capture, restores both methods, and asserts that every emitted frame and the
termination status equal a separately run uninstrumented episode. `new_area`
comes from the sensor frame immediately **after** an exploration movement;
it is not the candidate score. The controller does not expose a calibrated
expected information-gain metric.

The episode reaches the goal at frame 158/159. The suspicious interval is
decisions 7–20, zero-based playback frames 18–73. A `sense`, a `plan`, and a
`move` are separate frames; one high-level decision may also include a locked
return's `recover_start`, movement, sensing, and `recover_end` frames.
For example, decision 7 is sense frame 18, A* plan frame 19, and actual
exploration move frame 20. Its measured information gain appears in the next
iteration's sense frame 21. Decision 8 then has return-start frame 22, an
actual return move at 23, a locked-route sense at 24, and return-end at 25.

## 2. Chronological decisions

Let **A** = `(17.489,15.823)`, the local branching anchor, and **P** =
`(17.489,11.723)`, its earlier parent. All target points below were already
inside certified free space at selection. Every A* call in this interval
found a route. The `score` is the selected candidate's **unseen disk area**
(world units²), which ignores wall occlusion; it is not predicted visible area.
`gain` is newly certified free area from the subsequent sensor observation.
Distances are geometric execution lengths. The full-precision coordinates and
the full ancestor stack appear in the CSV.

| Decision / frames | State and choice | Known FREE area; valid local targets / score | A* plan / executed | Gain; graph change | Why return was or was not selected |
| --- | --- | ---: | ---: | --- | --- |
| 7 / 18–20 | A → `(17.489,18.732)` explore | 82.877; 8 / 66.723 | 2.910 / 2.910 | 0.002275; +1 scan | Highest disk score; A retained seven other eligible targets. |
| 8 / 21–25 | terminal → A return | 82.879; 0 at leaf, 7 at A | 2.910 / 2.910 | 0; no scan | Leaf exhausted; nearest viable ancestor A; A* accepted. |
| 9 / 26–28 | A → `(16.325,17.839)` explore | 82.879; 7 / 64.501 | 2.328 / 2.328 | 0.001305; +1 scan | Different cached sibling at A; highest remaining score. |
| 10 / 29–33 | leaf → A return | 82.880; 0 at leaf, 6 at A | 2.328 / 2.328 | 0; no scan | Leaf exhausted; A still viable. |
| 11 / 34–36 | A → `(18.510,17.591)` explore | 82.880; 6 / 61.248 | 2.042 / 2.042 | 0.001312; +1 scan | Different cached sibling; highest remaining score. |
| 12 / 37–41 | leaf → A return | 82.882; 0 at leaf, 5 at A | 2.042 / 2.042 | 0; no scan | Leaf exhausted; A still viable. |
| 13 / 42–44 | A → `(16.218,16.557)` explore | 82.882; 5 / 59.782 | 1.469 / 1.469 | 0.000966; +1 scan | Different cached sibling; highest remaining score. |
| 14 / 45–49 | leaf → A return | 82.883; 0 at leaf, 3 at A | 1.469 / 1.469 | 0; no scan | Leaf exhausted; A still viable. |
| 15 / 50–52 | A → `(16.192,15.074)` explore | 82.883; 3 / 53.744 | 1.498 / 1.498 | 0.000110; +1 scan | Different cached sibling; highest remaining score. |
| 16 / 53–57 | leaf → A return | 82.883; 0 at leaf, 2 at A | 1.498 / 1.498 | 0; no scan | Leaf exhausted; A still viable. |
| 17 / 58–60 | A → `(16.153,13.508)` explore | 82.883; 2 / 49.504 | 2.673 / 2.673 | 0.001506; +1 scan | Different cached sibling; highest remaining score. |
| 18 / 61–65 | leaf → A return | 82.884; 0 at leaf, 1 at A | 2.673 / 2.673 | 0; no scan | Leaf exhausted; A still viable. |
| 19 / 66–68 | A → `(18.475,14.116)` explore | 82.884; 1 / 46.748 | 1.971 / 1.971 | 0.000625; +1 scan | Last eligible cached sibling at A. |
| 20 / 69–73 | leaf → P return | 82.885; 0 at leaf, 0 at A, 5 at P | 2.588 / 2.588 | 0; no scan | A now exhausted; nearest viable ancestor is P. A* takes a verified shortcut against a 31.909-unit recorded entry. |

At the start of decision 7, A's accumulated known-free area is 82.876795
units². It increases to 82.884893 by decision 20: the seven probes certify
only about **0.008099 units²** despite 14.890 units of outbound exploration
and 30.397 units of combined exploration and return movement. Each new scan
gain is below the 0.05-unit² threshold for adding fresh candidates, so these
are primarily **pre-existing candidates cached at A**, not a sequence of newly
discovered frontiers. Selected target identities are distinct; the verified
graph gains a scan waypoint and 4–10 links on each outbound probe. All local
returns use C++ A*, none use reversed-entry fallback. The seven leaf branches
each return immediately after their own post-move sense. At decision 20,
returning to P is shorter than retracing the accumulated entry. The existing
same-graph Dijkstra audit independently reports **2.588298** for this A*
return (frame 70), matching its planned and executed length.

At decision 7 the current 360° observation contains 22 visible wall
fragments and adds 4.620013 units² at A, but the policy stores the union of
**certified free** wedges, not a persistent blocked-cell map. It emits the
wall fragments for playback. Outside known-free space, a disk-based score
cannot distinguish unknown space behind an observed wall from a possible
opening around it. The later terminal observations show 12–22 visible wall
fragments per scan but add only the small free areas in the table. We do not
infer hidden passage geometry from the generator when assessing online
decisions.

## 3. Exact controller transitions

- [`ContinuousWorld.sense`](../backend/app/services/bar_continuous_geometry.py)
  lines 120–189 casts 360° rays, conservatively unions free wedges, chooses
  points on verified rays, and emits visible edge fragments.
- [`ContinuousPolicy.observe`](../backend/app/services/bar_continuous.py)
  lines 73–90 unions certified free area and stores a scan position. It adds
  sensor-generated candidates to the active node only when gain is at least
  0.05 units². Observed wall fragments are frame output, not a blocked-map
  input to the candidate score.
- [`_candidate_valid`, `available`, `select`](../backend/app/services/bar_continuous.py)
  lines 92–127 reject near-previous scans or candidates outside known free;
  require proximity to a known-free boundary and at least 0.1 units² of
  **disk** area outside known free; defer graph-blocked targets; then choose
  the current node's highest disk score in Maze 3. Ancestors are considered
  only when the current node has no eligible target. Thus A's siblings prevent
  a farther return until decision 20.
- [`failed_plan` and `complete_recovery`](../backend/app/services/bar_continuous.py)
  lines 129–152 preserve graph-blocked candidates and candidates observed
  during locked return. Neither graph-blocked path fires in this interval:
  every plan succeeds, no target is deferred, and no fallback is needed.
- [`plan` and `recovery_route`](../backend/app/services/bar_continuous.py)
  lines 188–211 and 241–265 build visibility edges covered by known free,
  invoke C++ A*, and accept a return only when its verified route does not
  exceed the recorded entry. This is graph-shortest, not globally shortest
  across every continuous curve.
- [`simulate_continuous`](../backend/app/services/bar_continuous.py)
  lines 300–350 senses before selection, executes every planned exploration
  segment with physical collision checking, pushes a child after movement,
  and locks a return until it reaches the selected ancestor. The optional
  indoor `branch_id` playback frames are disabled for this Maze 3 run; the
  captured stack positions/history indices supply its actual ancestry.

## 4. Counterfactual at the first suspicious decision

At decision 7, the terminal point `(17.489,18.732)` is already reachable in
known free space, but its surroundings are not fully certified. Eight distinct
points near the known-free boundary pass the current eligibility tests; the
selected point has 66.723 units² of disk area outside known free. The robot
has not yet measured the terminal point's later 0.002275-unit² gain. An
immediate return to P **cannot be justified as a correctness-preserving
decision from the available observations**. A wall seen from A may hide an
opening around a corner, and the disk score is only a coarse potential.

After the first probe, the actual gain is tiny, but seven sibling targets
remain at A. Those targets face different directions; the current map does
not prove that all their sensor views would be equally unproductive. The
controller therefore returns from the exhausted leaf **to A**, then tries a
sibling. The trace establishes poor realized information per unit distance;
it does not prove that every probe could safely have been skipped without
foregoing a reachable passage in another map with the same earlier scans.

## 5. Competing hypotheses

| Hypothesis | Supporting evidence | Contradicting evidence | Verdict |
| --- | --- | --- | --- |
| A. Occluded unknown warranted movement | Boundary candidates were reachable; unknown space remained outside certified free at every choice. | All seven realized gains were only 0.000110–0.002275 units²; no substantial new area was found. | **Inconclusive** for necessity or importance. |
| B. Distinct viable local targets remained | Seven distinct points were selected successively; each passed eligibility and C++ A* found a route. | Their realized gains were extremely small. | **Supported** for distinct eligibility; useful information remains unproven. |
| C. Duplicate target reconsideration | Movement repeatedly returned to A. | Target coordinates were distinct and removed from A's list; none was selected twice. | **Rejected**. |
| D. Ranking explicitly favors tiny moves | Several outbound segments are only 1.47–2.91 units. | The code ranks by unseen disk area first, not short distance; each selection had the highest remaining disk score. | **Rejected** literally; score calibration is a separate issue. |
| E. Exhaustion not reached for a legitimate state reason | Every leaf has zero eligible targets and returns immediately; A retains 7→1 eligible siblings until the last probe. | Realized gains suggest the siblings were low yield. | **Supported** under the defined policy state. |
| F. Incorrect state delayed required return | A remained active during the local pattern. | Leaf returns occur at decisions 8, 10, 12, 14, 16, 18; after A reaches zero, decision 20 returns to P. | **Rejected** as a parent-stack state error. |
| G. Wrong ancestor or unlocked retreat | Several returns occur. | Each early return targets A, then P when A is empty; all returns are locked A* routes and satisfy the executed bound. | **Rejected**. |
| H. Visibility-graph failures caused extra movement | Each probe adds a scan waypoint and verified links. | All A* plans are found; no failed-plan deferral or fallback occurs. | **Rejected** as the cause. |
| I. Playback exaggerates movement | Repeated overlapping lines are visible. | Each line corresponds to a real `move` frame and measured executed distance; the full trace matches the uninstrumented run. | **Rejected**. |
| J. Novelty proxy overestimates visible gain | Disk scores remain 46.748–66.723 units² while actual gains are <0.0023; the disk ignores occluding walls. | Unknown space can genuinely exist behind walls or around corners; the score was never intended as a guaranteed gain. | **Supported** as an information-efficiency limitation, not an A* correctness failure. |

## 6. Diagnosis and options for later approval

The repeated motion is real and deterministic. The robot **already returns to
the local parent after each leaf probe**. What looks like reluctance to
backtrack is A repeatedly choosing distinct, previously cached sibling
targets before moving back to P. A* and parent selection behave as specified.
The confirmed behavioral limitation is that an occlusion-unaware disk score
keeps these siblings attractive after very low realized sensor gain. There is
no demonstrated collision, path-optimality, ancestry, or duplicate-state
correctness defect.

If a future change prioritizes reducing this inefficiency, two narrow options
are worth evaluating before approval:

1. **Temporarily defer remaining siblings at an anchor after repeated
   negligible realized gain**, and revisit them only when the discovered map
   changes. Expected effect: fewer local probe/return cycles. Risk: an
   untried viewpoint could reveal a real opening; this rule could delay or
   prevent goal discovery in a different map. It must not label the physical
   branch formally exhausted.
2. **Rank candidates using an occlusion-aware estimate from accumulated
   observed geometry.** Expected effect: avoid assigning large value to
   unseen disks hidden behind walls. Risk: unknown geometry makes the estimate
   uncertain; wall-fragment handling and sensing consistency would add
   complexity and could still suppress useful viewpoints.

Neither option is implemented here. Any later correction should be tested on
this trace and on maps where a small-gain viewpoint precedes an important
opening. Current targeted regressions pass: **29/29**, with one existing
Starlette/httpx deprecation warning. Passing tests establish existing
invariants, not exploration efficiency or optimal online travel.
