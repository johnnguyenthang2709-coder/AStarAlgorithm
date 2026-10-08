"""Online arbitrary-angle navigation with C++ A* on certified visibility edges."""

import math
from dataclasses import dataclass, field
from time import perf_counter

import astar_core
from shapely.geometry import GeometryCollection, LineString, Point as ShapePoint, box
from shapely.prepared import prep

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
    branch_id: int = 0
    parent_id: int | None = None


class ContinuousPolicy:
    """Consumes certified observations only; it has no ground-truth reference."""

    def __init__(self, start: Point, goal: Point, bounds: tuple[float, float, float, float],
                 sensing_radius: float, prefer_novelty: bool = False,
                 include_graph: bool = False, trace_hierarchy: bool = False):
        if sensing_radius <= 0:
            raise ValueError("sensing radius must be positive")
        self.current, self.goal, self.bounds = start, goal, bounds
        self.border = box(*bounds)
        self.radius = sensing_radius
        self.prefer_novelty = prefer_novelty
        self.include_graph = include_graph
        self.trace_hierarchy = trace_hierarchy
        self.next_branch_id = 1
        self.heading = 0.0
        self.last_heading: float | None = None
        self.known_free = GeometryCollection()
        self.history: list[Point] = [start]
        self.scan_positions: list[Point] = [start]
        self.verified_links: set[tuple[Point, Point]] = set()
        self.stack = [ExploreNode(start, 0)]
        self.tried: set[Point] = set()
        self.deferred: dict[Point, tuple[float, int]] = {}
        self.goal_deferred_at: tuple[float, int] | None = None
        self.active_recovery_trigger = "exhausted_branch"
        self.frames: list[dict] = []
        self.recoveries: list[dict] = []
        self.executed = 0.0
        self.turns = 0
        self.planning_calls = 0
        self.expanded = 0
        self.planning_ms = 0.0
        self.max_nodes = 0
        self.max_edges = 0

    @staticmethod
    def candidate_key(point: Point) -> Point:
        return round(point[0], 3), round(point[1], 3)

    def graph_changed_since(self, marker: tuple[float, int] | None) -> bool:
        return (marker is None or self.known_free.area > marker[0] + 1e-6 or
                len(self.scan_positions) > marker[1])

    def observe(self, observation: SensorObservation, owner: ExploreNode | None = None) -> float:
        before = self.known_free.area
        self.known_free = self.known_free.union(observation.region)
        gained = max(0.0, self.known_free.area - before)
        if not any(distance(self.current, old) < 1e-7 for old in self.scan_positions):
            self.scan_positions.append(self.current)
        node = owner if owner is not None else self.stack[-1]
        if gained >= 0.05:
            for candidate in observation.candidates:
                key = self.candidate_key(candidate)
                if key not in self.tried and all(distance(candidate, existing) >= 0.1 for existing in node.candidates):
                    node.candidates.append(candidate)
        self.frames.append({"event": "sense", "position": as_point(self.current),
                            "heading": self.heading, "region": observation.geojson(),
                            "obstacle_edges": [[as_point(a), as_point(b)] for a, b in observation.edges],
                            "new_area": round(gained, 6),
                            **({"branch_id": node.branch_id} if self.trace_hierarchy else {})})
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
        return [candidate for candidate in node.candidates
                if self.graph_changed_since(self.deferred.get(self.candidate_key(candidate)))]

    def select(self) -> tuple[str, Point | ExploreNode] | None:
        if self.known_free.covers(ShapePoint(self.goal)) and self.graph_changed_since(self.goal_deferred_at):
            return "goal", self.goal
        current = self.stack[-1]
        choices = self.available(current)
        if choices:
            def priority(point: Point) -> tuple[float, float, float, float]:
                reachable_disk = ShapePoint(point).buffer(self.radius, quad_segs=12).intersection(self.border)
                novelty = reachable_disk.difference(self.known_free).area
                return (-novelty, distance(point, self.goal), point[0], point[1])
            target = min(choices, key=priority) if self.prefer_novelty else min(
                choices, key=lambda p: (distance(p, self.goal), distance(p, self.current), p[0], p[1]))
            current.candidates.remove(target)
            self.tried.add(self.candidate_key(target))
            return "explore", target
        for ancestor in reversed(self.stack[:-1]):
            if self.available(ancestor):
                return "recover", ancestor
        return None

    def failed_plan(self, action: str, target: Point, result: dict) -> None:
        """Defer a graph-unreachable target until new free space is observed."""
        self.plan_frame(target, result, action)
        self.frames[-1]["status"] = "unreachable_target"
        if action == "goal":
            self.goal_deferred_at = (self.known_free.area, len(self.scan_positions))
            return
        key = self.candidate_key(target)
        self.tried.discard(key)
        self.deferred[key] = (self.known_free.area, len(self.scan_positions))
        node = self.stack[-1]
        if all(distance(target, existing) >= 0.1 for existing in node.candidates):
            node.candidates.append(target)

    def complete_recovery(self, ancestor: ExploreNode) -> None:
        """Keep deferred targets from discarded children for later map growth."""
        index = self.stack.index(ancestor)
        for child in self.stack[index + 1:]:
            for candidate in child.candidates:
                if (self.candidate_key(candidate) in self.deferred and
                        all(distance(candidate, existing) >= 0.1 for existing in ancestor.candidates)):
                    ancestor.candidates.append(candidate)
        self.stack = self.stack[:index + 1]
        ancestor.history_index = len(self.history) - 1

    def enter_branch(self) -> None:
        parent = self.stack[-1]
        node = ExploreNode(self.current, len(self.history) - 1,
                           branch_id=self.next_branch_id, parent_id=parent.branch_id)
        self.next_branch_id += 1
        self.stack.append(node)
        if self.trace_hierarchy:
            self.frames.append({"event": "branch", "position": as_point(self.current),
                                "heading": self.heading, "status": "active",
                                "branch_id": node.branch_id, "parent_id": parent.branch_id,
                                "anchor": as_point(parent.position)})

    def leave_branches(self, ancestor: ExploreNode) -> None:
        if self.trace_hierarchy:
            for node in reversed(self.stack[self.stack.index(ancestor) + 1:]):
                blocked = any(self.candidate_key(candidate) in self.deferred
                              for candidate in node.candidates)
                self.frames.append({"event": "branch", "position": as_point(self.current),
                                    "heading": self.heading, "branch_id": node.branch_id,
                                    "parent_id": node.parent_id,
                                    "status": "temporarily_unavailable" if blocked else "exhausted",
                                    "anchor": as_point(ancestor.position)})

    def recovery_trigger(self, ancestor: ExploreNode) -> str:
        """A failed graph route is distinct from a branch with no useful frontier."""
        index = self.stack.index(ancestor)
        blocked = any(
            not self.graph_changed_since(self.deferred[self.candidate_key(candidate)])
            for node in self.stack[index + 1:]
            for candidate in node.candidates
            if self.candidate_key(candidate) in self.deferred
        )
        return "graph_blocked_target" if blocked else "exhausted_branch"

    def plan(self, target: Point) -> dict:
        points = list(dict.fromkeys(self.scan_positions + [self.current, target]))
        start, goal = points.index(self.current), points.index(target)
        prepared = prep(self.known_free)
        links = []
        for a in range(len(points)):
            for b in range(a + 1, len(points)):
                key = (points[a], points[b])
                if key in self.verified_links or prepared.covers(LineString(key)):
                    self.verified_links.add(key)
                    links.append((a, b))
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
        return {**result, "route": route, "nodes": len(points), "edges": len(links),
                "graph_points": points if self.include_graph else [],
                "graph_links": links if self.include_graph else []}

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
        frame = {"event": "plan", "position": as_point(self.current),
                            "heading": self.heading, "target": as_point(target),
                            "path": [as_point(point) for point in result["route"]],
                            "phase": phase, "graph_nodes": result["nodes"],
                            "graph_edges": result["edges"]}
        if self.include_graph:
            frame["graph_points"] = [as_point(point) for point in result["graph_points"]]
            frame["graph_links"] = result["graph_links"]
        self.frames.append(frame)

    def recovery_route(self, ancestor: ExploreNode) -> tuple[list[Point], bool, float]:
        self.active_recovery_trigger = self.recovery_trigger(ancestor)
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
        frame = {"event": "recover_start", "position": as_point(self.current),
                            "heading": self.heading, "anchor": as_point(ancestor.position),
                            "entry_path": [as_point(point) for point in entry],
                            "path": [as_point(point) for point in route],
                            "fallback": not valid, "entry_length": entry_length,
                            "trigger": self.active_recovery_trigger,
                            **({"branch_id": self.stack[-1].branch_id,
                                "parent_id": ancestor.branch_id} if self.trace_hierarchy else {})}
        if self.include_graph:
            frame["graph_points"] = [as_point(point) for point in result["graph_points"]]
            frame["graph_links"] = result["graph_links"]
        self.frames.append(frame)
        return route, not valid, entry_length

    def finish_recovery(self, ancestor: ExploreNode, fallback: bool,
                        entry_length: float, before: float) -> None:
        retreat_length = self.executed - before
        verified = (distance(self.current, ancestor.position) < 1e-6
                    and retreat_length <= entry_length + 1e-6)
        record = {"anchor": as_point(ancestor.position), "entry_length": entry_length,
                  "retreat_length": retreat_length,
                  "retreat_ratio": retreat_length / entry_length if entry_length else None,
                  "fallback": fallback, "invariant_verified": verified,
                  "trigger": self.active_recovery_trigger}
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
                            "max_graph_edges": self.max_edges,
                            **({"observed_free_area": round(self.known_free.area, 3),
                                "observed_branches": self.next_branch_id - 1}
                               if self.trace_hierarchy else {})}}


def simulate_continuous(world: ContinuousWorld, radius: float, limit: int = 250,
                        prefer_novelty: bool = False, include_graph: bool = False,
                        complete_frontier_route: bool = False,
                        trace_hierarchy: bool = False) -> dict:
    """Simulator orchestrates sensing and physical checks outside the policy."""
    policy = ContinuousPolicy(world.start, world.goal, world.bounds, radius,
                              prefer_novelty, include_graph, trace_hierarchy)

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
                policy.observe(world.sense(policy.current, radius), owner=ancestor)  # locked route
            policy.finish_recovery(ancestor, fallback, entry_length, before)
            policy.leave_branches(ancestor)
            policy.complete_recovery(ancestor)
            continue
        target = value
        result = policy.plan(target)
        if not result["found"] or len(result["route"]) < 2:
            policy.failed_plan(action, target, result)
            continue
        policy.plan_frame(target, result, action)
        if action == "goal":
            for waypoint in result["route"][1:]:
                checked_move(waypoint, "goal")
                policy.observe(world.sense(policy.current, radius))
            return policy.finish("goal_reached")
        # Maze mode reaches the selected frontier even when the constructed
        # graph needs intermediate waypoints. Fixed polygon baselines retain
        # their original one-waypoint episode protocol for comparability.
        waypoints = result["route"][1:] if complete_frontier_route else result["route"][1:2]
        for waypoint in waypoints:
            checked_move(waypoint, "explore")
        policy.enter_branch()
    return policy.finish("step_limit")
