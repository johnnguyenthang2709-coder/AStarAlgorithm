# A* Navigation Lab

Explore shortest paths on a directed road graph near HCMUT Campus 1 and on an editable robot grid. **A* and Dijkstra run in C++17**. Python, pybind11, and FastAPI adapt and serve the results; React, TypeScript, and Leaflet visualize them. The original algorithm reference remains in `reference/2550216/` and is exercised by regression tests.

For a source-guided explanation of the algorithm, see [How A* works in this project](docs/astar-implementation.md).

Application 1, **Blind-Alley Robot Navigation**, is a separate limited-sensing
mode under **Blind Alley**. It uses the existing C++ four-direction A* with a
discovered occupancy map, frontier exploration, and autonomous exhausted-branch
recovery. The benchmark gate labels events only after navigation. See
[BAR methods and experiments](docs/bar-application.md) and the
[exact recovery trigger](docs/bar-recovery-trigger.md). The
[independent paper/source review](docs/bar-independent-review.md) distinguishes
this grid adaptation from the authors' continuous-space method. Run the fixed experiment
matrix with `.venv\Scripts\python.exe scripts\benchmark_bar.py`; see the
[frozen results table](docs/bar-results.md).
For a larger visual demonstration, the Blind Alley screen also includes
32 × 32 and 40 × 40 maps; see [large simulation measurements](docs/bar-large-simulation.md).
It also accepts polygon CSV maps from the original research generator format
through an offline, conservative grid converter. Two independently authored
irregular maps are included; see [polygon-map adaptation and results](docs/bar-polygon-maps.md).
The default Blind Alley view now offers **Maze 3: Irregular Labyrinth**, a seeded
continuous 2D point-robot demonstration with winding polygon corridors, dead
ends, and loops. The earlier room-based Maze 3 is still selectable.
It uses certified 360° observations, arbitrary-angle segments, and the same
C++ A* core through a Euclidean visibility graph adapter. The previous fixed
polygon scenarios and original grid benchmarks remain selectable. See
[irregular labyrinth design and results](docs/bar-labyrinth.md),
[original Maze 3 baseline](docs/bar-maze-3.md), and
[continuous method and assumptions](docs/bar-continuous.md).

```text
React + Leaflet → FastAPI → pybind11 → C++ search → RoadProblem / GridProblem / visibility graph
```

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

## Deterministic demos

Enter coordinates in Road Navigation and press each **Set** button. Search results and metrics always come from the live C++ engine.

| Demo | Start (lat, lon) | Goal (lat, lon) | Action | Measured result for checked-in graph |
| --- | --- | --- | --- | --- |
| A: Road A* | 10.7901425, 106.6432639 | 10.7909411, 106.6627844 | A* → Visualize search | 3,925.09 m, 458 expansions |
| B: Compare | 10.773535, 106.662370 | 10.7901425, 106.6432639 | Compare Dijkstra | Same 4,042.89 m; A* 694, Dijkstra 2,968 expansions |

Demo C uses the built-in 20 × 30 Robot Lab map. Select **8 directions**, **A***, then **Run search** (initial path cost 29). Press **Run robot** and pause after it reaches displayed row 11, column 5 (zero-based `(10,4)`). With **Draw obstacle** selected, click displayed row 11, column 7 (zero-based `(10,6)`). The app calls `/api/grid/replan` from `(10,4)`, updates the route and current search metrics, and increments the simulation replan count. The checked-in scenario replans to cost 27 from that cell; press **Run robot** again to reach the goal. Coordinates and obstacles are deterministic inputs, not stored algorithm output.

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
