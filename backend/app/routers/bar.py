from fastapi import APIRouter, HTTPException

from app.schemas.bar import BarRequest, BarResponse
from app.services.bar_evaluation import evaluate
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
        return {"scenario": scenario.name, "radius": body.radius,
                "rows": len(scenario.rows), "cols": len(scenario.rows[0]),
                "start": as_cell(scenario.start), "goal": as_cell(scenario.goal),
                **episode, "metrics": {**episode["metrics"], **gate_metrics}}
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
