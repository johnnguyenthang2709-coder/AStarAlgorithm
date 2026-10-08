from fastapi import APIRouter, HTTPException

from app.schemas.bar import BarRequest, BarResponse, ContinuousBarRequest, ContinuousBarResponse
from app.services.bar_evaluation import evaluate
from app.services.bar_continuous import simulate_continuous
from app.services.bar_continuous_geometry import ContinuousWorld, as_point
from app.services.bar_maze import MazeConfig, SHOWCASE, HARD, generate_maze
from app.services.bar_labyrinth import LabyrinthConfig, EXPLORATION, BLIND_ALLEY, COMPLEX, generate_labyrinth
from app.services.bar_indoor import APARTMENT, OFFICE, CHALLENGE, IndoorConfig, generate_indoor
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
        indoor = None
        if body.scenario.startswith("indoor_"):
            config = {"indoor_apartment": APARTMENT, "indoor_office": OFFICE,
                      "indoor_challenge": CHALLENGE}.get(body.scenario)
            if config is None:
                config = IndoorConfig(body.indoor_layout, body.seed)
            indoor = generate_indoor(config)
            world = indoor.world
        elif body.scenario.startswith("lab_"):
            config = {"lab_exploration": EXPLORATION, "lab_alley": BLIND_ALLEY,
                      "lab_complex": COMPLEX}.get(body.scenario)
            if config is None:
                config = LabyrinthConfig(
                    seed=body.seed, size=body.size, corridor_width=body.corridor_width,
                    loop_rate=body.loop_rate, dead_end_rate=body.dead_end_rate,
                    trap_count=body.trap_count, difficulty=body.difficulty,
                    irregularity=body.irregularity,
                    start_cell=body.start_cell, goal_cell=body.goal_cell)
            maze = generate_labyrinth(config)
            world = maze.world
        elif body.scenario.startswith("maze_"):
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
                                      complete_frontier_route=maze is not None or indoor is not None,
                                      trace_hierarchy=indoor is not None)
        return {"scenario": body.scenario, "radius": body.radius,
                "bounds": world.bounds, "y_axis": world.y_axis,
                "start": as_point(world.start), "goal": as_point(world.goal),
                "maze_config": vars(maze.config) if maze else None,
                "indoor_config": vars(indoor.config) if indoor else None,
                **episode}
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
