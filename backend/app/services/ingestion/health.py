"""Ingestor liveness state shared through Redis.

The Telegram listener runs in its own process, so its connection health is
published to a Redis hash that the metrics collector and alert monitor read.
Fields: ``connected`` ("1"/"0"), ``reconnects`` (counter), ``heartbeat``
(epoch seconds of the last sample), ``last_event`` (epoch seconds of the last
ingested message), ``started_at``.
"""

import asyncio
import time

INGESTOR_KEY = "runtime:ingestor"


def _now() -> float:
    return time.time()


async def record_started(client) -> None:
    now = _now()
    await client.hset(
        INGESTOR_KEY,
        mapping={"started_at": now, "heartbeat": now, "connected": "1"},
    )


async def record_heartbeat(client, connected: bool) -> None:
    await client.hset(
        INGESTOR_KEY,
        mapping={"connected": "1" if connected else "0", "heartbeat": _now()},
    )


async def record_event(client) -> None:
    await client.hset(INGESTOR_KEY, mapping={"last_event": _now()})


async def record_reconnect(client) -> None:
    await client.hincrby(INGESTOR_KEY, "reconnects", 1)


async def read_state(client) -> dict:
    try:
        return await client.hgetall(INGESTOR_KEY)
    except Exception:
        return {}


async def snapshot(stale_seconds: int, timeout: float) -> dict:
    """Timeout-bounded ingestion health for the readiness endpoint.

    Reads the ingestor hash under ``wait_for`` so a hung Redis cannot block
    the health endpoint. Returns ``status = unknown`` when the ingestor has
    never reported or the read failed, ``degraded`` when it is offline or its
    heartbeat is stale, and ``ok`` otherwise.
    """
    from app.services.ingestion.queue import get_client

    try:
        state = await asyncio.wait_for(
            get_client().hgetall(INGESTOR_KEY), timeout=timeout
        )
    except Exception:
        state = {}

    if not state:
        return {
            "reported": False,
            "connected": False,
            "seconds_since_heartbeat": None,
            "stale": True,
            "status": "unknown",
        }

    heartbeat = state.get("heartbeat")
    seconds_since = None
    if heartbeat is not None:
        seconds_since = max(0.0, time.time() - float(heartbeat))
    connected = state.get("connected") == "1"
    stale = seconds_since is None or seconds_since > stale_seconds
    return {
        "reported": True,
        "connected": connected,
        "seconds_since_heartbeat": seconds_since,
        "stale": stale,
        "status": "degraded" if (stale or not connected) else "ok",
    }
