"""Irregular polygon corridors on a seeded maze topology.

The lattice selects connectivity only. The robot never receives the lattice or
centerlines; it senses polygon walls and plans in continuous discovered space.
"""

import random
from dataclasses import dataclass

from shapely.geometry import LineString, Point as ShapePoint, Polygon, box
from shapely.ops import unary_union

from app.services.bar_continuous_geometry import ContinuousWorld, Point
from app.services.bar_maze import Cell, Link, MazeConfig, canonical, generate_maze

PITCH = 5.0


@dataclass(frozen=True)
class LabyrinthConfig(MazeConfig):
    irregularity: float = 0.65

    def validate(self) -> None:
        super().validate()
        if not 0 <= self.irregularity <= 1:
            raise ValueError("irregularity must be between 0 and 1")
        if self.corridor_width > 3.2:
            raise ValueError("labyrinth corridor width must not exceed 3.2 world units")


@dataclass(frozen=True)
class LabyrinthLayout:
    config: LabyrinthConfig
    world: ContinuousWorld
    open_links: frozenset[Link]
    centerlines: tuple[tuple[Point, ...], ...]
    centers: dict[Cell, Point]
    start_cell: Cell
    goal_cell: Cell
    dead_ends: tuple[Cell, ...]
    loop_count: int


def _polygons(geometry) -> tuple[Polygon, ...]:
    if isinstance(geometry, Polygon):
        return (geometry,)
    return tuple(part for part in geometry.geoms if isinstance(part, Polygon))


def generate_labyrinth(config: LabyrinthConfig) -> LabyrinthLayout:
    config.validate()
    # Reuse the validated spanning-tree-plus-loops topology and endpoint rule.
    # This also retains the exact legacy Maze 3 generator as a regression base.
    topology = generate_maze(config)
    rng = random.Random(config.seed ^ 0x6A09E667)
    size = config.size
    jitter = 0.42 * config.irregularity
    centers = {(row, col): ((col + .5) * PITCH + rng.uniform(-jitter, jitter),
                            (row + .5) * PITCH + rng.uniform(-jitter, jitter))
               for row in range(size) for col in range(size)}

    centerlines: list[tuple[Point, ...]] = []
    corridors = []
    for a, b in sorted(topology.open_links):
        origin, target = centers[a], centers[b]
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        length = (dx * dx + dy * dy) ** .5
        perpendicular = (-dy / length, dx / length)
        bend = rng.uniform(-.70, .70) * config.irregularity
        second_bend = bend * .65 + rng.uniform(-.13, .13) * config.irregularity
        path = (origin,
                (origin[0] + dx * .34 + perpendicular[0] * bend,
                 origin[1] + dy * .34 + perpendicular[1] * bend),
                (origin[0] + dx * .68 + perpendicular[0] * second_bend,
                 origin[1] + dy * .68 + perpendicular[1] * second_bend),
                target)
        centerlines.append(path)
        width = config.corridor_width * (1 + rng.uniform(-.10, .10) * config.irregularity)
        corridors.append(LineString(path).buffer(width / 2, quad_segs=2,
                                                  cap_style=1, join_style=1))

    walkable = unary_union(corridors)
    boundary = box(0, 0, size * PITCH, size * PITCH)
    walls = boundary.difference(walkable)
    if not walkable.is_valid or not walls.is_valid or len(_polygons(walkable)) != 1:
        raise ValueError("generated labyrinth has invalid or disconnected corridors")
    wall_polygons = _polygons(walls)
    if not wall_polygons:
        raise ValueError("generated labyrinth has no walls")
    world = ContinuousWorld(tuple(boundary.bounds), wall_polygons,
                            centers[topology.start_cell], centers[topology.goal_cell])

    for path in centerlines:
        if any(not world.collision_free(a, b) for a, b in zip(path, path[1:])):
            raise ValueError("generated corridor centerline lacks clearance")
    for row in range(size):
        for col in range(size):
            a = (row, col)
            for b in ((row + 1, col), (row, col + 1)):
                if b[0] >= size or b[1] >= size or canonical(a, b) in topology.open_links:
                    continue
                separator = (LineString((((col + 1) * PITCH, row * PITCH),
                                         ((col + 1) * PITCH, (row + 1) * PITCH)))
                             if b[1] != col else
                             LineString(((col * PITCH, (row + 1) * PITCH),
                                         ((col + 1) * PITCH, (row + 1) * PITCH))))
                if (world.collision_free(centers[a], centers[b]) or
                        world.free_space.intersection(separator).length > 1e-7):
                    raise ValueError("generated labyrinth has an accidental wall opening")
    if not all(world.free_space.contains(ShapePoint(point)) for point in (world.start, world.goal)):
        raise ValueError("generated start or goal is not free")
    return LabyrinthLayout(config, world, topology.open_links, tuple(centerlines),
                           centers, topology.start_cell, topology.goal_cell,
                           topology.dead_ends, topology.loop_count)


EXPLORATION = LabyrinthConfig(seed=17, size=5, corridor_width=2.65,
                              loop_rate=.12, dead_end_rate=.7, trap_count=2,
                              difficulty="easy", irregularity=.68)
BLIND_ALLEY = LabyrinthConfig(seed=23, size=5, corridor_width=2.4,
                              loop_rate=.09, dead_end_rate=.8, trap_count=3,
                              difficulty="hard", irregularity=.72)
COMPLEX = LabyrinthConfig(seed=2026, size=6, corridor_width=2.05,
                          loop_rate=.22, dead_end_rate=.6, trap_count=4,
                          difficulty="normal", irregularity=.88)
