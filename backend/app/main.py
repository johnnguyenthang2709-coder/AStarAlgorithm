from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.routers import grid, road
from app.schemas.road import HealthResponse
from app.services.road_bundle import load_bundle

LOG = logging.getLogger(__name__)
DEFAULT_GRAPH = Path(__file__).resolve().parents[2] / "data" / "road" / "graph.json"


def create_app(graph_path: Path | None = None) -> FastAPI:
    dataset = graph_path or Path(os.getenv("ASTAR_ROAD_GRAPH", DEFAULT_GRAPH))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.road_engine, app.state.road_geometry, app.state.road_context = load_bundle(dataset)
            LOG.info("Road graph loaded from %s", dataset)
        except Exception:
            app.state.road_engine = None
            app.state.road_geometry = None
            app.state.road_context = None
            LOG.exception("Road graph unavailable from %s", dataset)
        yield
        app.state.road_engine = None
        app.state.road_geometry = None
        app.state.road_context = None

    app = FastAPI(
        title="A* Road and Grid API",
        description="C++ A* and Dijkstra search for a local directed road graph and request grids.",
        version="0.1.0",
        lifespan=lifespan,
    )
    origins = [origin.strip() for origin in os.getenv(
        "ASTAR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_credentials=False, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])
    app.include_router(road.router)
    app.include_router(grid.router)

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health(response: Response):
        engine = getattr(app.state, "road_engine", None)
        if engine is None:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "degraded", "road_graph_loaded": False,
                    "road_nodes": 0, "road_edges": 0}
        return {"status": "ok", "road_graph_loaded": True,
                "road_nodes": engine.node_count, "road_edges": engine.edge_count}

    return app


app = create_app()
