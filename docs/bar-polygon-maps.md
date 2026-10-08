# Polygon-map adaptation for Blind Alley

## Source assessment and integration decision

At authors' repository commit [`8bbbfb8`](https://github.com/ThanhBinhTran/autonomousRobot/tree/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8), [`Map_generator/map_generator.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Map_generator/map_generator.py) asks for obstacle vertices through Matplotlib `ginput`; left click adds, right click undoes, and middle click ends an obstacle. It writes one `x,y` header and integer vertex coordinates per obstacle through [`Obstacles.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Obstacles.py). [`map_display.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Map_generator/map_display.py) fills each polygon for inspection. The `-img` path uses [`Robot_world_lib.py`](https://github.com/ThanhBinhTran/autonomousRobot/blob/8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8/Robot_world_lib.py) to find OpenCV contours and writes the same CSV grouping, retaining only parent contours. Manual Matplotlib coordinates use *y up*; image pixel coordinates use *y down*. The CSV does not record which convention was used.

The original generator needs a graphical Matplotlib session; the image path additionally needs OpenCV. Its `-wsize` option sets the plotter's window, while `Robot_map_lib.Map.generate` fixes the input axis to 0–100; verify bounds in the output rather than relying on that switch. `Obstacles.read_csv` closes polygons in memory and also accepts repeated headers. The original repository exposes no license metadata, so **no authors' source code, CSV map, or image is bundled here**. Our checked-in CSVs were independently authored in its documented format. An upstream CSV can be imported offline from its own checkout.

We chose an **offline CSV-to-grid converter** in [`scripts/import_bar_polygon.py`](../scripts/import_bar_polygon.py). It preserves the current C++ four-neighbor unit-cost A*, limited sensing, discovered map, and bridge-based recovery. FastAPI serves only the converted occupancy scenario and a `polygon_grid` type label. The planner never receives polygon vertices, authoring metadata, or evaluation gates. The UI renders only cells revealed by sensing; its seamless default makes observed irregular walls legible, and “Grid lines” exposes the discrete model. The goal coordinate remains known, as in the existing BAR application.

## Format, transform, and safety model

Each polygon begins with `x,y`, followed by at least three finite vertices. Repeating the header starts the next polygon. The first vertex may optionally be repeated at the end. Concave simple polygons and multiple independent obstacles are supported. There is no hole syntax. Self-intersecting or self-touching shapes have ambiguous even-odd interiors and should be repaired before import. Every vertex must lie inside the declared world bounds.

The converter requires explicit `x_min y_min x_max y_max`, a cell size that exactly partitions both spans, and start/goal **at cell centers**. This avoids silently moving the mission endpoints. For manual maps, row 0 lies at `y_max`; for image contours use `--y-axis down`, so row 0 lies at `y_min`. The point robot is the default (`--robot-radius 0`). A positive radius is measured in world-coordinate units; an obstacle boundary closer than or equal to that radius blocks a center or move.

The rasterizer first marks centers inside or too close to polygons. It then checks every candidate cardinal center-to-center segment against all polygon edges, including clearance, and blocks both endpoint cells of any intersecting edge. Consequently **every remaining adjacent FREE pair has a collision-free center segment** under the static simple-polygon and numerical-tolerance assumptions. This is conservative: a narrow physically open corridor may close in the grid. The converter rejects a blocked or insufficient-clearance start/goal. It does not promise that a continuous-space route will remain connected at a chosen resolution. Sensor occlusion operates on the resulting occupancy cells, not exact continuous line of sight. BAR entry and retreat lengths remain counts of executed unit grid moves, not continuous geometric lengths.

## Reproduce the two included scenarios

From the repository root, with the project Python environment installed:

```powershell
.venv\Scripts\python.exe scripts\import_bar_polygon.py --source data\bar\polygon_sources\irregular_u.csv --output data\bar\irregular_u.json --bounds 0 0 40 40 --cell-size 1 --start 36.5 20.5 --goal 4.5 20.5
.venv\Scripts\python.exe scripts\import_bar_polygon.py --source data\bar\polygon_sources\irregular_bugtrap.csv --output data\bar\irregular_bugtrap.json --bounds 0 0 48 48 --cell-size 1 --start 43.5 23.5 --goal 5.5 23.5
```

`irregular_u` has seven polygons, a concave U, angled walls, exterior islands, and a one-cell mouth after rasterization. `irregular_bugtrap` has eight polygons, nested islands, and a larger concave trapping region. The generated JSONs contain source SHA-256, bounds, axis choice, cell size, clearance, and polygon count. Git preserves the CSV source bytes on every OS so those hashes remain reproducible. The deterministic tests regenerate equivalent scenario data and audit all traversable edges against the source polygons. Both are **new grid benchmarks inspired by the map format**, not the authors' benchmark maps or a reproduction of their continuous-space trials. No evaluation gate is defined for them; their `no_gate` label does not negate autonomous branch recoveries.

For an external authors' CSV, point `--source` to that file, choose bounds enclosing its vertices, then choose center-aligned start/goal and a clearance. Add `--y-axis down` for an image-derived `*.png.csv`. The source files inspected externally parsed as repeated polygon groups: `_map_deadend.csv` has one polygon with 339 vertices in approximately 0–100 coordinates; `_map_bugtrap.csv` and `Map_generator/_map_u_liked_shape.png.csv` each have two polygons with 562 vertices in approximately 0–200 coordinates. Their coordinates and images are not checked into this project. Before using an external source as a benchmark, independently specify its start/goal, robot size, bounds, and sensor range.

## Resolution and performance

We selected one world unit per cell after comparing the included U map at sizes 2, 1, and 0.5. The corresponding raster shapes/free-cell counts were 20×20/247, 40×40/1,076, and 80×80/4,313; offline conversion took approximately 0.12, 0.31, and 1.68 seconds on the development machine. The 40×40 map retains the narrow entrance and produces an autonomous recovery at sensing radii 2 and 4. A smaller cell captures more geometric detail but increases cells and potential playback memory fourfold. We do not infer topological equivalence to the original polygons from these counts alone. The tests include a passage that closes at coarse resolution and remains open at fine resolution. External authors' CSVs rasterized to 40×40 in approximately 1.9–3.3 seconds with the chosen conservative scan; offline conversion needs no spatial index at this scale.

Run the endpoint benchmark with:

```powershell
.venv\Scripts\python.exe scripts\benchmark_bar_polygon.py
```

One Windows CPython 3.12.10 run, via FastAPI `TestClient`, yielded:

| Scenario | Radius | Goal | Recoveries | Executed cells | Frames | Response bytes | Endpoint ms | Peak traced Python KiB | Raw playback snapshots KiB |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Irregular U, 40×40 | 1 | yes | 0 | 322 | 968 | 279,115 | 400 | 3,415 | 1,512 |
| Irregular U, 40×40 | 2 | yes | 1 | 202 | 598 | 186,911 | 264 | 2,614 | 934 |
| Irregular U, 40×40 | 4 | yes | 1 | 168 | 497 | 166,404 | 248 | 2,737 | 777 |
| Polygon bugtrap, 48×48 | 1 | yes | 1 | 476 | 1,411 | 415,384 | 723 | 5,246 | 3,175 |
| Polygon bugtrap, 48×48 | 2 | yes | 1 | 322 | 960 | 299,526 | 563 | 4,190 | 2,160 |
| Polygon bugtrap, 48×48 | 4 | yes | 1 | 230 | 680 | 229,194 | 478 | 3,559 | 1,530 |

Each request is run once for timing and again with `tracemalloc` for peak Python memory. That peak excludes native C++ and browser memory. Raw playback snapshots count one `Int8Array` byte per cell per frame; JavaScript object overhead is additional. The browser renders at most 2,304 grid cells per frame. These measured sizes did not justify a streaming protocol or canvas rewrite, but the 1,411-frame radius-1 playback is long (about 85 seconds at 60 ms/frame fast speed). Step, scrub, and next-recovery controls remain available.

## Claims and limitations

The C++ A* finds shortest paths on each *currently discovered, rasterized* grid. Online executed distance can exceed a full-map shortest path because the environment is unknown. A recovery bound applies only to a recognized exhausted branch under the existing reversible, static, unit-cost grid assumptions; it is verified from executed steps. The irregular polygon shape does not extend the BAR proof to arbitrary continuous regions. Conservative rasterization may block a real passage, and grid sensing can differ from continuous visibility. The external authors' source maps and paper use different geometry and evaluation protocols; do not compare their travel distances or claim experimental reproduction from these demonstrations.
