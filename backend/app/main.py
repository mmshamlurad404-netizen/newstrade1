from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.routes import router, ws_router
from app.core import runtime
from app.core.config import settings
from app.db.session import async_session_factory
from app.services.ingestion import health as ingestion_health
from app.services.ingestion.queue import get_client
from app.services.observability import metrics

app = FastAPI(title="newstrade1 backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)


@app.get("/api/health")
async def health() -> dict:
    ingestion = await ingestion_health.snapshot(
        settings.alert_ingestor_stale_seconds,
        settings.health_check_timeout_seconds,
    )
    return {
        "status": "ok",
        "trading_mode": settings.trading_mode,
        "kill_switch": settings.kill_switch or await runtime.get_kill_switch(),
        "ingestion": ingestion,
    }


@app.get("/metrics")
async def prometheus_metrics() -> Response:
    async with async_session_factory() as session:
        samples = await metrics.collect(session, get_client())
    return Response(
        metrics.render(samples), media_type="text/plain; version=0.0.4"
    )
