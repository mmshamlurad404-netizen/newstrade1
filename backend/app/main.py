from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, ws_router
from app.core import runtime
from app.core.config import settings

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
    return {
        "status": "ok",
        "trading_mode": settings.trading_mode,
        "kill_switch": settings.kill_switch or await runtime.get_kill_switch(),
    }
