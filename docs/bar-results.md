# Frozen BAR benchmark results

This is the checked-in result of `scripts/benchmark_bar.py` on Windows,
CPython 3.12.10, the existing Release C++ binding, and the six original grid
fixtures in `data/bar/`. The machine-readable run is
[`bar-results.csv`](bar-results.csv). Recreate the matrix from the repository
root after building the binding:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar.py
```

All paths use four cardinal moves of unit cost. Radius is measured in grid
cells. **Executed** is the complete online movement history; **full map** is
an offline C++ A* search given the entire fixture from the outset. Full-map
cost is an evaluation reference, never planner input. **Extra** is executed
minus full-map distance for a successful run; it does not imply that the online
policy could have known the offline route. A dash means that a quantity does
not apply or that the goal is unreachable. `Calls` counts C++ A* invocations,
including recovery and any failed goal search. `Expanded` sums their expanded
nodes. `Turns` counts changes between consecutive executed cardinal headings;
there is no initial-orientation turn. `Plan ms` is measured wall time around
C++ binding calls, excluding sensing, frontier scoring, bridge analysis, and
rendering. It varies across reruns and is not directly comparable to the
authors' method timings.

| Scenario | Radius | Goal | Executed | Entry / retreat | Evaluation | A* returns / fallback | Calls | Expanded | Turns | Plan ms | Full map | Extra |
| --- | ---: | :---: | ---: | :---: | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alley_reachable | 1 | yes | 31 | 7 / 7 | certified | 1 / 0 | 26 | 65 | 4 | 0.254 | 17 | 14 |
| alley_reachable | 2 | yes | 31 | 7 / 7 | certified | 1 / 0 | 26 | 68 | 4 | 0.144 | 17 | 14 |
| alley_reachable | 3 | yes | 31 | 7 / 7 | certified | 1 / 0 | 26 | 71 | 4 | 0.147 | 17 | 14 |
| alley_turn | 1 | yes | 41 | 9 / 9 | certified | 1 / 0 | 34 | 85 | 8 | 0.183 | 23 | 18 |
| alley_turn | 2 | yes | 41 | 9 / 9 | certified | 1 / 0 | 34 | 86 | 8 | 0.167 | 23 | 18 |
| alley_turn | 3 | yes | 41 | 9 / 9 | certified | 1 / 0 | 34 | 94 | 8 | 0.184 | 23 | 18 |
| alley_shortcut | 1 | yes | 45 | 20 / 8 | certified | 1 / 0 | 39 | 120 | 9 | 0.181 | 17 | 28 |
| alley_shortcut | 2 | yes | 35 | 10 / 8 | certified | 1 / 0 | 29 | 88 | 8 | 0.139 | 17 | 18 |
| alley_shortcut | 3 | yes | 35 | 10 / 8 | certified | 1 / 0 | 29 | 95 | 8 | 0.124 | 17 | 18 |
| wide_mouth_alley | 1 | yes | 33 | — | uncertified exit | 0 / 0 | 33 | 66 | 5 | 0.136 | 19 | 14 |
| wide_mouth_alley | 2 | yes | 37 | — | uncertified exit | 0 / 0 | 37 | 127 | 8 | 0.188 | 19 | 18 |
| wide_mouth_alley | 3 | yes | 37 | — | uncertified exit | 0 / 0 | 37 | 138 | 8 | 0.179 | 19 | 18 |
| open_route | 1 | yes | 8 | — | no gate | 0 / 0 | 8 | 16 | 0 | 0.024 | 8 | 0 |
| open_route | 2 | yes | 8 | — | no gate | 0 / 0 | 8 | 23 | 0 | 0.027 | 8 | 0 |
| open_route | 3 | yes | 8 | — | no gate | 0 / 0 | 8 | 29 | 0 | 0.027 | 8 | 0 |
| unreachable | 1 | no | 5 | — | no gate | 0 / 0 | 5 | 11 | 2 | 0.018 | — | — |
| unreachable | 2 | no | 4 | — | no gate | 0 / 0 | 4 | 13 | 2 | 0.014 | — | — |
| unreachable | 3 | no | 3 | — | no gate | 0 / 0 | 3 | 13 | 1 | 0.010 | — | — |

The three `alley_shortcut` returns are genuine C++ A* routes, not reversed-entry
fallbacks. At radius 2, the return plan has cost 8 on the discovered map,
Dijkstra confirms cost 8 on the same snapshot, and the eight executed retreat
moves match that A* path. The reverse entry would take 10 moves. The existing
fallback regression forces a failed recovery plan and verifies execution of
the reversed recorded path. Thus both branches are tested. In contrast,
`wide_mouth_alley` has a successful natural gate exit but no locked certified
retreat. `unreachable` ends with `no_reachable_frontier`; it does not have an
offline path either.

The gate is evaluation metadata. Its entry/retreat numbers are emitted only
after the complete run; the controller neither receives nor queries the gate.
The bound applies to a recognized exhausted bridge branch under static,
correctly observed, reversible, unit-length edges with preserved entry history.
It does not cover every geometric blind alley, and total online travel is not
globally optimal in an unknown environment.

## Regression record

These commands were run from the repository root on 2026-10-08, except the
`npm` commands, which were run from `frontend/`:

| Command | Result |
| --- | --- |
| `.venv\Scripts\cmake.exe --build build-cpython --parallel 4` | Passed; Ninja reported no work to do |
| `.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure` | 4/4 passed |
| `.venv\Scripts\python.exe -m unittest discover -s tests -p preprocess_tests.py -v` | 9/9 passed |
| `.venv\Scripts\python.exe -m pytest -q tests` | 52 passed; one existing Starlette/httpx deprecation warning |
| `npm run test` | 24/24 passed across six files |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed |
| `npm run build` | Passed |

The Python suite includes a frozen-matrix test that regenerates all 18 rows
and compares every field except measured planning time. It also verifies
that the offline full-map cost never exceeds successful executed travel.
