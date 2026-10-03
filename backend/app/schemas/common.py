from typing import Literal
from pydantic import BaseModel, Field


Algorithm = Literal["astar", "dijkstra"]


class Coordinate(BaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(ge=-180, le=180, description="Longitude in decimal degrees")


class GridCell(BaseModel):
    row: int = Field(ge=0)
    col: int = Field(ge=0)


class SearchMetrics(BaseModel):
    expanded_nodes: int = Field(description="Valid OPEN pops, including re-expansions and goal")
    unique_expanded_states: int
    generated_nodes: int = Field(description="Total OPEN pushes, including start")
    unique_discovered_states: int
    relaxed_edges: int = Field(description="Outgoing edges that improved a state")
    examined_edges: int = Field(description="All outgoing edges examined")


class SearchTraceEvent(BaseModel):
    type: Literal["DISCOVER", "EXPAND", "UPDATE", "CLOSE", "GOAL_FOUND"]
    state: int | GridCell
    parent: int | GridCell | None
    g: float
    h: float
    f: float
