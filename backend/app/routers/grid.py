from fastapi import APIRouter, HTTPException
from app.schemas.grid import (GridReplanRequest, GridSearchRequest,
                              GridSearchResponse)
from app.services import grid_service

router = APIRouter(prefix="/api/grid", tags=["grid"])


@router.post("/search", response_model=GridSearchResponse)
def search(body: GridSearchRequest):
    try:
        return grid_service.search(body)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/replan", response_model=GridSearchResponse)
def replan(body: GridReplanRequest):
    try:
        return grid_service.replan(body)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
