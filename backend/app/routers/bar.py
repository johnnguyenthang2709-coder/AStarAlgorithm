from fastapi import APIRouter, HTTPException

from app.schemas.bar import BarRequest, BarResponse, ContinuousBarRequest, ContinuousBarResponse
from app.services.bar_evaluation import evaluate
from app.services.bar_continuous import simulate_continuous
from app.services.bar_continuous_geometry import ContinuousWorld, as_point
from app.services.bar_maze import MazeConfig, SHOWCASE, HARD, generate_maze
from app.services.bar_scenarios import load_scenario
from app.services.bar_service import BarController, as_cell

router = APIRouter(prefix="/api/bar", tags=["blind-alley robot"])


@router.post("/simulate", response_model=BarResponse)
def simulate(body: BarRequest):
    try:
        scenario = load_scenario(body.scenario)
        # Only rows and public endpoints enter the navigation policy. The gate
        # is read by the evaluator after the complete episode has finished.
        episode = BarController(scenario.rows, scenario.start, scenario.goal, body.radius).run()
        gate_metrics = evaluate(scenario, episode)
        return {"scenario": scenario.name,
                "map_kind": "polygon_grid" if scenario.map_source else "grid",
                "radius": body.radius,
                "rows": len(scenario.rows), "cols": len(scenario.rows[0]),
                "start": as_cell(scenario.start), "goal": as_cell(scenario.goal),
                **episode, "metrics": {**episode["metrics"], **gate_metrics}}
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/continuous", response_model=ContinuousBarResponse)
def simulate_polygon(body: ContinuousBarRequest):
    try:
        maze = None
        if body.scenario.startswith("maze_"):
            config = SHOWCASE if body.scenario == "maze_showcase" else HARD if body.scenario == "maze_hard" else MazeConfig(
                seed=body.seed, size=body.size, corridor_width=body.corridor_width,
                loop_rate=body.loop_rate, dead_end_rate=body.dead_end_rate,
                trap_count=body.trap_count, difficulty=body.difficulty,
                start_cell=body.start_cell, goal_cell=body.goal_cell)
            maze = generate_maze(config)
            world = maze.world
        else:
            world = ContinuousWorld.load(body.scenario)
        episode = simulate_continuous(world, body.radius, prefer_novelty=maze is not None,
                                      include_graph=body.debug_graph,
                                      complete_frontier_route=maze is not None)
        return {"scenario": body.scenario, "radius": body.radius,
                "bounds": world.bounds, "y_axis": world.y_axis,
                "start": as_point(world.start), "goal": as_point(world.goal),
                "maze_config": vars(maze.config) if maze else None,
                **episode}
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
