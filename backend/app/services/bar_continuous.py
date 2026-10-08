"""Online arbitrary-angle navigation with C++ A* on certified visibility edges."""

import math
from dataclasses import dataclass, field
from time import perf_counter

import astar_core
from shapely.geometry import GeometryCollection, Point as ShapePoint, box

from app.services.bar_continuous_geometry import (
    ContinuousWorld, Point, SensorObservation, as_point, distance, segment_in_region,
)


def path_length(points: list[Point]) -> float:
    return sum(distance(a, b) for a, b in zip(points, points[1:]))


@dataclass
class ExploreNode:
    position: Point
    history_index: int
    candidates: list[Point] = field(default_factory=list)


class ContinuousPolicy:
    """Consumes certified observations only; it has no ground-truth reference."""

    def __init__(self, start: Point, goal: Point, bounds: tuple[float, float, float, float],
                 sensing_radius: float):
        if sensing_radius <= 0:
            raise ValueError("sensing radius must be positive")
        self.current, self.goal, self.bounds = start, goal, bounds
        self.border = box(*bounds)
        self.radius = sensing_radius
        self.heading = 0.0
        self.last_heading: float | None = None
        self.known_free = GeometryCollection()
        self.history: list[Point] = [start]
        self.scan_positions: list[Point] = [start]
        self.stack = [ExploreNode(start, 0)]
        self.tried: set[Point] = set()
        self.frames: list[dict] = []
        self.recoveries: list[dict] = []
        self.executed = 0.0
        self.turns = 0
        self.planning_calls = 0
        self.expanded = 0
        self.planning_ms = 0.0
        self.max_nodes = 0
        self.max_edges = 0

    def observe(self, observation: SensorObservation) -> float:
        before = self.known_free.area
        self.known_free = self.known_free.union(observation.region)
        gained = max(0.0, self.known_free.area - before)
        if not any(distance(self.current, old) < 1e-7 for old in self.scan_positions):
            self.scan_positions.append(self.current)
        node = self.stack[-1]
        if gained >= 0.05:
            for candidate in observation.candidates:
                key = (round(candidate[0], 3), round(candidate[1], 3))
                if key not in self.tried and all(distance(candidate, existing) >= 0.1 for existing in node.candidates):
                    node.candidates.append(candidate)
        self.frames.append({"event": "sense", "position": as_point(self.current),
                            "heading": self.heading, "region": observation.geojson(),
                            "obstacle_edges": [[as_point(a), as_point(b)] for a, b in observation.edges],
                            "new_area": round(gained, 6)})
        return gained

    def _candidate_valid(self, candidate: Point) -> bool:
        if any(distance(candidate, old) < self.radius * 0.25 for old in self.scan_positions):
            return False
        if not self.known_free.covers(ShapePoint(candidate)):
            return False
        if self.known_free.boundary.distance(ShapePoint(candidate)) > self.radius * 0.55:
            return False
        potential = ShapePoint(candidate).buffer(self.radius, quad_segs=12).intersection(self.border)
        if potential.difference(self.known_free).area < 0.1:
            return False
        return True

    def available(self, node: ExploreNode) -> list[Point]:
        node.candidates = [candidate for candidate in node.candidates if self._candidate_valid(candidate)]
        return node.candidates

    def select(self) -> tuple[str, Point | ExploreNode] | None:
        if self.known_free.covers(ShapePoint(self.goal)):
            return "goal", self.goal
        current = self.stack[-1]
        choices = self.available(current)
        if choices:
            target = min(choices, key=lambda p: (distance(p, self.goal), distance(p, self.current), p[0], p[1]))
            current.candidates.remove(target)
            self.tried.add((round(target[0], 3), round(target[1], 3)))
            return "explore", target
        for ancestor in reversed(self.stack[:-1]):
            if self.available(ancestor):
                return "recover", ancestor
        return None

    def plan(self, target: Point) -> dict:
        points = list(dict.fromkeys(self.scan_positions + [self.current, target]))
        start, goal = points.index(self.current), points.index(target)
        links = [(a, b) for a in range(len(points)) for b in range(a + 1, len(points))
                 if segment_in_region(self.known_free, points[a], points[b])]
        self.max_nodes = max(self.max_nodes, len(points))
        self.max_edges = max(self.max_edges, len(links))
        begin = perf_counter()
        result = astar_core.visibility_search(points, links, start, goal, "astar")
        self.planning_ms += (perf_counter() - begin) * 1000
        self.planning_calls += 1
        self.expanded += result["metrics"]["expanded_nodes"]
        route = [points[index] for index in result["path"]]
        if result["found"] and abs(path_length(route) - result["cost"]) > 1e-6:
            raise AssertionError("Euclidean graph cost differs from route length")
        return {**result, "route": route, "nodes": len(points), "edges": len(links)}

    def move(self, destination: Point, phase: str) -> None:
        if distance(self.current, destination) < 1e-7 or not segment_in_region(self.known_free, self.current, destination):
            raise AssertionError("motion segment is not certified free")
        origin = self.current
        heading = math.atan2(destination[1] - origin[1], destination[0] - origin[0])
        if self.last_heading is not None and abs(math.atan2(math.sin(heading - self.last_heading),
                                                            math.cos(heading - self.last_heading))) > 1e-6:
            self.turns += 1
        self.last_heading = self.heading = heading
        length = distance(origin, destination)
        self.executed += length
        self.current = destination
        self.history.append(destination)
        self.frames.append({"event": "move", "from": as_point(origin),
                            "position": as_point(destination), "heading": heading,
                            "distance": length, "phase": phase})

    def plan_frame(self, target: Point, result: dict, phase: str) -> None:
        self.frames.append({"event": "plan", "position": as_point(self.current),
                            "heading": self.heading, "target": as_point(target),
                            "path": [as_point(point) for point in result["route"]],
                            "phase": phase, "graph_nodes": result["nodes"],
                            "graph_edges": result["edges"]})

    def recovery_route(self, ancestor: ExploreNode) -> tuple[list[Point], bool, float]:
        entry = self.history[ancestor.history_index:]
        entry_length = path_length(entry)
        result = self.plan(ancestor.position)
        proposed = result["route"]
        valid = (result["found"] and proposed and proposed[0] == self.current
                 and proposed[-1] == ancestor.position and path_length(proposed) <= entry_length + 1e-7
                 and all(segment_in_region(self.known_free, a, b) for a, b in zip(proposed, proposed[1:])))
        route = proposed if valid else list(reversed(entry))
        if not all(segment_in_region(self.known_free, a, b) for a, b in zip(route, route[1:])):
            raise AssertionError("recorded entry is no longer reversible")
        self.frames.append({"event": "recover_start", "position": as_point(self.current),
                            "heading": self.heading, "anchor": as_point(ancestor.position),
                            "entry_path": [as_point(point) for point in entry],
                            "path": [as_point(point) for point in route],
                            "fallback": not valid, "entry_length": entry_length})
        return route, not valid, entry_length

    def finish_recovery(self, ancestor: ExploreNode, fallback: bool,
                        entry_length: float, before: float) -> None:
        retreat_length = self.executed - before
        verified = (distance(self.current, ancestor.position) < 1e-6
                    and retreat_length <= entry_length + 1e-6)
        record = {"anchor": as_point(ancestor.position), "entry_length": entry_length,
                  "retreat_length": retreat_length,
                  "retreat_ratio": retreat_length / entry_length if entry_length else None,
                  "fallback": fallback, "invariant_verified": verified}
        self.recoveries.append(record)
        self.frames.append({"event": "recover_end", "position": as_point(self.current),
                            "heading": self.heading, **record})
        if not verified:
            raise AssertionError("executed continuous retreat bound failed")

    def finish(self, status: str) -> dict:
        self.frames.append({"event": "finish", "position": as_point(self.current),
                            "heading": self.heading, "status": status})
        return {"status": status, "success": status == "goal_reached",
                "frames": self.frames, "recoveries": self.recoveries,
                "metrics": {"executed_distance": self.executed,
                            "turn_count": self.turns,
                            "astar_expanded_nodes": self.expanded,
                            "replanning_count": self.planning_calls,
                            "planning_time_ms": round(self.planning_ms, 3),
                            "max_graph_nodes": self.max_nodes,
                            "max_graph_edges": self.max_edges}}


def simulate_continuous(world: ContinuousWorld, radius: float, limit: int = 250) -> dict:
    """Simulator orchestrates sensing and physical checks outside the policy."""
    policy = ContinuousPolicy(world.start, world.goal, world.bounds, radius)

    def checked_move(point: Point, phase: str) -> None:
        if not world.collision_free(policy.current, point):
            raise AssertionError("physical polygon collision")
        policy.move(point, phase)

    for _ in range(limit):
        policy.observe(world.sense(policy.current, radius))
        if distance(policy.current, world.goal) < 1e-6:
            return policy.finish("goal_reached")
        decision = policy.select()
        if decision is None:
            return policy.finish("no_reachable_frontier")
        action, value = decision
        if action == "recover":
            ancestor = value
            route, fallback, entry_length = policy.recovery_route(ancestor)
            before = policy.executed
            for waypoint in route[1:]:
                checked_move(waypoint, "retreat")
                policy.observe(world.sense(policy.current, radius))  # locked route
            policy.finish_recovery(ancestor, fallback, entry_length, before)
            policy.stack = policy.stack[:policy.stack.index(ancestor) + 1]
            ancestor.history_index = len(policy.history) - 1
            continue
        target = value
        result = policy.plan(target)
        if not result["found"] or len(result["route"]) < 2:
            continue
        policy.plan_frame(target, result, action)
        if action == "goal":
            for waypoint in result["route"][1:]:
                checked_move(waypoint, "goal")
                policy.observe(world.sense(policy.current, radius))
            return policy.finish("goal_reached")
        checked_move(result["route"][1], "explore")
        policy.stack.append(ExploreNode(policy.current, len(policy.history) - 1))
    return policy.finish("step_limit")
