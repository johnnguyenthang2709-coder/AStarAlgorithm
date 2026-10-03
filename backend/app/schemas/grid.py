from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .common import Algorithm, GridCell, SearchMetrics, SearchTraceEvent


GridValue = Literal[0, 1]


def validate_raw_cells(value):
    if not isinstance(value, list):
        return value
    for row in value:
        if not isinstance(row, list):
            continue
        if any(type(cell) is not int or cell not in (0, 1) for cell in row):
            raise ValueError("grid values must be integers 0 or 1")
    return value


def validate_grid(grid: list[list[GridValue]], start: GridCell,
                  goal: GridCell) -> None:
    if not grid or not grid[0]:
        raise ValueError("grid must be nonempty")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("grid rows must have equal length")
    for label, cell in (("start", start), ("goal", goal)):
        if cell.row >= len(grid) or cell.col >= width:
            raise ValueError(f"{label} cell is outside grid")
        if grid[cell.row][cell.col] == 1:
            raise ValueError(f"{label} cell is blocked")


class GridSearchRequest(BaseModel):
    grid: list[list[GridValue]] = Field(description="0 = traversable, 1 = blocked")
    start: GridCell
    goal: GridCell
    movement: Literal[4, 8] = 8
    algorithm: Algorithm = "astar"
    trace: bool = False

    @field_validator("grid", mode="before")
    @classmethod
    def check_cell_values(cls, value):
        return validate_raw_cells(value)

    @model_validator(mode="after")
    def check_grid(self):
        validate_grid(self.grid, self.start, self.goal)
        return self


class GridReplanRequest(BaseModel):
    grid: list[list[GridValue]] = Field(description="0 = traversable, 1 = blocked")
    current: GridCell
    goal: GridCell
    new_obstacles: list[GridCell]
    movement: Literal[4, 8] = 8
    algorithm: Algorithm = "astar"
    trace: bool = False

    @field_validator("grid", mode="before")
    @classmethod
    def check_cell_values(cls, value):
        return validate_raw_cells(value)

    @model_validator(mode="after")
    def check_grid(self):
        validate_grid(self.grid, self.current, self.goal)
        for obstacle in self.new_obstacles:
            if obstacle.row >= len(self.grid) or obstacle.col >= len(self.grid[0]):
                raise ValueError("new obstacle is outside grid")
            if obstacle == self.current or obstacle == self.goal:
                raise ValueError("new obstacle cannot block current or goal")
        return self


class GridSearchResponse(BaseModel):
    found: bool
    cost: float | None
    path: list[GridCell]
    metrics: SearchMetrics
    trace: list[SearchTraceEvent]
