# Larger Blind Alley demonstrations

The six original grid fixtures and their [frozen benchmark](bar-results.md)
remain unchanged. Two additional, checked-in maps are for longer UI
demonstrations:

- `expedition_narrow.json` (32 × 32): a one-cell entrance, branching chamber,
  obstacle islands, side corridors, and nested dead ends. At radius 2 or 4 the
  observed-map bridge trigger certifies the benchmark gate return. At radius 1
  the policy reaches the goal without entering that gate; `no_entry` is the
  correct evaluation label.
- `expedition_wide.json` (40 × 40): a three-cell entrance, room obstacles, side
  passages, and several recoverable interior branches. The robot reaches the
  goal after exiting the wide benchmark mouth, but that exit is **uncertified**.
  Interior branches may have locked, verified retreats. The UI distinguishes
  those events from the overall gate label.

Both maps retain a known goal coordinate and initially unknown occupancy.
Only the sensor reads obstacle rows to reveal cells; a movement assertion
checks physical collisions. The controller cannot access evaluation gates.
Existing four-direction unit-cost C++ A*, sensing, frontier selection, and
bridge recovery are unchanged.

## Reproduce the large-run measurements

After building the binding, run from the repository root:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar_large.py
```

This invokes the existing FastAPI endpoint in process through TestClient.
The table below is one Windows CPython 3.12.10 run. Endpoint time and A*
planning time are wall-clock samples, not stable baselines; their decimal
formatting can also change response size by a few bytes. Frame counts, path
metrics, and labels are deterministic for these inputs.
The existing Starlette/httpx deprecation warning may appear on stderr.

| Map | Radius | Frames | API bytes | Endpoint ms | Goal | Gate label | Recoveries | Distance | A* calls | Expanded | Turns |
| --- | ---: | ---: | ---: | ---: | :---: | --- | ---: | ---: | ---: | ---: | ---: |
| 32 × 32 narrow | 1 | 149 | 45,487 | 45.7 | yes | no entry | 0 | 49 | 49 | 98 | 3 |
| 32 × 32 narrow | 2 | 486 | 147,836 | 248.3 | yes | certified | 2 | 165 | 152 | 376 | 27 |
| 32 × 32 narrow | 4 | 399 | 124,410 | 116.7 | yes | certified | 2 | 137 | 121 | 341 | 19 |
| 40 × 40 wide | 1 | 926 | 271,030 | 461.5 | yes | uncertified exit | 4 | 314 | 292 | 736 | 66 |
| 40 × 40 wide | 2 | 728 | 219,776 | 339.7 | yes | uncertified exit | 4 | 248 | 226 | 695 | 43 |
| 40 × 40 wide | 4 | 645 | 200,365 | 247.0 | yes | uncertified exit | 4 | 220 | 199 | 779 | 33 |

The 40 × 40 radius-1 run crosses the evaluation mouth twice in each direction.
No crossing is a locked retreat across that mouth. Its four verified interior
branch recoveries must not be presented as certification of the wide-mouth
gate. One separate local HTTP run took approximately 1.2 seconds for the
largest case, including server and transport overhead.

The observed-map playback is cached once as one `Int8Array` per frame, so
scrubbing to a later frame does not replay hundreds of earlier frames. Raw
occupancy snapshots use `frames × rows × cols` bytes: at most 1,481,600 bytes
(about 1.41 MiB) for the six runs above, before JavaScript object overhead.
Controller-only Python `tracemalloc` sampling peaked at about 1.1 MiB for the
40 × 40 radius-1 episode; that excludes native C++ and FastAPI serialization.
The grid has at most 1,600 DOM cells. These measurements do not justify a
streaming API, spatial index, or canvas rewrite at this scale.

## Playback and presentation

The map occupies the main workspace. Fit, zoom, and native scrolling support
inspection on desktop and mobile. “Follow robot” keeps the active position
visible while zoomed; turn it off to pan independently. Frontiers are marked
only where observed FREE touches UNKNOWN and can be hidden. This visual count
describes the geometric boundary; the controller may temporarily suppress a
frontier that produced no new observation. The known goal
coordinate is marked even before its occupancy is sensed, without revealing
the cell state. The selected path, recorded entry, and executed retreat use
separate restrained colors. A frame callout describes sensing, planning,
movement, recovery, and finish events without revealing final benchmark
results early.

Playback supports careful, normal, and fast speeds (240, 120, and 60 ms per
frame), single-frame steps, a scrubber, and a jump to the next autonomous
recovery. At fast speed the longest 926-frame run takes roughly 56 seconds if
played from beginning to end. Outcome metrics appear at the final frame.

These demos increase visual and behavioral complexity, not the scope of the
mathematical guarantee. The bridge trigger still covers only recognized
exhausted branches under the static reversible grid assumptions in
[bar-recovery-trigger.md](bar-recovery-trigger.md).
