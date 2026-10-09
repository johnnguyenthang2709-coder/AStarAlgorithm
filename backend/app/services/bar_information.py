"""Frontier opportunity estimated only from accumulated sensor observations.

Observed wall fragments remove blocked portions of the certified-free boundary.
Remaining visible boundary is a possible FREE/UNKNOWN frontier. Its length and
remaining sensor reach approximate how much newly visible area a viewpoint may
offer. This is a ranking estimate, never a physical sensor or proof of absence.
"""

from shapely.geometry import LineString, MultiLineString, Point as ShapePoint
from app.services.bar_continuous_geometry import Point, RAY_MARGIN, distance


def wall_key(a: Point, b: Point) -> tuple[Point, Point]:
    """Suppress identical observed fragments without merging different views."""
    endpoints = ((round(a[0], 4), round(a[1], 4)),
                 (round(b[0], 4), round(b[1], 4)))
    return tuple(sorted(endpoints))


def extend_wall_mask(mask, new_walls: list[tuple[Point, Point]]):
    """Union only newly sensed wall buffers; geometrically the full wall mask."""
    addition = MultiLineString(new_walls).buffer(2 * RAY_MARGIN)
    return mask.union(addition) if not mask.is_empty else addition


def possible_frontier(known_free, border, walls: list[tuple[Point, Point]], wall_mask=None):
    """FREE boundary minus observed walls; None requests a full reconstruction."""
    if known_free.is_empty:
        return known_free.boundary
    boundary = known_free.boundary
    tolerance = 2 * RAY_MARGIN  # sensor reports points 0.001 inside the wall
    if walls:
        mask = wall_mask if wall_mask is not None else MultiLineString(walls).buffer(tolerance)
        boundary = boundary.difference(mask)
    return boundary.difference(border.boundary.buffer(tolerance))


def visible_frontier_gain(point: Point, radius: float, prepared_free, frontier) -> float:
    """Approximate area beyond line-of-sight verified frontier pieces.

    For a visible segment of length L at midpoint distance d, a triangular
    continuation contributes L*(radius-d)/2. Unknown obstacles may shrink
    this area, so the value is not guaranteed sensor information gain.
    """
    if frontier.is_empty:
        return 0.0
    clipped = frontier.intersection(ShapePoint(point).buffer(radius, quad_segs=12))
    if clipped.is_empty:
        return 0.0
    pieces = [clipped] if clipped.geom_type == "LineString" else (
        list(clipped.geoms) if hasattr(clipped, "geoms") else [])
    total = 0.0
    for piece in pieces:
        if piece.geom_type != "LineString":
            continue
        coordinates = list(piece.coords)
        for a, b in zip(coordinates, coordinates[1:]):
            midpoint = ((a[0]+b[0])/2, (a[1]+b[1])/2)
            remaining = radius - distance(point, midpoint)
            if remaining > 0 and prepared_free.covers(LineString((point, midpoint))):
                total += distance(a, b) * remaining / 2
    return total
