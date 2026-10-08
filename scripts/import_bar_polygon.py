"""Convert the authors' repeated x,y polygon CSV format to a BAR grid scenario.

This is an offline, conservative four-neighbor grid adaptation. No source
polygon geometry is sent to the navigation policy or playback API.
"""

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from evaluate_author_map import Point, blocked, read_polygons, segment_blocked


@dataclass(frozen=True)
class GridTransform:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    cell_size: float
    y_axis: str = "up"

    def __post_init__(self):
        values = (self.x_min, self.y_min, self.x_max, self.y_max, self.cell_size)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("bounds and cell size must be finite")
        if self.x_max <= self.x_min or self.y_max <= self.y_min or self.cell_size <= 0:
            raise ValueError("bounds must have positive area and cell size must be positive")
        if self.y_axis not in ("up", "down"):
            raise ValueError("y_axis must be 'up' or 'down'")
        for span in (self.x_max - self.x_min, self.y_max - self.y_min):
            count = span / self.cell_size
            if not math.isclose(count, round(count), rel_tol=0, abs_tol=1e-8):
                raise ValueError("each bound span must be a whole number of cells")

    @property
    def width(self) -> int:
        return round((self.x_max - self.x_min) / self.cell_size)

    @property
    def height(self) -> int:
        return round((self.y_max - self.y_min) / self.cell_size)

    def center(self, row: int, col: int) -> Point:
        return (self.x_min + (col + 0.5) * self.cell_size,
                self.y_max - (row + 0.5) * self.cell_size if self.y_axis == "up"
                else self.y_min + (row + 0.5) * self.cell_size)

    def cell(self, point: Point) -> tuple[int, int]:
        x, y = point
        col = (x - self.x_min) / self.cell_size - 0.5
        row = ((self.y_max - y) if self.y_axis == "up" else (y - self.y_min)) / self.cell_size - 0.5
        if not all(math.isfinite(value) for value in point):
            raise ValueError("start and goal coordinates must be finite")
        r, c = round(row), round(col)
        if not (0 <= r < self.height and 0 <= c < self.width):
            raise ValueError("start or goal lies outside map bounds")
        if not math.isclose(row, r, rel_tol=0, abs_tol=1e-8) or not math.isclose(col, c, rel_tol=0, abs_tol=1e-8):
            raise ValueError("start and goal must be exact cell centers; adjust bounds or cell size")
        return r, c


def rasterize_bounded(polygons: list[list[Point]], transform: GridTransform,
                      robot_radius: float) -> tuple[str, ...]:
    if not math.isfinite(robot_radius) or robot_radius < 0:
        raise ValueError("robot radius must be finite and nonnegative")
    if not polygons:
        raise ValueError("at least one polygon is required")
    for polygon in polygons:
        for x, y in polygon:
            if not (transform.x_min <= x <= transform.x_max and
                    transform.y_min <= y <= transform.y_max):
                raise ValueError("polygon vertex lies outside map bounds")
    height, width = transform.height, transform.width
    cells = [["#" if blocked(transform.center(r, c), polygons, robot_radius) else "."
              for c in range(width)] for r in range(height)]
    # The planner has only cell occupancy, not per-edge collision flags. Remove
    # both endpoints of every intersecting center-to-center edge. This may
    # close a narrow passage, but cannot leave a traversable crossing.
    removed: set[tuple[int, int]] = set()
    for r in range(height):
        for c in range(width):
            if cells[r][c] == "#":
                continue
            for nr, nc in ((r + 1, c), (r, c + 1)):
                if nr >= height or nc >= width or cells[nr][nc] == "#":
                    continue
                if segment_blocked(transform.center(r, c), transform.center(nr, nc),
                                   polygons, robot_radius):
                    removed.update(((r, c), (nr, nc)))
    for r, c in removed:
        cells[r][c] = "#"
    return tuple("".join(row) for row in cells)


def import_scenario(source: Path, transform: GridTransform, start: Point, goal: Point,
                    robot_radius: float = 0.0) -> dict:
    polygons = read_polygons(source)
    rows = rasterize_bounded(polygons, transform, robot_radius)
    start_cell, goal_cell = transform.cell(start), transform.cell(goal)
    for label, (r, c) in (("start", start_cell), ("goal", goal_cell)):
        if rows[r][c] != ".":
            raise ValueError(f"{label} is blocked or lacks the specified clearance")
    return {
        "rows": rows, "start": start_cell, "goal": goal_cell,
        "continuous_world": {
            "bounds": [transform.x_min, transform.y_min, transform.x_max, transform.y_max],
            "y_axis": transform.y_axis, "start": start, "goal": goal,
            "polygons": polygons,
        },
        "map_source": {
            "format": "authors_polygon_csv", "file": source.name,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "polygon_count": len(polygons),
            "bounds": [transform.x_min, transform.y_min, transform.x_max, transform.y_max],
            "cell_size": transform.cell_size, "robot_radius": robot_radius,
            "axis": f"CSV y {transform.y_axis}; grid row 0 at " +
                    ("y_max" if transform.y_axis == "up" else "y_min"),
            "rasterization": "blocked centers and endpoints of intersecting cardinal edges",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bounds", nargs=4, type=float, required=True,
                        metavar=("X_MIN", "Y_MIN", "X_MAX", "Y_MAX"))
    parser.add_argument("--cell-size", type=float, required=True)
    parser.add_argument("--y-axis", choices=("up", "down"), default="up",
                        help="manual Matplotlib maps use up; OpenCV image contours use down")
    parser.add_argument("--start", nargs=2, type=float, required=True, metavar=("X", "Y"))
    parser.add_argument("--goal", nargs=2, type=float, required=True, metavar=("X", "Y"))
    parser.add_argument("--robot-radius", type=float, default=0.0)
    args = parser.parse_args()
    transform = GridTransform(*args.bounds, args.cell_size, args.y_axis)
    scenario = import_scenario(args.source, transform, tuple(args.start), tuple(args.goal), args.robot_radius)
    args.output.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
    print(f"{args.output}: {transform.height}x{transform.width}, "
          f"{scenario['map_source']['polygon_count']} polygons, "
          f"{sum(row.count('.') for row in scenario['rows'])} free cells")


if __name__ == "__main__":
    main()
