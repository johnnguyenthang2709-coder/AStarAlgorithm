"""Limited-sensing grid exploration using the existing C++ A* binding."""

from collections import deque
from time import perf_counter

import astar_core

from app.services.bar_sensing import FREE, UNKNOWN, cardinal, sense

Cell = tuple[int, int]


def as_cell(cell: Cell) -> dict[str, int]:
    return {"row": cell[0], "col": cell[1]}


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class BarController:
    """Navigation policy. It never accepts or reads evaluation gate metadata."""

    def __init__(self, rows: tuple[str, ...], start: Cell, goal: Cell, radius: float):
        if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("invalid scenario grid")
        if radius < 1:
            raise ValueError("sensor radius must be at least one cell")
        self.rows = rows  # accessed only by sense() and the movement assertion
        self.goal = goal
        self.current = start
        self.radius = radius
        self.height, self.width = len(rows), len(rows[0])
        self.known = [[UNKNOWN] * self.width for _ in rows]
        self.frames: list[dict] = []
        self.history: list[Cell] = [start]
        self.expanded_nodes = 0
        self.replans = 0
        self.planning_ms = 0.0
        self.turns = 0
        self.last_heading: Cell | None = None
        self.exhausted: dict[Cell, int] = {}
        self.revision = 0
        self.recoveries: list[dict] = []

    def observe(self) -> list[tuple[Cell, int]]:
        changes = sense(self.rows, self.known, self.current, self.radius)
        if changes:
            self.revision += 1
        self.frames.append({"event": "sense", "position": as_cell(self.current),
                            "changes": [{"cell": as_cell(cell), "state": value} for cell, value in changes]})
        return changes

    def planning_grid(self) -> list[list[int]]:
        return [[0 if cell == FREE else 1 for cell in row] for row in self.known]

    def plan(self, target: Cell, grid: list[list[int]]) -> dict:
        start = perf_counter()
        result = astar_core.grid_search(grid, self.current, target, 4, "astar", False)
        self.planning_ms += (perf_counter() - start) * 1000
        self.replans += 1
        self.expanded_nodes += result["metrics"]["expanded_nodes"]
        return result

    def frontiers(self) -> list[Cell]:
        return [(r, c) for r in range(self.height) for c in range(self.width)
                if self.known[r][c] == FREE and self.exhausted.get((r, c)) != self.revision
                and any(self.known[y][x] == UNKNOWN for y, x in cardinal((r, c), self.height, self.width))]

    def choose_target(self) -> tuple[Cell, dict] | None:
        grid = self.planning_grid()
        if self.known[self.goal[0]][self.goal[1]] == FREE:
            route = self.plan(self.goal, grid)
            if route["found"]:
                return self.goal, route
        # Unit cardinal costs let one breadth-first pass score every frontier.
        # C++ A* still plans the actual route to the selected target.
        distances = {self.current: 0}
        pending = deque([self.current])
        while pending:
            cell = pending.popleft()
            for neighbor in cardinal(cell, self.height, self.width):
                if self.known[neighbor[0]][neighbor[1]] == FREE and neighbor not in distances:
                    distances[neighbor] = distances[cell] + 1
                    pending.append(neighbor)
        best: tuple[tuple[float, int, int, int], Cell] | None = None
        for target in self.frontiers():
            if target == self.current:
                self.exhausted[target] = self.revision
                continue
            if target not in distances:
                continue
            rank = (distances[target] + 0.75 * manhattan(target, self.goal),
                    distances[target], target[0], target[1])
            if best is None or rank < best[0]:
                best = rank, target
        if best is None:
            return None
        route = self.plan(best[1], grid)
        if not route["found"] or route["cost"] != distances[best[1]]:
            raise AssertionError("frontier distance and C++ A* disagree")
        return best[1], route

    def exhausted_branch(self) -> tuple[Cell, list[Cell]] | None:
        """Find a known bridge enclosing no active frontier, using only known map/history."""
        active = set(self.frontiers())
        start = self.history[0]
        discovered = {start: 0}
        low = {start: 0}
        parent: dict[Cell, Cell] = {}
        frontier_count = {start: int(start in active)}
        bridges: set[frozenset[Cell]] = set()
        stack = [(start, iter(cardinal(start, self.height, self.width)))]
        while stack:
            cell, neighbors = stack[-1]
            neighbor = next(neighbors, None)
            if neighbor is None:
                stack.pop()
                if cell in parent:
                    prior = parent[cell]
                    if low[cell] > discovered[prior] and frontier_count[cell] == 0:
                        bridges.add(frozenset((prior, cell)))
                    low[prior] = min(low[prior], low[cell])
                    frontier_count[prior] += frontier_count[cell]
                continue
            if self.known[neighbor[0]][neighbor[1]] != FREE:
                continue
            if neighbor not in discovered:
                parent[neighbor] = cell
                discovered[neighbor] = low[neighbor] = len(discovered)
                frontier_count[neighbor] = int(neighbor in active)
                stack.append((neighbor, iter(cardinal(neighbor, self.height, self.width))))
            elif parent.get(cell) != neighbor:
                low[cell] = min(low[cell], discovered[neighbor])
        # A bridge qualifies only when its frontier-free child side contains
        # the current robot. Walk its DFS ancestry, then find the real entry.
        current_side: set[frozenset[Cell]] = set()
        cell = self.current
        while cell in parent:
            current_side.add(frozenset((parent[cell], cell)))
            cell = parent[cell]
        last_crossing = {(a, b): i for i, (a, b) in enumerate(zip(self.history, self.history[1:]))}
        checked: set[frozenset[Cell]] = set()
        for a, b in zip(self.history, self.history[1:]):
            edge = frozenset((a, b))
            if edge in checked:
                continue
            checked.add(edge)
            if edge not in bridges or edge not in current_side:
                continue
            outside, inside = (a, b) if parent.get(b) == a else (b, a)
            index = last_crossing.get((outside, inside))
            if index is None:
                continue
            entry = self.history[index:].copy()
            if entry[0] == outside and entry[-1] == self.current:
                return outside, entry
        return None

    def recover(self, anchor: Cell, entry: list[Cell]) -> None:
        entry_length = len(entry) - 1
        result = self.plan(anchor, self.planning_grid())
        proposed = [(cell["row"], cell["col"]) for cell in result["path"]]
        valid = (result["found"] and bool(proposed) and len(proposed) - 1 <= entry_length
                 and proposed[0] == self.current and proposed[-1] == anchor)
        if valid:
            valid = all(manhattan(a, b) == 1 and self.known[b[0]][b[1]] == FREE
                        for a, b in zip(proposed, proposed[1:]))
        fallback = not valid
        route = proposed if valid else list(reversed(entry))
        self.frames.append({"event": "recover_start", "position": as_cell(self.current),
                            "anchor": as_cell(anchor), "entry_path": [as_cell(c) for c in entry],
                            "path": [as_cell(c) for c in route], "fallback": fallback})
        before = len(self.history) - 1
        for cell in route[1:]:
            self.move(cell, "retreat")
            self.observe()  # observations do not interrupt the locked retreat
        retreat_length = len(self.history) - 1 - before
        verified = self.current == anchor and retreat_length <= entry_length + 1e-9
        record = {"anchor": as_cell(anchor), "entry_length": entry_length,
                  "retreat_length": retreat_length,
                  "retreat_ratio": retreat_length / entry_length if entry_length else None,
                  "fallback": fallback, "invariant_verified": verified}
        self.recoveries.append(record)
        self.frames.append({"event": "recover_end", "position": as_cell(self.current), **record})
        if not verified:
            raise AssertionError("BAR executed retreat invariant failed")

    def move(self, next_cell: Cell, phase: str = "explore") -> None:
        if manhattan(self.current, next_cell) != 1 or self.known[next_cell[0]][next_cell[1]] != FREE:
            raise AssertionError("controller attempted an unverified move")
        if self.rows[next_cell[0]][next_cell[1]] != ".":
            raise AssertionError("collision despite verified map")
        heading = (next_cell[0] - self.current[0], next_cell[1] - self.current[1])
        if self.last_heading is not None and heading != self.last_heading:
            self.turns += 1
        self.last_heading = heading
        self.current = next_cell
        self.history.append(next_cell)
        self.frames.append({"event": "move", "phase": phase, "position": as_cell(next_cell)})

    def finish(self, status: str) -> dict:
        self.frames.append({"event": "finish", "status": status, "position": as_cell(self.current)})
        return {"status": status, "success": status == "goal_reached", "frames": self.frames,
                "recoveries": self.recoveries,
                "metrics": {"executed_distance": len(self.history) - 1, "turn_count": self.turns,
                            "astar_expanded_nodes": self.expanded_nodes,
                            "replanning_count": self.replans,
                            "planning_time_ms": round(self.planning_ms, 3)}}

    def run(self) -> dict:
        limit = 10 * self.height * self.width * self.height * self.width
        for _ in range(limit):
            changes = self.observe()
            if self.current == self.goal:
                return self.finish("goal_reached")
            if not changes:
                self.exhausted[self.current] = self.revision
            choice = self.choose_target()
            if choice is None or choice[0] != self.goal:
                branch = self.exhausted_branch()
                if branch is not None:
                    self.recover(*branch)
                    continue
            if choice is None:
                return self.finish("no_reachable_frontier")
            target, route = choice
            self.frames.append({"event": "plan", "position": as_cell(self.current),
                                "target": as_cell(target), "path": route["path"]})
            if len(route["path"]) < 2:
                self.exhausted[target] = self.revision
                continue
            next_cell = route["path"][1]
            self.move((next_cell["row"], next_cell["col"]))
        return self.finish("step_limit")
