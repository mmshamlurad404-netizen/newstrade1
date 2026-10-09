from sqlalchemy import select

from app.core.logging import get_logger
from app.models.notifications import DeviceToken, Notification
from app.services.notifications.senders import get_sender

log = get_logger("notifications.dispatcher")


def _fmt(value, digits: int = 4):
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def build_notification(event: dict) -> dict | None:
    """Translate a pipeline event into a notification payload.

    Returns None for events that should not alert the user.
    """
    if not isinstance(event, dict):
        return None

    status = event.get("status")
    signal_id = event.get("signal_id")

    if status == "active":
        asset = event.get("asset", "?")
        direction = event.get("direction", "?")
        title = f"New {direction} signal: {asset}"
        body = (
            f"Entry {_fmt(event.get('entry_low'), 4)}-{_fmt(event.get('entry_high'), 4)}, "
            f"confidence {event.get('confidence', '?')}, "
            f"R:R {_fmt(event.get('risk_reward'), 2)}"
        )
        return _row("signal_new", title, body, event, signal_id)

    if status == "rejected":
        asset = event.get("asset", "?")
        reasons = event.get("reasons") or []
        title = f"Signal rejected: {asset}"
        body = ", ".join(str(r) for r in reasons) or "did not pass risk checks"
        return _row("signal_rejected", title, body, event, signal_id)

    if status == "closed":
        asset = event.get("asset", "?")
        reason = event.get("close_reason", "closed")
        title = f"Position closed ({reason}): {asset}"
        body = f"PnL {_fmt(event.get('pnl'), 2)} ({_fmt(event.get('pnl_pct'), 2)}%)"
        return _row("signal_closed", title, body, event, signal_id)

    headline = event.get("headline")
    if headline:
        body = event.get("summary") or event.get("body") or event.get("event_type")
        return _row("news", str(headline), body, event, event.get("signal_id"))

    return None


def _row(event_type, title, body, event, signal_id) -> dict:
    return {
        "channel": "inapp",
        "event_type": event_type,
        "title": title,
        "body": body,
        "payload": event,
        "signal_id": signal_id,
    }


async def dispatch(session, event: dict, sender=None) -> Notification | None:
    """Persist a notification and fan it out to active device tokens."""
    data = build_notification(event)
    if data is None:
        return None

    note = Notification(**data)
    session.add(note)

    tokens = (
        await session.scalars(
            select(DeviceToken).where(DeviceToken.is_active.is_(True))
        )
    ).all()

    if tokens:
        sender = sender or get_sender()
        payload = {
            "event_type": data["event_type"],
            "signal_id": data["signal_id"],
        }
        for device in tokens:
            try:
                await sender.send(device.token, data["title"], data["body"], payload)
            except Exception as exc:
                log.error(
                    "delivery failed for token %.8s: %s" % (device.token, exc),
                    extra={"stage": "notifications"},
                )

    await session.commit()
    return note
