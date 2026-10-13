"""Periodic alert monitor.

Collects the shared-state metrics on an interval, evaluates the alert rules
in ``alerts.py``, and dispatches any newly-fired alerts through the existing
notification dispatcher (in-app row plus device push).
"""

import asyncio
import time

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.services.ingestion.queue import close, get_client
from app.services.notifications.dispatcher import dispatch
from app.services.observability import alerts, metrics

log = get_logger("observability.monitor")

_state = alerts.AlertState()


def _config() -> alerts.AlertConfig:
    return alerts.AlertConfig(
        backlog_threshold=settings.alert_backlog_threshold,
        dlq_threshold=settings.alert_dlq_threshold,
        daily_loss_pct=settings.max_daily_loss_pct,
        open_risk_pct_max=settings.alert_open_risk_pct_max,
        cooldown_seconds=settings.alert_cooldown_seconds,
        ingestor_stale_seconds=settings.alert_ingestor_stale_seconds,
        ingestor_reconnect_spike=settings.alert_ingestor_reconnect_spike,
    )


async def run_once() -> list[alerts.Alert]:
    async with async_session_factory() as session:
        samples = await metrics.collect(session, get_client())
        data = metrics.to_dict(samples)
        fired = alerts.evaluate(
            data,
            time.time(),
            _config(),
            _state,
            settings.paper_equity,
        )
        for alert in fired:
            await dispatch(
                session,
                {
                    "kind": "system_alert",
                    "event_type": alert.event_type,
                    "alert": alert.key,
                    "severity": alert.severity,
                    "title": alert.title,
                    "body": alert.body,
                    "payload": alert.payload,
                },
            )
    return fired


async def run() -> None:
    configure_logging(settings.log_level)
    log.info("alert monitor started", extra={"stage": "monitor"})
    while True:
        try:
            if settings.alerts_enabled:
                fired = await run_once()
                for alert in fired:
                    log.warning(
                        "alert fired: %s - %s" % (alert.key, alert.body),
                        extra={"stage": "monitor"},
                    )
        except Exception as exc:
            log.error(
                "alert cycle failed: %s" % exc, extra={"stage": "monitor"}
            )
        await asyncio.sleep(settings.alert_interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
