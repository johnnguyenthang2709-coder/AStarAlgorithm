from fastapi import APIRouter, Depends, HTTPException, Request, Response
import astar_core
from app.schemas.common import Coordinate
from app.schemas.road import (RoadCompareRequest, RoadCompareResponse,
                              RoadSearchRequest, RoadSearchResponse,
                              RoadSnapResponse, RoadNodePosition)
from app.services import road_service

router = APIRouter(prefix="/api/road", tags=["road"])


def get_engine(request: Request) -> astar_core.RoadEngine:
    engine = getattr(request.app.state, "road_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="road graph unavailable")
    return engine


@router.post("/snap", response_model=RoadSnapResponse)
def snap(point: Coordinate, engine: astar_core.RoadEngine = Depends(get_engine)):
    return road_service.snap(engine, point)


@router.get("/nodes", response_model=list[RoadNodePosition])
def nodes(engine: astar_core.RoadEngine = Depends(get_engine)):
    return road_service.nodes(engine)


@router.get("/geometry", response_class=Response)
def geometry(request: Request, engine: astar_core.RoadEngine = Depends(get_engine)):
    _ = engine
    return Response(content=request.app.state.road_geometry,
                    media_type="application/geo+json")


@router.get("/context", response_class=Response)
def context(request: Request, engine: astar_core.RoadEngine = Depends(get_engine)):
    _ = engine
    payload = request.app.state.road_context
    if payload is None:
        raise HTTPException(status_code=404, detail="cartographic context not exported")
    return Response(content=payload, media_type="application/geo+json")


@router.post("/search", response_model=RoadSearchResponse)
def search(body: RoadSearchRequest, engine: astar_core.RoadEngine = Depends(get_engine)):
    try:
        return road_service.search(engine, body)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/compare", response_model=RoadCompareResponse)
def compare(body: RoadCompareRequest, engine: astar_core.RoadEngine = Depends(get_engine)):
    try:
        return road_service.compare(engine, body)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
