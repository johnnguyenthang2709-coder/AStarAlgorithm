# A* Algorithm — Road and Robot Navigation

A completed university algorithms project demonstrating one reusable **C++17 A* search engine** in road routing and partially observed robot navigation. FastAPI exposes the engine through pybind11; React/TypeScript visualizes searches, sensing, exploration, and recovery.

## Applications

- **Road Navigation:** shortest-distance routing on 2,986 nodes and 7,152 directed road edges near HCMUT Campus 1. Clicking a road projects onto its polyline; request-local virtual endpoints preserve partial-edge costs and one-way direction. Compare A* and Dijkstra on identical snapped inputs. Local road geometry works without online map tiles.
- **Robot Navigation:** continuous 360° point-robot movement through polygonal mazes and indoor rooms, using limited-range, occlusion-aware sensing and accumulated discovered geometry. Radar-informed frontier exploration repeatedly invokes C++ A* on an observed visibility graph. Parent-aware backtracking plans a verified return with A*, with a reversed-entry fallback. Branch recovery certification applies under the documented reversible-trajectory assumptions; it is not general polygonal blind-alley detection.
- **Retained baselines:** editable four/eight-direction Robot Lab, limited-sensing grid BAR fixtures, fixed polygon environments, seeded Maze 3 and irregular labyrinths, and indoor rooms with furniture and doorways. These remain selectable alongside the continuous demonstrations.

![Continuous labyrinth observation and executed-path diagnostic](docs/images/labyrinth-observed-trace.png)

*Existing diagnostic figure: observed geometry and navigation trace; not a screenshot or evidence of universal navigation success.*

## Architecture and source guide

```text
React / TypeScript / Leaflet
            ↓ HTTP
FastAPI routers and robot exploration controllers
            ↓ pybind11
Shared C++ A* / Dijkstra search
            ↓
GridProblem | RoadProblem + temporary snapped edges | observed visibility graph
```

| Location | Responsibility |
| --- | --- |
| [include/astar/search.hpp](include/astar/search.hpp) | Main generic A* loop, queue updates, reopening, parent reconstruction; Dijkstra uses zero heuristic |
| [include/astar/](include/astar/) and [src/](src/) | Grid and directed-road problem adapters, edge snapping |
| [backend/bindings.cpp](backend/bindings.cpp) | Python/C++ interface |
| [backend/app/](backend/app/) | API validation, road loading, sensing, continuous exploration and recovery |
| [frontend/src/](frontend/src/) | Application interface, maps, trace and movement playback |
| [data/](data/) | Reproducible road bundle and robot fixtures |
| [tests/](tests/) | C++/Python correctness and regression coverage |
| [experiments/benchmarks/](experiments/benchmarks/) | Frozen protocols, manifests, raw results, diagnostics and validators |
| [reference/2550216/](reference/2550216/) | Original provided A* reference, preserved and regression-tested |

See [how A* is implemented](docs/astar-implementation.md), [continuous sensing and motion assumptions](docs/bar-continuous.md), [parent-aware backtracking audit](docs/bar-parent-backtracking-audit.md), [radar-informed exploration](docs/bar-radar-informed-exploration.md), [indoor exploration](docs/bar-indoor.md), and [irregular labyrinth design](docs/bar-labyrinth.md).

## Final reports

- **Approved HCMUT report:** [PDF](report/hcmut-project/report.pdf), [LaTeX entry point](report/hcmut-project/main.tex), [sources and build instructions](report/hcmut-project/), [final layout QA](report/hcmut-project/FINAL-LAYOUT-QA.md). The approved PDF has 21 pages. Its content and pagination are frozen.
- **Springer LNCS manuscript:** [PDF](report/springer-lncs/report.pdf), [LaTeX entry point](report/springer-lncs/main.tex), [sources](report/springer-lncs/), [literature review matrix](report/springer-lncs/LITERATURE-REVIEW-MATRIX.md).

The report-directory READMEs contain historical conversion notes; the checked-in PDFs, current metadata sources, and final validation records define the finalized versions. Rebuilding is optional and requires pdfLaTeX/BibTeX and the documented TeX packages. The application does not require LaTeX.

## Verified experiments and their limits

These are **frozen measurements**, not new experiments run during repository integration. See the [final benchmark report](experiments/benchmarks/FINAL-BENCHMARK-REPORT.md), [summary](experiments/benchmarks/FINAL-BENCHMARK-SUMMARY.md), [manifest and hashes](experiments/benchmarks/benchmark-final-manifest.json), and [data dictionary](experiments/benchmarks/benchmark-data-dictionary.md).

| Experiment | Verified result | Interpretation |
| --- | --- | --- |
| Road A* vs Dijkstra, 180 identical directed pairs | Equal optimal costs in 180/180; A* fewer expansions in 180/180; median paired expansion reduction 76%; median A*/Dijkstra search-time ratio 0.338 | Frozen local graph; C++ search timing only; no universal speed claim |
| Authors' ASP/DAP vs our A*, shared observed local states | 351 decisions captured, 21 eligible pairs; ASP shorter 9, A* shorter 10, equal 2 | Same observations/endpoints, different planning representations; not online navigation distance |
| Point-path validity of those 21 pairs | Interior-only validity 21/21 for both; strict boundary-free validity ASP 15/21, A* 21/21 | Boundary conventions matter; finite-radius safety is not established by the primary comparison |
| Frontier-cache study | Identical navigation playback in 20/20 paired episodes; median frontier processing 639.166 ms full vs 46.723 ms cached | Measured optimization on these configurations |
| Radar ranking study | 20 successful pairs; radar shorter in 18, longer in 2 | Exploration ordering can regress; no claim of global online optimality |

ASP Python core time and C++ A* search time have different scope and implementation language and must not be presented as an equivalent end-to-end speed comparison. The prespecified **48-case end-to-end authors-versus-our-robot comparison remains blocked** because source waypoint execution and footprint semantics are not reconciled. Planned path lengths, source coordinate transitions, and physically collision-checked executed distances are distinct quantities.

### Validate the frozen artifacts

From the repository root:

```powershell
.venv\Scripts\python.exe experiments\benchmarks\validate_road.py
.venv\Scripts\python.exe experiments\benchmarks\validate_supporting.py
.venv\Scripts\python.exe experiments\benchmarks\validate_final_benchmark.py
py -3.14 report\hcmut-project\scripts\validate_report.py
```

The final benchmark and report validators also require a clean, separately obtained authors' checkout at sibling directory `../AStarAlgorithm-authors-benchmark`, pinned to `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`. This checkout is not needed to run the applications. Report validation additionally uses `pypdf` and Poppler `pdftotext`; the command above uses the existing Python 3.14 report environment. Install `pypdf` in your chosen validator environment if necessary. Replaying authors' experiments has separate dependencies and source-commit requirements in the [benchmark reproduction documentation](experiments/benchmarks/FINAL-BENCHMARK-REPORT.md); validators check frozen data rather than regenerate measurements.

## Research attribution

The robot application studies the limited-vision blind-alley problem discussed by Phan Thanh An et al., *The sequences of bundles of line segments for autonomous robots with limited vision range to escape from blind alley regions*, **Robotics and Autonomous Systems 195 (2026), 105185**, [DOI](https://doi.org/10.1016/j.robot.2025.105185). Original research code: [ThanhBinhTran/autonomousRobot](https://github.com/ThanhBinhTran/autonomousRobot).

Our application keeps A* central and uses an observed visibility graph and frontier exploration. It does not reproduce the paper's bundle optimization/DAP algorithm. The [independent review](docs/bar-independent-review.md) and [motion-validity audit](experiments/benchmarks/author-motion-validity-audit.md) document the distinctions. No authors' source or CSV maps are bundled; their repository has no license granting redistribution. Local third-party papers remain untracked. Existing Springer template/style attribution and nlohmann/json licensing are retained; OSM-derived data retain the attribution below.

## Search behavior

The shared C++ core uses a priority queue ordered by lower `f`, then lower `h`, then insertion order. A better `g` pushes a fresh entry; stale entries are skipped. A state can reopen after an improvement. Parent links reconstruct paths, including `start == goal`. Dijkstra uses the same core and edges with `h = 0`. Costs and heuristic values must be finite and nonnegative. A* optimality requires an admissible heuristic; reopening accommodates an admissible but inconsistent one.

`GridProblem` allows four cardinal moves of cost 1, or eight moves with diagonal cost 1.5. Its heuristic is Manhattan for four moves and `max(dx,dy) + 0.5 min(dx,dy)` for eight. Diagonal moves require both adjacent cardinal cells to be free. Robot replanning is a fresh A* search from the **current robot cell** on the edited grid. Trace playback shows algorithm events; robot playback follows the final path. Replan count belongs to the frontend simulation, while search metrics describe only the latest C++ search.

`RoadProblem` preserves directed roads and distance costs in meters. Its Haversine heuristic is scaled by the graph's minimum edge-length/direct-distance ratio, capped at 1, to remain a lower bound despite small distance-model differences. Coordinate searches project onto the nearest road polyline and use request-local virtual endpoints with proportional partial-edge costs. A* and Dijkstra compare on the same snapped graph; `same_optimal_cost` is computed by the backend. UI comparisons show measured results for the selected route only. The routing objective is **shortest physical road distance**.

Traces are optional. With `trace=false`, C++ skips event collection and the binding/API return an empty trace; ordinary Find route requests use this mode. The frontend requests the full road node-coordinate mapping once when first drawing a trace, then resolves event node IDs in memory. It does not send one request per event. `CLOSE` ends one expansion; a later `UPDATE` can return that state to the frontier.

## Road data

`data/road/config.json` fixes the HCMUT Campus 1 center, 2,000 m extraction distance, OSMnx `drive` network, and simplification option. The checked-in export has 2,986 nodes and 7,152 directed edges. `scripts/preprocess_roads.py` writes `graph.json` for C++, `roads.geojson` for visualization, and `metadata.json` with counts and SHA-256 hashes. Startup verifies the graph and geometry hashes and counts together. A mismatch disables road endpoints while Robot Lab stays available. The offline endpoint `/api/road/geometry` serves verified bytes, so rebuilding data requires **one preprocess command and no manual frontend copy**.

The export uses OSMnx edge lengths. Parallel edges with the same ordered endpoints are reduced to the shortest distance, using edge key to break a tie. It retains OSM IDs, way IDs, names, and oriented geometry for selected edges. The largest weakly connected component may still contain unreachable directed pairs. Coordinate snapping linearly scans road polylines; existing node-to-node searches remain available in the C++ binding.

To regenerate data when online OSM access is available:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-road.txt
.venv\Scripts\python.exe scripts\preprocess_roads.py
.venv\Scripts\python.exe -m unittest discover -s tests -p preprocess_tests.py -v
```

The road geometry fallback stays visible when online tiles fail, provided FastAPI and the verified road bundle are running. Tile failure does not disable routing. The OpenStreetMap tile layer retains attribution; local data are OSM derived and subject to the [OpenStreetMap copyright and ODbL terms](https://www.openstreetmap.org/copyright). The vendored nlohmann/json header retains its MIT license.

## Windows setup and run

Tested with Windows CPython 3.12, MSYS2 UCRT64 `g++`, CMake, Ninja, Node.js 24, and npm. Install [uv](https://docs.astral.sh/uv/) and MSYS2 UCRT64 first. Python build packages, including pybind11, must be installed **before** CMake configures the binding. `requirements-road.txt` is needed only to regenerate OSM data; the checked-in export needs `requirements-backend.txt`.

From the repository root:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-backend.txt
$pybindDir = & .venv\Scripts\python.exe -m pybind11 --cmakedir
$pythonLib = & .venv\Scripts\python.exe -c "import pathlib,sys; print(pathlib.Path(sys.base_prefix)/'libs'/f'python{sys.version_info.major}{sys.version_info.minor}.lib')"
.venv\Scripts\cmake.exe -S . -B build-cpython -G Ninja `
  -DCMAKE_MAKE_PROGRAM="$PWD\.venv\Scripts\ninja.exe" `
  -DCMAKE_CXX_COMPILER="C:\msys64\ucrt64\bin\g++.exe" `
  -DPython_EXECUTABLE="$PWD\.venv\Scripts\python.exe" `
  -DPython_LIBRARY="$pythonLib" -Dpybind11_DIR="$pybindDir" -DCMAKE_BUILD_TYPE=Release
.venv\Scripts\cmake.exe --build build-cpython --parallel 4
```

Use the same Windows CPython for the virtual environment and binding; MSYS2's `libpython*.dll.a` cannot be imported by standard Windows Python. CMake builds C++ tests and places `astar_core*.pyd` with runtime DLLs in `backend/`.

Start FastAPI in one terminal:

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'backend')
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then start Vite in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/`. API docs are at `http://127.0.0.1:8000/docs`. Use `VITE_API_BASE_URL` in `frontend/.env.local` for a different API base (see `.env.example`); `ASTAR_CORS_ORIGINS` configures permitted frontend origins. `ASTAR_ROAD_GRAPH` can point to another `graph.json` in a complete road bundle directory. Grid endpoints stay available when road loading fails. A valid unreachable route returns HTTP 200 with `found=false`; invalid input returns 422.

## Tests and production build

Run from the repository root after building the binding:

```powershell
.venv\Scripts\ctest.exe --test-dir build-cpython --output-on-failure
.venv\Scripts\python.exe -m unittest discover -s tests -p preprocess_tests.py -v
$env:PYTHONPATH = (Join-Path $PWD 'backend')
.venv\Scripts\python.exe -m pytest -q tests
cd frontend
npm run test
npm run typecheck
npm run lint
npm run build
```

The C++ targets cover the reference, generic core, RoadProblem, and edge snapping. Other tests cover preprocessing, pybind11, FastAPI, deterministic robot cases, and frontend state/race behavior. `npm run build` writes `frontend/dist/`.

## Local cartography

Road Navigation overlays local OSM road hierarchy, deduplicated street labels, selected landmarks, and a metric scale with or without online tiles. **Map layers** controls street names, available buildings, landmarks, search states, one-way arrows, and graph nodes. Arrows and graph nodes are off by default; both use Canvas vector rendering. Click a road line for its actual OSM name/type, direction, length, and directed graph edge. POI markers provide details on click. Start and Destination have explicit text labels.

The checked-in display data were enriched from the original cached OSMnx road extraction. `osm-display-source.json` retains only the tags needed to reproduce this enrichment. It provides eight named bus stops/platforms, rather than manufacturing a target number of landmarks. OSM building downloads were unavailable in the development environment, so this bundle has **zero building polygons** and hides the Buildings switch. Polygon extraction and subtle rendering are implemented and tested for a future OSM context snapshot. The HCMUT point is the existing configured Campus 1 extraction anchor, not an inferred campus boundary or a newly sourced OSM campus feature; its popup makes this distinction explicit.

Reproduce the current cartography offline, preserving `graph.json` byte for byte:

```powershell
.venv\Scripts\python.exe scripts\preprocess_roads.py --context-only --osm-source data\road\osm-display-source.json
```

To fetch OSM buildings and selected POIs for the same configured area during preprocessing (requires Overpass access):

```powershell
.venv\Scripts\python.exe scripts\preprocess_roads.py --context-only --osm-source data\road\osm-display-source.json --download-context
```

The download saves `osm-context-source.json`. Later offline regeneration can repeat `--osm-source` for both saved snapshots. A full road rebuild can also add `--download-context`; without that flag or a saved context source, it exports no additional POIs/buildings. Frontend operation never queries Overpass. `context.geojson` is served by `/api/road/context`; its hash, center, and feature counts are checked alongside the graph/road bundle. Restart FastAPI after preprocessing to load the new bundle. No frontend copy is needed.

Street labels are prioritized by highway class and zoom, deduplicated by street name, and filtered for viewport edges, label collisions, and route/endpoint clearance. Local road styles group primary/secondary and their links as major, tertiary/unclassified as medium, residential as local, and remaining types as minor. Missing road information is shown as unrecorded. One-way chevrons follow the exported **directed geometry**, including OSM reverse-oneway roads, and have a bounded screen density. Context panes remain below route, endpoints, and search states.

Assets: enriched roads 2,318,534 bytes; context 1,750 bytes; saved display-source snapshot 351,848 bytes. The routing graph remains 1,742,486 bytes with SHA-256 `d3f4b7091e25c791c2ebcfbc4c3863622cc45baa745dae8359b5298e11d874bc`. Live online tiles could not be verified here. Their built-in labels cannot be controlled by the local Street names switch.

## Known limits

- Road optimization is distance only: no live traffic, ETA, travel-time objective, or road preferences.
- OSM turn-restriction relations are not modeled. Parallel-edge reduction is valid for the current distance objective.
- Edge snapping scans every road polyline and pairs reverse directions only when their exported geometries match.
- The packaged graph covers the local HCMUT area only; online tiles cannot extend routing.
- Grid navigation is classical A*, not Hybrid A*. Replanning repeats A*, not D* Lite.
- Online OpenStreetMap tiles require external network and still need a separate check where that host resolves. The bundled geometry and routing work without tiles when FastAPI is available.
