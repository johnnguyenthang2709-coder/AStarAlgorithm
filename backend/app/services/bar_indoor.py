"""Seeded indoor polygon worlds. Layout metadata stays in the simulator/tests.

The navigation policy receives only ContinuousWorld.sense observations. Rooms
are deliberately nonuniform; an observed exploration anchor is not asserted
to be a recognized architectural room.
"""

import random
from dataclasses import dataclass

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from app.services.bar_continuous_geometry import ContinuousWorld, Point


@dataclass(frozen=True)
class IndoorConfig:
    layout: str = "apartment"
    seed: int = 41

    def validate(self) -> None:
        if self.layout not in ("apartment", "office", "challenge"):
            raise ValueError("unknown indoor layout")
        if not 0 <= self.seed <= 2**31 - 1:
            raise ValueError("indoor seed outside supported range")


@dataclass(frozen=True)
class Room:
    name: str
    bounds: tuple[float, float, float, float]
    kind: str


@dataclass(frozen=True)
class Door:
    room: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class IndoorLayout:
    config: IndoorConfig
    world: ContinuousWorld
    rooms: tuple[Room, ...]
    doors: tuple[Door, ...]
    corridor_bounds: tuple[tuple[float, float, float, float], ...]
    furniture: tuple[Polygon, ...]


def _parts(shape) -> tuple[Polygon, ...]:
    if isinstance(shape, Polygon):
        return (shape,)
    return tuple(part for part in shape.geoms if isinstance(part, Polygon) and part.area > 1e-8)


def _spec(layout: str) -> tuple[tuple[float, float, float, float], tuple[Room, ...],
                                tuple[tuple[float, float, float, float], ...],
                                tuple[tuple[str, str, float], ...], str, str]:
    """Door tuple: room name, side facing a corridor, coordinate along wall."""
    if layout == "apartment":
        bounds = (0., 0., 64., 48.)
        rooms = (Room("living", (4, 28, 19, 43), "living"),
                 Room("kitchen", (21, 28, 34, 40), "kitchen"),
                 Room("study", (36, 28, 44, 43), "office"),
                 Room("guest", (50, 28, 60, 41), "living"),
                 Room("bedroom", (4, 6, 17, 20), "living"),
                 Room("bath", (20, 10, 31, 20), "sparse"),
                 Room("storage", (33, 7, 44, 20), "storage"),
                 Room("utility", (50, 7, 60, 20), "office"))
        halls = ((4, 22, 60, 26), (45, 8, 49, 41))
        doors = tuple((room.name, "south" if room.bounds[1] > 26 else "north",
                       (room.bounds[0] + room.bounds[2]) / 2) for room in rooms)
        doors += (("study", "east", 35.), ("utility", "west", 13.))
        return bounds, rooms, halls, doors, "living", "storage"
    if layout == "office":
        bounds = (0., 0., 78., 54.)
        rooms = (Room("lobby", (3, 31, 18, 49), "living"),
                 Room("meeting", (20, 31, 36, 49), "office"),
                 Room("records", (38, 31, 53, 47), "storage"),
                 Room("studio", (60, 31, 74, 49), "office"),
                 Room("lab", (3, 5, 19, 24), "office"),
                 Room("copy", (21, 8, 35, 24), "storage"),
                 Room("break", (38, 5, 53, 24), "living"),
                 Room("archive", (60, 5, 74, 24), "storage"))
        halls = ((3, 26, 74, 29), (55, 7, 58, 48))
        doors = tuple((room.name, "south" if room.bounds[1] > 29 else "north",
                       (room.bounds[0] + room.bounds[2]) / 2) for room in rooms)
        doors += (("records", "east", 39.), ("break", "east", 15.),
                  ("studio", "west", 39.), ("archive", "west", 15.))
        return bounds, rooms, halls, doors, "lobby", "archive"
    bounds = (0., 0., 82., 58.)
    rooms = (Room("entry", (3, 35, 17, 53), "living"),
             Room("workshop", (19, 35, 38, 54), "partition"),
             Room("upper_store", (40, 35, 56, 53), "storage"),
             Room("east_lab", (63, 34, 78, 54), "partition"),
             Room("west_store", (3, 5, 18, 27), "storage"),
             Room("machine", (20, 6, 37, 27), "partition"),
             Room("office", (40, 5, 56, 27), "office"),
             Room("deep_store", (63, 5, 78, 27), "storage"))
    halls = ((3, 29, 78, 32), (58, 7, 61, 51), (10, 29, 13, 35))
    doors = tuple((room.name, "south" if room.bounds[1] > 32 else "north",
                   (room.bounds[0] + room.bounds[2]) / 2) for room in rooms)
    doors += (("upper_store", "east", 45.), ("office", "east", 15.),
              ("east_lab", "west", 44.), ("deep_store", "west", 16.))
    return bounds, rooms, halls, doors, "entry", "deep_store"


def _door(room: Room, side: str, coordinate: float, jitter: float) -> Door:
    x0, y0, x1, y1 = room.bounds
    width = 2.15 if room.kind != "storage" else 1.8
    center = coordinate + jitter
    if side == "south":
        return Door(room.name, (center - width/2, y0 - 3.2, center + width/2, y0 + .15))
    if side == "north":
        return Door(room.name, (center - width/2, y1 - .15, center + width/2, y1 + 2.2))
    if side == "east":
        return Door(room.name, (x1 - .15, center - width/2, x1 + 2.2, center + width/2))
    return Door(room.name, (x0 - 2.2, center - width/2, x0 + .15, center + width/2))


def _furniture(room: Room, rng: random.Random) -> list[Polygon]:
    x0, y0, x1, y1 = room.bounds
    dx, dy = rng.uniform(-.35, .35), rng.uniform(-.35, .35)
    center = (x0 + x1)/2
    if room.kind == "sparse":
        return [box(x0 + 1.4, y1 - 2.0, x0 + 3.5, y1 - 1.1)]
    if room.kind == "storage":
        # Offset shelf ends alternate, so the room contains genuine interior
        # branches without sealing the route through its doorway.
        return [box(x0 + 2.0 + i*2.6, y0 + (2.0 if i % 2 else 4.0),
                    x0 + 2.65 + i*2.6, y1 - (1.5 if i % 2 else 3.0))
                for i in range(max(2, int((x1-x0-4)/2.6)))]
    if room.kind == "partition":
        return [box(center - .28, y0 + 2.0, center + .28, y1 - 3.5),
                box(x0 + 2., y0 + 3., x0 + 3.7, y0 + 4.)]
    if room.kind == "office":
        return [box(center - 1.25 + dx, y0 + (y1-y0)*.56 + dy,
                    center + 1.25 + dx, y0 + (y1-y0)*.56 + 1.1 + dy),
                box(x1 - 2.6, y1 - 2.0, x1 - 1.0, y1 - 1.0)]
    if room.kind == "kitchen":
        return [box(x0 + 1., y1 - 2.1, x1 - 1., y1 - 1.2),
                box(center - 1.2 + dx, y0 + 3 + dy, center + 1.2 + dx, y0 + 4 + dy)]
    return [box(center - 1.4 + dx, y0 + (y1-y0)*.57 + dy,
                center + 1.4 + dx, y0 + (y1-y0)*.57 + 1.0 + dy),
            box(x0 + 1.0, y1 - 2.0, x0 + 3.4, y1 - 1.1)]


def generate_indoor(config: IndoorConfig) -> IndoorLayout:
    config.validate()
    rng = random.Random(config.seed)
    bounds, rooms, halls, door_specs, start_room, goal_room = _spec(config.layout)
    by_name = {room.name: room for room in rooms}
    doors = tuple(_door(by_name[name], side, coordinate, rng.uniform(-.35, .35))
                  for name, side, coordinate in door_specs)
    furniture = tuple(shape for room in rooms for shape in _furniture(room, rng))
    footprint = unary_union([box(*room.bounds) for room in rooms] +
                            [box(*hall) for hall in halls] +
                            [box(*door.bounds) for door in doors])
    border = box(*bounds)
    free = footprint.difference(unary_union(furniture))
    if not free.is_valid or free.geom_type != "Polygon":
        raise ValueError("indoor floor plan is disconnected or invalid")
    walls = border.difference(free)
    def anchor(name: str) -> Point:
        x0, y0, x1, y1 = by_name[name].bounds
        return x0 + 1.5, y0 + 1.5
    world = ContinuousWorld(bounds, _parts(walls), anchor(start_room), anchor(goal_room))
    if any(not free.covers(box(*door.bounds)) for door in doors):
        raise ValueError("indoor doorway obstructed")
    return IndoorLayout(config, world, rooms, doors, halls, furniture)


APARTMENT = IndoorConfig("apartment", 41)
OFFICE = IndoorConfig("office", 73)
CHALLENGE = IndoorConfig("challenge", 211)
