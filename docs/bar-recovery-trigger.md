# Autonomous recovery trigger for the BAR grid benchmark

The controller receives only the static map through its sensor, a start cell, a goal
coordinate, and a sensing radius. The scenario's `evaluation_gate` or
`evaluation_gate_edges` are **not
controller input**. The evaluator reads that gate only after an episode to label
entry/exit crossings and calculate benchmark metrics.

At each sensed position, first use the observed FREE-cell graph and the existing
C++ A* to check for a verified route to the goal. If one exists, follow it. If it
does not, examine previously traversed edges in chronological order. An edge
`outside -> inside` is a candidate only when:

1. Removing that edge from the *currently observed* four-neighbor FREE graph
   separates the current cell from the start cell (the edge is a known bridge).
2. The current-cell side contains no active observed-FREE frontier adjacent to
   UNKNOWN. A frontier already sensed without adding any observation is inactive
   until the map changes.
3. The movement history contains an actual crossing into that side. Its suffix
   from the last `outside -> inside` crossing to the current position is retained
   verbatim as the reversible entry trajectory.

Choose the earliest qualifying bridge on the current traversal history. This
labels an exhausted observed branch, without claiming to recognize every
continuous-space blind alley. It depends only on the discovered map and executed
movements. In particular, it cannot access the benchmark gate or hidden obstacle
cells. If no edge qualifies, continue frontier-guided repeated A*.

Recovery runs A* from the current cell to the observed outside endpoint, then
executes the whole return path without switching to exploration. The exactly
reversed recorded entry trajectory is a verified fallback if A* cannot supply a
valid path or its planned length exceeds entry length. Under a static map,
reversible point-robot moves, and unit geometric edge lengths, the reverse is
feasible and A*'s shortest path is no longer. The implementation checks the
**executed** retreat distance against the **actual recorded** entry distance.
An invariant failure is reported explicitly if those assumptions fail.

The bridge test is implemented with one depth-first low-link pass over the
observed FREE graph. It has the same trigger semantics as testing each
historical edge by removal, which a randomized oracle test checks. A
multiple-cell entrance has no bridge and therefore no certified recovery under
this rule, even when the robot physically leaves the blind alley.

The evaluator separately looks for its declared gate crossing and measures the
episode's gate entry and retreat. Gate agreement with an autonomous bridge is a
benchmark outcome, not information supplied to the navigation policy.
