"""Conservative 360-degree polygon sensing for a holonomic point robot.

Only certified free triangles and observed boundary fragments leave the sensor.
The controller never receives this world's polygons or collision oracle.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import LineString, Point as ShapePoint, Polygon, box, mapping
from shapely.ops import unary_union

from app.services.bar_scenarios import SCENARIO_DIR, load_scenario

Point = tuple[float, float]
EPS = 1e-7
RAY_MARGIN = 1e-3


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def as_point(point: Point) -> dict[str, float]:
    return {"x": round(point[0], 6), "y": round(point[1], 6)}


def point_tuple(value: dict) -> Point:
    return float(value["x"]), float(value["y"])


def segment_in_region(region, a: Point, b: Point) -> bool:
    return region.covers(LineString((a, b)))


@dataclass(frozen=True)
class SensorObservation:
    region: object
    candidates: tuple[Point, ...]
    edges: tuple[tuple[Point, Point], ...]

    def geojson(self) -> dict:
        return mapping(self.region)


class ContinuousWorld:
    """Simulator-only ground truth. The policy sees SensorObservation values."""

    def __init__(self, bounds: tuple[float, float, float, float],
                 polygons: tuple[tuple[Point, ...], ...], start: Point,
                 goal: Point, y_axis: str = "up"):
        if y_axis not in ("up", "down") or len(bounds) != 4 or not all(map(math.isfinite, bounds)):
            raise ValueError("invalid continuous-world bounds or axis")
        x0, y0, x1, y1 = bounds
        if x1 <= x0 or y1 <= y0:
            raise ValueError("continuous-world bounds must have positive area")
        self.bounds = bounds
        self.start, self.goal, self.y_axis = start, goal, y_axis
        self.border = box(*bounds)
        shapes = []
        for vertices in polygons:
            shape = Polygon(vertices)
            if not shape.is_valid or shape.area <= EPS or not self.border.covers(shape):
                raise ValueError("continuous obstacles must be simple polygons inside bounds")
            shapes.append(shape)
        self.polygons = polygons
        self.obstacles = unary_union(shapes)
        self.free_space = self.border.difference(self.obstacles)
        for label, point in (("start", start), ("goal", goal)):
            if not all(map(math.isfinite, point)) or not self.border.contains(ShapePoint(point)) or self.obstacles.intersects(ShapePoint(point)):
                raise ValueError(f"continuous {label} must be strictly free and inside bounds")
        self.edges: list[tuple[Point, Point, tuple[int, int] | None]] = []
        for polygon_index, vertices in enumerate(polygons):
            for edge_index, (a, b) in enumerate(zip(vertices, vertices[1:] + vertices[:1])):
                self.edges.append((a, b, (polygon_index, edge_index)))
        corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        for a, b in zip(corners, corners[1:] + corners[:1]):
            self.edges.append((a, b, None))

    @classmethod
    def load(cls, name: str):
        scenario = load_scenario(name)
        if scenario.map_source is None or scenario.map_source.get("robot_radius") != 0:
            raise ValueError("continuous mode requires a point-robot polygon scenario")
        data = json.loads((SCENARIO_DIR / f"{name}.json").read_text(encoding="utf-8"))
        source = data.get("continuous_world")
        if not source:
            raise ValueError("scenario has no continuous polygon world")
        bounds = tuple(float(v) for v in source["bounds"])
        polygons = tuple(tuple((float(x), float(y)) for x, y in polygon)
                         for polygon in source["polygons"])
        return cls(bounds, polygons, tuple(source["start"]), tuple(source["goal"]), source["y_axis"])

    def collision_free(self, a: Point, b: Point) -> bool:
        path = LineString((a, b))
        return self.border.covers(path) and not self.obstacles.intersects(path)

    def _cast(self, origin: Point, angle: float, radius: float,
              edges=None) -> tuple[float, tuple[int, int] | None]:
        dx, dy = math.cos(angle), math.sin(angle)
        best, hit = radius, None
        for a, b, identity in self.edges if edges is None else edges:
            ex, ey = b[0] - a[0], b[1] - a[1]
            denominator = dx * ey - dy * ex
            if abs(denominator) < 1e-12:
                continue
            rx, ry = a[0] - origin[0], a[1] - origin[1]
            t = (rx * ey - ry * ex) / denominator
            u = (rx * dy - ry * dx) / denominator
            if EPS < t < best + EPS and -EPS <= u <= 1 + EPS:
                best, hit = max(0, t), identity
        return best, hit

    def sense(self, origin: Point, radius: float) -> SensorObservation:
        if radius <= 0 or not self.collision_free(origin, origin):
            raise ValueError("sensor pose must be free and radius positive")
        # Only nearby segments can intersect a radius-limited ray. This changes
        # neither the observed geometry nor the conservative wedge test.
        active_edges = [(a, b, identity) for a, b, identity in self.edges
                        if min(a[0], b[0]) <= origin[0] + radius
                        and max(a[0], b[0]) >= origin[0] - radius
                        and min(a[1], b[1]) <= origin[1] + radius
                        and max(a[1], b[1]) >= origin[1] - radius]
        # Vertex rays resolve concave corners. Uniform rays bound arc error.
        angles = {2 * math.pi * index / 72 for index in range(72)}
        for a, b, _ in active_edges:
            for vertex in (a, b):
                vertex_distance = distance(origin, vertex)
                if vertex_distance > radius + EPS:
                    continue
                theta = math.atan2(vertex[1] - origin[1], vertex[0] - origin[0])
                first_hit, _ = self._cast(origin, theta, radius, active_edges)
                if first_hit < vertex_distance - 1e-5:
                    continue  # hidden vertices must not affect the observation
                for delta in (-1e-5, 0, 1e-5):
                    angles.add((theta + delta) % (2 * math.pi))
        samples = []
        for angle in sorted(angles):
            hit_distance, identity = self._cast(origin, angle, radius, active_edges)
            end_distance = hit_distance - RAY_MARGIN if identity is not None or hit_distance < radius - EPS else radius
            end_distance = max(0, end_distance)
            point = (origin[0] + end_distance * math.cos(angle),
                     origin[1] + end_distance * math.sin(angle))
            samples.append((angle, point, hit_distance, identity))
        triangles = []
        valid_wedges = []
        for left, right in zip(samples, samples[1:] + samples[:1]):
            triangle = Polygon((origin, left[1], right[1]))
            valid = triangle.area > EPS and self.border.covers(triangle) and not self.obstacles.intersects(triangle)
            valid_wedges.append(valid)
            if valid:
                triangles.append(triangle)
        region = unary_union(triangles) if triangles else ShapePoint(origin).buffer(EPS)
        # Candidate waypoints lie along verified rays. Short rays also let the
        # robot inspect polygon corners and the far side of narrow mouths.
        candidates = []
        for index in range(0, 72, 6):
            angle = 2 * math.pi * index / 72
            hit_distance, identity = self._cast(origin, angle, radius, active_edges)
            travel = min(radius * 0.82, hit_distance - 0.12)
            if travel < radius * 0.24:
                continue
            point = (origin[0] + travel * math.cos(angle),
                     origin[1] + travel * math.sin(angle))
            if region.covers(ShapePoint(point)) and segment_in_region(region, origin, point):
                candidates.append(point)
        # Neighboring rays that hit the same polygon edge expose only that
        # visible edge fragment; no hidden polygon vertices leave the sensor.
        observed_edges = []
        run_start = run_end = run_id = None
        for index, (left, right) in enumerate(zip(samples, samples[1:] + samples[:1])):
            identity = left[3] if valid_wedges[index] and left[3] is not None and left[3] == right[3] else None
            if identity != run_id or (run_end is not None and distance(run_end, left[1]) > 1e-4):
                if run_start is not None and distance(run_start, run_end) > 1e-4:
                    observed_edges.append((run_start, run_end))
                run_start = run_end = run_id = None
            if identity is not None:
                if run_start is None:
                    run_start = left[1]
                run_end, run_id = right[1], identity
        if run_start is not None and distance(run_start, run_end) > 1e-4:
            observed_edges.append((run_start, run_end))
        return SensorObservation(region, tuple(candidates), tuple(observed_edges))
