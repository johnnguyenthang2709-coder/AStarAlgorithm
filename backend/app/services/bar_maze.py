"""Seeded polygon-wall mazes for the continuous point-robot simulator.

The lattice chooses wall openings only. Robot poses, sensing, collision checks,
and A* visibility edges remain continuous geometry.
"""

import random
from dataclasses import dataclass

from app.services.bar_continuous_geometry import ContinuousWorld, Point

Cell = tuple[int, int]
Link = tuple[Cell, Cell]


def canonical(a: Cell, b: Cell) -> Link:
    return (a, b) if a < b else (b, a)


@dataclass(frozen=True)
class MazeConfig:
    seed: int = 17
    size: int = 5
    corridor_width: float = 2.8
    loop_rate: float = 0.08
    dead_end_rate: float = 0.45
    trap_count: int = 2
    difficulty: str = "normal"
    start_cell: Cell | None = None
    goal_cell: Cell | None = None

    def validate(self) -> None:
        if not 0 <= self.seed <= 2**31 - 1 or not 4 <= self.size <= 8:
            raise ValueError("maze seed or size outside supported range")
        if not 1.2 <= self.corridor_width <= 4.2:
            raise ValueError("corridor width must be 1.2–4.2 world units")
        if not 0 <= self.loop_rate <= 0.35 or not 0 <= self.dead_end_rate <= 1:
            raise ValueError("maze loop/dead-end rates must be in supported range")
        if not 1 <= self.trap_count <= 8 or self.difficulty not in ("easy", "normal", "hard"):
            raise ValueError("invalid maze trap count or difficulty")
        if (self.start_cell is None) != (self.goal_cell is None):
            raise ValueError("supply both start and goal rooms, or neither")
        for cell in (self.start_cell, self.goal_cell):
            if cell is not None and (len(cell) != 2 or any(not isinstance(v, int) or not 0 <= v < self.size for v in cell)):
                raise ValueError("start/goal room outside maze")
        if self.start_cell is not None and self.goal_cell is not None:
            if sum(abs(a-b) for a, b in zip(self.start_cell, self.goal_cell)) < self.size:
                raise ValueError("start and goal rooms must be meaningfully separated")


@dataclass(frozen=True)
class MazeLayout:
    config: MazeConfig
    world: ContinuousWorld
    open_links: frozenset[Link]
    start_cell: Cell
    goal_cell: Cell
    dead_ends: tuple[Cell, ...]
    loop_count: int


def _neighbors(cell: Cell, size: int) -> list[Cell]:
    row, col = cell
    return [(r, c) for r, c in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
            if 0 <= r < size and 0 <= c < size]


def _rect(x0: float, y0: float, x1: float, y1: float) -> tuple[Point, ...]:
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def generate_maze(config: MazeConfig) -> MazeLayout:
    config.validate()
    rng = random.Random(config.seed)
    size, pitch, thickness = config.size, 5.0, 0.36
    cells = [(r, c) for r in range(size) for c in range(size)]
    # Randomized depth-first spanning tree: connected and rich in terminal branches.
    visited = {(0, 0)}
    stack = [(0, 0)]
    opened: set[Link] = set()
    while stack:
        options = [cell for cell in _neighbors(stack[-1], size) if cell not in visited]
        if not options:
            stack.pop()
            continue
        target = rng.choice(options)
        opened.add(canonical(stack[-1], target))
        visited.add(target)
        stack.append(target)

    all_links = {canonical(cell, other) for cell in cells for other in _neighbors(cell, size)}
    tree_links = set(opened)
    closed = sorted(all_links - opened)
    rng.shuffle(closed)
    loop_count = 0
    effective_loop_rate = min(0.35, max(0.0, config.loop_rate +
                                       {"easy": 0.08, "normal": 0.0, "hard": -0.05}[config.difficulty]))
    for link in closed:
        if rng.random() >= effective_loop_rate:
            continue
        degrees = {cell: sum(cell in edge for edge in opened) for cell in link}
        # Preserve designated cul-de-sacs instead of erasing every dead end.
        if 1 in degrees.values() and rng.random() < config.dead_end_rate:
            continue
        opened.add(link)
        loop_count += 1

    if config.loop_rate > 0 and loop_count == 0:
        for link in closed:
            degrees = {cell: sum(cell in edge for edge in opened) for cell in link}
            if 1 not in degrees.values():
                opened.add(link)
                loop_count = 1
                break

    dead_ends = tuple(cell for cell in cells if sum(cell in edge for edge in opened) == 1)
    if len(dead_ends) < config.trap_count:
        # Remove only added loop links. A spanning tree always remains connected.
        for link in sorted(opened - tree_links):
            opened.remove(link)
            loop_count -= 1
            dead_ends = tuple(cell for cell in cells if sum(cell in edge for edge in opened) == 1)
            if len(dead_ends) >= config.trap_count:
                break
    if len(dead_ends) < config.trap_count:
        raise ValueError("requested trap count cannot be achieved for these parameters")
    if config.loop_rate > 0 and loop_count == 0:
        raise ValueError("a loop and the requested trap count cannot coexist")

    # Select graph-diameter endpoints; no navigation-policy success filtering.
    adjacency = {cell: [] for cell in cells}
    for a, b in opened:
        adjacency[a].append(b)
        adjacency[b].append(a)
    def distances(source: Cell) -> dict[Cell, int]:
        found = {source: 0}
        queue = [source]
        for cell in queue:
            for other in adjacency[cell]:
                if other not in found:
                    found[other] = found[cell] + 1
                    queue.append(other)
        return found
    separated = [(a, b) for a in cells for b in cells
                 if abs(a[0]-b[0]) + abs(a[1]-b[1]) >= size]
    start_cell, goal_cell = max(separated,
                                key=lambda pair: (distances(pair[0])[pair[1]],
                                                  abs(pair[0][0]-pair[1][0]) + abs(pair[0][1]-pair[1][1]), pair))
    if config.start_cell is not None and config.goal_cell is not None:
        start_cell, goal_cell = config.start_cell, config.goal_cell
    gap = config.corridor_width
    polygons: list[tuple[Point, ...]] = []
    # Walls stand on shared room boundaries. Open links get centered doors;
    # closed links get full wall slabs. Rectangles may touch/overlap safely.
    for row in range(size):
        for col in range(1, size):
            a, b = (row, col - 1), (row, col)
            x, y = col * pitch, row * pitch
            pieces = ((y, y + (pitch-gap)/2), (y + (pitch+gap)/2, y + pitch)) \
                if canonical(a, b) in opened else ((y, y + pitch),)
            polygons.extend(_rect(x-thickness/2, lo, x+thickness/2, hi)
                            for lo, hi in pieces)
    for row in range(1, size):
        for col in range(size):
            a, b = (row - 1, col), (row, col)
            y, x = row * pitch, col * pitch
            pieces = ((x, x + (pitch-gap)/2), (x + (pitch+gap)/2, x + pitch)) \
                if canonical(a, b) in opened else ((x, x + pitch),)
            polygons.extend(_rect(lo, y-thickness/2, hi, y+thickness/2)
                            for lo, hi in pieces)

    def center(cell: Cell) -> Point:
        return ((cell[1] + 0.5) * pitch, (cell[0] + 0.5) * pitch)

    world = ContinuousWorld((0., 0., size*pitch, size*pitch), tuple(polygons),
                            center(start_cell), center(goal_cell))
    for a, b in all_links:
        traversable = world.collision_free(center(a), center(b))
        if traversable != (canonical(a, b) in opened):
            raise AssertionError("maze wall topology differs from generated links")
    return MazeLayout(config, world, frozenset(opened), start_cell, goal_cell,
                      dead_ends, loop_count)


SHOWCASE = MazeConfig(seed=17, size=5, corridor_width=3.2, loop_rate=0.12,
                      dead_end_rate=0.7, trap_count=2, difficulty="easy")
HARD = MazeConfig(seed=431, size=7, corridor_width=2.3, loop_rate=0.09,
                  dead_end_rate=0.8, trap_count=4, difficulty="hard")
