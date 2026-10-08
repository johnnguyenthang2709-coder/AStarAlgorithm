"""Exploratory BAR run on an externally supplied authors' polygon CSV.

No third-party map or code is bundled. This is a conservative grid adaptation,
not a reproduction of the paper's continuous-space experiment.
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.bar_service import BarController

Point = tuple[float, float]


def read_polygons(path: Path) -> list[list[Point]]:
    polygons: list[list[Point]] = []
    vertices: list[Point] = []
    seen_header = False
    with path.open(newline="", encoding="utf-8") as source:
        for line_number, row in enumerate(csv.reader(source), 1):
            if not row or all(not field.strip() for field in row):
                continue
            if len(row) != 2:
                raise ValueError(f"line {line_number}: expected two CSV columns")
            if [field.strip().lower() for field in row] == ["x", "y"]:
                if seen_header:
                    polygons.append(vertices)
                vertices = []
                seen_header = True
            else:
                if not seen_header:
                    raise ValueError(f"line {line_number}: expected x,y polygon header")
                try:
                    point = (float(row[0]), float(row[1]))
                except ValueError as exc:
                    raise ValueError(f"line {line_number}: invalid polygon coordinate") from exc
                if not all(math.isfinite(value) for value in point):
                    raise ValueError(f"line {line_number}: coordinates must be finite")
                vertices.append(point)
    if seen_header:
        polygons.append(vertices)
    if not polygons:
        raise ValueError("map must contain x,y polygon groups")
    for index, polygon in enumerate(polygons, 1):
        if len(polygon) > 1 and polygon[-1] == polygon[0]:
            polygon.pop()  # both explicitly closed and implicitly closed CSVs are accepted
        area = sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(polygon, polygon[1:] + polygon[:1])) / 2
        if len(set(polygon)) < 3 or abs(area) <= 1e-9:
            raise ValueError(f"polygon {index} must have nonzero area and three distinct vertices")
    return polygons


def point_segment_distance(point: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.dist(point, a)
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length_sq))
    return math.dist(point, (a[0] + t * dx, a[1] + t * dy))


def blocked(point: Point, polygons: list[list[Point]], robot_radius: float) -> bool:
    for polygon in polygons:
        inside = False
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            if point_segment_distance(point, a, b) <= robot_radius + 1e-9:
                return True
            if (a[1] > point[1]) != (b[1] > point[1]) and point[0] < (
                (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]
            ):
                inside = not inside
        if inside:
            return True
    return False


def segment_blocked(a: Point, b: Point, polygons: list[list[Point]], robot_radius: float) -> bool:
    if blocked(a, polygons, robot_radius) or blocked(b, polygons, robot_radius):
        return True
    def cross(p: Point, q: Point, r: Point) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    def on_segment(p: Point, q: Point, r: Point) -> bool:
        return abs(cross(p, q, r)) <= 1e-9 and (
            min(p[0], q[0]) - 1e-9 <= r[0] <= max(p[0], q[0]) + 1e-9 and
            min(p[1], q[1]) - 1e-9 <= r[1] <= max(p[1], q[1]) + 1e-9)
    for polygon in polygons:
        for c, d in zip(polygon, polygon[1:] + polygon[:1]):
            ab_c, ab_d = cross(a, b, c), cross(a, b, d)
            cd_a, cd_b = cross(c, d, a), cross(c, d, b)
            intersects = ((ab_c * ab_d < 0 and cd_a * cd_b < 0) or
                          any((on_segment(a, b, c), on_segment(a, b, d),
                               on_segment(c, d, a), on_segment(c, d, b))))
            if intersects or min(point_segment_distance(p, x, y) for p, x, y in
                                 ((a, c, d), (b, c, d), (c, a, b), (d, a, b))) <= robot_radius + 1e-9:
                return True
    return False


def rasterize(polygons: list[list[Point]], cell_size: int, robot_radius: float,
              goal: Point, conservative_edges: bool = True) -> tuple[str, ...]:
    max_x = max(goal[0], *(x for polygon in polygons for x, _ in polygon))
    max_y = max(goal[1], *(y for polygon in polygons for _, y in polygon))
    width = math.ceil(max_x / cell_size) + 2
    height = math.ceil(max_y / cell_size) + 2
    cells = [["#" if blocked((c * cell_size, r * cell_size), polygons, robot_radius)
              else "." for c in range(width)] for r in range(height)]
    if conservative_edges:
        remove = set()
        for r in range(height):
            for c in range(width):
                if cells[r][c] == "#":
                    continue
                for nr, nc in ((r + 1, c), (r, c + 1)):
                    if nr >= height or nc >= width or cells[nr][nc] == "#":
                        continue
                    a, b = (c * cell_size, r * cell_size), (nc * cell_size, nr * cell_size)
                    if segment_blocked(a, b, polygons, robot_radius):
                        remove.update(((r, c), (nr, nc)))
        for r, c in remove:
            cells[r][c] = "#"
    return tuple("".join(row) for row in cells)


def run(path: Path, cell_size: int, sensor_range: int, start: Point,
        goal: Point, robot_radius: float, conservative_edges: bool = True) -> dict:
    if cell_size < 1 or sensor_range < cell_size or robot_radius < 0:
        raise ValueError("invalid cell size, sensor range, or robot radius")
    if any(value < 0 or value % cell_size for value in (*start, *goal)):
        raise ValueError("start and goal must be nonnegative grid-center coordinates")
    polygons = read_polygons(path)
    rows = rasterize(polygons, cell_size, robot_radius, goal, conservative_edges)
    start_cell = (int(start[1] / cell_size), int(start[0] / cell_size))
    goal_cell = (int(goal[1] / cell_size), int(goal[0] / cell_size))
    if rows[start_cell[0]][start_cell[1]] != "." or rows[goal_cell[0]][goal_cell[1]] != ".":
        raise ValueError("rasterization blocks start or goal")
    controller = BarController(rows, start_cell, goal_cell, sensor_range / cell_size)
    episode = controller.run()
    invalid_steps = 0
    for a, b in zip(controller.history, controller.history[1:]):
        start_world = (a[1] * cell_size, a[0] * cell_size)
        end_world = (b[1] * cell_size, b[0] * cell_size)
        if segment_blocked(start_world, end_world, polygons, robot_radius):
            invalid_steps += 1
    return {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "cell_size": cell_size, "sensor_range": sensor_range,
            "robot_radius": robot_radius, "start": start, "goal": goal,
            "map_shape": [len(rows), len(rows[0])], "polygon_count": len(polygons),
            "raster_mode": "conservative_edges" if conservative_edges else "center_only",
            "continuous_collision_steps": invalid_steps,
            "status": episode["status"], "grid_goal_reached": episode["success"],
            "collision_free_goal_reached": episode["success"] and invalid_steps == 0,
            "autonomous_recovery_count": len(episode["recoveries"]),
            "metrics": episode["metrics"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--cell-size", type=int, default=5)
    parser.add_argument("--sensor-range", type=int, default=20)
    parser.add_argument("--start-x", type=float, default=0)
    parser.add_argument("--start-y", type=float, default=0)
    parser.add_argument("--goal-x", type=float, required=True)
    parser.add_argument("--goal-y", type=float, required=True)
    parser.add_argument("--robot-radius", type=float, default=0.0)
    parser.add_argument("--center-only", action="store_true",
                        help="Exploratory center-only occupancy; can permit edge collisions")
    args = parser.parse_args()
    result = run(args.map, args.cell_size, args.sensor_range,
                 (args.start_x, args.start_y), (args.goal_x, args.goal_y),
                 args.robot_radius, not args.center_only)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
