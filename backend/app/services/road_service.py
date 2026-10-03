import astar_core
from app.schemas.common import Coordinate
from app.schemas.road import RoadCompareRequest, RoadSearchRequest


def snap(engine: astar_core.RoadEngine, point: Coordinate) -> dict:
    return astar_core.road_edge_snap(engine, point.lat, point.lon)


def nodes(engine: astar_core.RoadEngine) -> list[dict]:
    return astar_core.road_nodes(engine)


def _matches(result: dict, start: Coordinate, goal: Coordinate) -> dict:
    start_snap = result.pop("start_snap")
    goal_snap = result.pop("goal_snap")
    return {**result,
            "start": {"requested": start, "snapped": start_snap},
            "goal": {"requested": goal, "snapped": goal_snap}}


def search(engine: astar_core.RoadEngine, request: RoadSearchRequest) -> dict:
    result = astar_core.road_search_coordinates(
        engine, (request.start.lat, request.start.lon),
        (request.goal.lat, request.goal.lon), request.algorithm, request.trace)
    return _matches(result, request.start, request.goal)


def compare(engine: astar_core.RoadEngine, request: RoadCompareRequest) -> dict:
    result = astar_core.road_compare_coordinates(
        engine, (request.start.lat, request.start.lon),
        (request.goal.lat, request.goal.lon), request.trace)
    return _matches(result, request.start, request.goal)
