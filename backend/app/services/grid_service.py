import astar_core
from app.schemas.grid import GridReplanRequest, GridSearchRequest


def search(request: GridSearchRequest) -> dict:
    return astar_core.grid_search(
        request.grid,
        (request.start.row, request.start.col),
        (request.goal.row, request.goal.col),
        request.movement,
        request.algorithm,
        request.trace,
    )


def replan(request: GridReplanRequest) -> dict:
    updated = [row.copy() for row in request.grid]
    for obstacle in request.new_obstacles:
        updated[obstacle.row][obstacle.col] = 1
    ordinary_request = GridSearchRequest(
        grid=updated, start=request.current, goal=request.goal,
        movement=request.movement, algorithm=request.algorithm, trace=request.trace,
    )
    return search(ordinary_request)
