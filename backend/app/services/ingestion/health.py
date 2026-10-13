"""Ingestor liveness state shared through Redis.

The Telegram listener runs in its own process, so its connection health is
published to a Redis hash that the metrics collector and alert monitor read.
Fields: ``connected`` ("1"/"0"), ``reconnects`` (counter), ``heartbeat``
(epoch seconds of the last sample), ``last_event`` (epoch seconds of the last
ingested message), ``started_at``.
"""

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
