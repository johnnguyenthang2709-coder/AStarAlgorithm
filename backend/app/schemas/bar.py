from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import GridCell


class BarRequest(BaseModel):
    scenario: Literal["alley_reachable", "alley_turn", "alley_shortcut", "wide_mouth_alley", "open_route", "unreachable", "expedition_narrow", "expedition_wide", "irregular_u", "irregular_bugtrap"]
    radius: int = Field(default=2, ge=1, le=10)


class BarChange(BaseModel):
    cell: GridCell
    state: Literal[0, 1]


class BarFrame(BaseModel):
    event: Literal["sense", "plan", "move", "recover_start", "recover_end", "finish"]
    position: GridCell
    changes: list[BarChange] = Field(default_factory=list)
    target: GridCell | None = None
    path: list[GridCell] = Field(default_factory=list)
    entry_path: list[GridCell] = Field(default_factory=list)
    anchor: GridCell | None = None
    phase: Literal["explore", "retreat"] | None = None
    fallback: bool | None = None
    status: str | None = None
    entry_length: int | None = None
    retreat_length: int | None = None
    retreat_ratio: float | None = None
    invariant_verified: bool | None = None


class BarRecovery(BaseModel):
    anchor: GridCell
    entry_length: int
    retreat_length: int
    retreat_ratio: float | None
    fallback: bool
    invariant_verified: bool


class BarMetrics(BaseModel):
    executed_distance: int
    turn_count: int
    astar_expanded_nodes: int
    replanning_count: int
    planning_time_ms: float
    gate_entry_length: int | None
    gate_retreat_length: int | None
    gate_retreat_ratio: float | None
    gate_bound_verified: bool | None
    gate_entries: int
    gate_exits: int
    bar_evaluation_status: Literal["no_gate", "no_entry", "entered_no_exit", "uncertified_exit", "certified", "bound_failed"]


class BarResponse(BaseModel):
    scenario: str
    map_kind: Literal["grid", "polygon_grid"]
    radius: int
    rows: int
    cols: int
    start: GridCell
    goal: GridCell
    status: str
    success: bool
    frames: list[BarFrame]
    recoveries: list[BarRecovery]
    metrics: BarMetrics


class ContinuousBarRequest(BaseModel):
    scenario: Literal["irregular_u", "irregular_bugtrap", "maze_showcase", "maze_hard", "maze_seeded"]
    radius: float = Field(default=6.0, ge=1.0, le=10.0)
    seed: int = Field(default=17, ge=0, le=2**31-1)
    size: int = Field(default=5, ge=4, le=8)
    corridor_width: float = Field(default=2.8, ge=1.2, le=4.2)
    loop_rate: float = Field(default=0.08, ge=0, le=0.35)
    dead_end_rate: float = Field(default=0.45, ge=0, le=1)
    trap_count: int = Field(default=2, ge=1, le=8)
    difficulty: Literal["easy", "normal", "hard"] = "normal"
    start_cell: tuple[int, int] | None = None
    goal_cell: tuple[int, int] | None = None
    debug_graph: bool = False


class ContinuousBarResponse(BaseModel):
    scenario: str
    mode: Literal["continuous"] = "continuous"
    radius: float
    sensor_fov_degrees: int = 360
    robot_radius: float = 0.0
    bounds: tuple[float, float, float, float]
    y_axis: Literal["up", "down"]
    start: dict[str, float]
    goal: dict[str, float]
    status: str
    success: bool
    frames: list[dict]
    recoveries: list[dict]
    metrics: dict
    maze_config: dict | None = None
