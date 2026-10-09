"""Point-robot visibility certificates from frozen upstream sight records.

No obstacle-map polygon is an input. A sight is its recorded center, radius,
and visible blocking line segments. Segment coverage is split at all circle,
radial-endpoint, and blocking-line events, then tested on each open interval.
"""

import math


EPS = 1e-9


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def point_visible(point, sight, radius):
    """Interior-only point visibility; contact at a known wall is allowed."""
    center = sight["center"]
    ray = subtract(point, center)
    if math.hypot(*ray) > radius + EPS:
        return False
    if math.hypot(*ray) < EPS:
        return True
    for closed in sight["closed_sights"]:
        a, b = closed[:2]
        edge = subtract(b, a)
        offset = subtract(a, center)
        denominator = cross(ray, edge)
        if abs(denominator) < 1e-12:
            continue
        ray_fraction = cross(offset, edge) / denominator
        wall_fraction = cross(offset, ray) / denominator
        if EPS < ray_fraction < 1 - EPS and -EPS <= wall_fraction <= 1 + EPS:
            return False
    return True


def _line_event(start, delta, line_origin, line_direction):
    denominator = cross(delta, line_direction)
    if abs(denominator) < 1e-12:
        return None
    return cross(subtract(line_origin, start), line_direction) / denominator


def _circle_events(start, delta, center, radius):
    offset = subtract(start, center)
    a = delta[0] * delta[0] + delta[1] * delta[1]
    if a < EPS * EPS:
        return []
    b = 2 * (offset[0] * delta[0] + offset[1] * delta[1])
    c = offset[0] * offset[0] + offset[1] * offset[1] - radius * radius
    discriminant = b * b - 4 * a * c
    if discriminant <= 0:
        return []
    root = math.sqrt(discriminant)
    return [(-b - root) / (2 * a), (-b + root) / (2 * a)]


def segment_certified(start, end, sights, radius):
    """Certify every open interval of a straight segment as observed free.

    Visibility can change only at a sight-circle boundary, an angular ray
    through a recorded blocker endpoint, or the blocker's support line.
    Returns the certificate and the number of tested intervals.
    """
    delta = subtract(end, start)
    events = [0.0, 1.0]
    for sight in sights:
        center = sight["center"]
        events.extend(_circle_events(start, delta, center, radius))
        for closed in sight["closed_sights"]:
            a, b = closed[:2]
            for origin, direction in ((center, subtract(a, center)),
                                      (center, subtract(b, center)),
                                      (a, subtract(b, a))):
                value = _line_event(start, delta, origin, direction)
                if value is not None:
                    events.append(value)
    ordered = sorted(min(1.0, max(0.0, t)) for t in events if -EPS <= t <= 1 + EPS)
    distinct = []
    for value in ordered:
        if not distinct or value - distinct[-1] > 1e-10:
            distinct.append(value)
    tested = 0
    for left, right in zip(distinct, distinct[1:]):
        if right - left <= 1e-10:
            continue
        t = (left + right) * 0.5
        point = (start[0] + t * delta[0], start[1] + t * delta[1])
        tested += 1
        if not any(point_visible(point, sight, radius) for sight in sights):
            return False, tested
    return (any(point_visible(start, sight, radius) for sight in sights)
            and any(point_visible(end, sight, radius) for sight in sights)), tested
