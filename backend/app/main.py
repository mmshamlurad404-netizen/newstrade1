from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="newstrade1 backend", version="0.1.0")


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "trading_mode": settings.trading_mode,
        "kill_switch": settings.kill_switch,
    }
