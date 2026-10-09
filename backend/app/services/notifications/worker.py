import asyncio
import json

from app.services.notifications.dispatcher import dispatch

from app.core.logging import configure_logging, get_logger
from app.core.config import settings
from app.db.session import async_session_factory
from app.services.ingestion.queue import (
    FAST_ALERTS_STREAM,
    SIGNALS_STREAM,
    close,
    get_client,
)

log = get_logger("notifications.worker")

NOTIFY_GROUP = "notifications"
CONSUMER = "notifier-1"


async def _ensure_groups() -> None:
    client = get_client()
    for stream in (SIGNALS_STREAM, FAST_ALERTS_STREAM):
        try:
            # "$" so notifications only cover events arriving after startup,
            # unlike the pipeline groups which replay from the beginning.
            await client.xgroup_create(stream, NOTIFY_GROUP, id="$", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise


async def run() -> None:
    configure_logging(settings.log_level)
    await _ensure_groups()
    client = get_client()
    streams = {SIGNALS_STREAM: ">", FAST_ALERTS_STREAM: ">"}
    log.info("notifications worker started", extra={"stage": "notifications"})

    while True:
        try:
            response = await client.xreadgroup(
                NOTIFY_GROUP, CONSUMER, streams, count=20, block=5000
            )
        except Exception as exc:
            log.error(
                "read failed: %s" % exc, extra={"stage": "notifications"}
            )
            await asyncio.sleep(1)
            continue

        if not response:
            continue

        for stream, entries in response:
            for entry_id, fields in entries:
                try:
                    if settings.notifications_enabled:
                        payload = json.loads(fields.get("payload", "{}"))
                        async with async_session_factory() as session:
                            await dispatch(session, payload)
                except Exception as exc:
                    log.error(
                        "dispatch failed: %s" % exc,
                        extra={"stage": "notifications"},
                    )
                finally:
                    await client.xack(stream, NOTIFY_GROUP, entry_id)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
