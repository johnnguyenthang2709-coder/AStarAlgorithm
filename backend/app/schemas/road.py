from typing import Literal
from pydantic import BaseModel, Field
from .common import Algorithm, Coordinate, SearchMetrics, SearchTraceEvent


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    road_graph_loaded: bool
    road_nodes: int
    road_edges: int


class RoadSnapResponse(Coordinate):
    node_id: int | None
    osm_id: int | None
    from_node: int
    to_node: int
    fraction: float
    snap_distance_m: float


class RoadNodePosition(Coordinate):
    node_id: int


class LocationMatch(BaseModel):
    requested: Coordinate
    snapped: RoadSnapResponse


class RoadEdgeResponse(BaseModel):
    from_node: int
    to_node: int
    length_m: float
    osm_key: str
    osmid: int | list[int] | str | None
    name: str


class RoadRouteResponse(BaseModel):
    cost_m: float
    node_path: list[int]
    edge_path: list[RoadEdgeResponse]
    geometry: list[Coordinate]


class RoadSearchRequest(BaseModel):
    start: Coordinate
    goal: Coordinate
    algorithm: Algorithm = Field(default="astar", description="C++ A* or Dijkstra")
    trace: bool = Field(default=False, description="Include algorithm events for later replay")


class RoadCompareRequest(BaseModel):
    start: Coordinate
    goal: Coordinate
    trace: bool = False


class RoadSearchResult(BaseModel):
    found: bool
    route: RoadRouteResponse | None
    metrics: SearchMetrics
    trace: list[SearchTraceEvent]
    trace_nodes: list[RoadNodePosition] = Field(default_factory=list)


class RoadSearchResponse(RoadSearchResult):
    start: LocationMatch
    goal: LocationMatch


class RoadCompareResponse(BaseModel):
    start: LocationMatch
    goal: LocationMatch
    same_optimal_cost: bool
    cost_difference_m: float | None
    astar: RoadSearchResult
    dijkstra: RoadSearchResult
