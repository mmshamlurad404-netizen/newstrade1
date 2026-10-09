from datetime import datetime
from decimal import Decimal


def _num(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _dt(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_news(news, origin_channel: str | None = None) -> dict:
    return {
        "id": news.id,
        "headline": news.headline,
        "coins": list(news.coins or []),
        "event_type": news.event_type,
        "sentiment": news.sentiment,
        "sentiment_score": _num(news.sentiment_score),
        "urgency": news.urgency,
        "certainty": _num(news.certainty),
        "impact_timeframe": news.impact_timeframe,
        "market_scope": news.market_scope,
        "source_count": news.source_count,
        "origin_channel": origin_channel,
        "asset_resolved": news.asset_resolved,
        "analysis_status": news.analysis_status,
        "jev": getattr(news, "jev_assessment", None),
        "first_seen_at": _dt(news.first_seen_at),
        "last_seen_at": _dt(news.last_seen_at),
    }


def serialize_signal(signal) -> dict:
    return {
        "signal_id": signal.id,
        "news_id": signal.news_id,
        "asset": signal.asset,
        "direction": signal.direction,
        "entry_low": _num(signal.entry_low),
        "entry_high": _num(signal.entry_high),
        "order_type": signal.order_type,
        "stop_loss": _num(signal.stop_loss),
        "take_profits": [float(tp) for tp in (signal.take_profits or [])],
        "leverage_suggested": signal.leverage_suggested,
        "timeframe": signal.timeframe,
        "confidence": signal.confidence,
        "market_risk_factor": _num(signal.market_risk_factor),
        "risk_pct": _num(signal.risk_pct),
        "risk_reward": _num(signal.risk_reward),
        "rationale": signal.rationale,
        "status": signal.status,
        "prompt_version": signal.prompt_version,
        "created_at": _dt(signal.created_at),
        "expires_at": _dt(signal.expires_at),
    }


def serialize_trade(trade, mode: str = "paper") -> dict:
    return {
        "id": trade.id,
        "signal_id": trade.signal_id,
        "mode": mode,
        "asset": trade.asset,
        "direction": trade.direction,
        "entry_price": _num(trade.entry_price),
        "exit_price": _num(trade.exit_price),
        "quantity": _num(trade.quantity),
        "pnl": _num(trade.pnl),
        "pnl_pct": _num(trade.pnl_pct),
        "fees": _num(trade.fees),
        "opened_at": _dt(trade.opened_at),
        "closed_at": _dt(trade.closed_at),
        "close_reason": trade.close_reason,
    }


def serialize_channel(channel) -> dict:
    return {
        "id": channel.id,
        "telegram_id": channel.telegram_id,
        "username": channel.username,
        "title": channel.title,
        "kind": getattr(channel, "kind", "telegram"),
        "feed_url": getattr(channel, "feed_url", None),
        "poll_interval_seconds": getattr(channel, "poll_interval_seconds", None),
        "last_polled_at": _dt(getattr(channel, "last_polled_at", None)),
        "is_private": channel.is_private,
        "credibility": _num(channel.credibility),
        "is_active": channel.is_active,
        "last_seen_at": _dt(channel.last_seen_at),
    }


def serialize_notification(note) -> dict:
    return {
        "id": note.id,
        "channel": note.channel,
        "event_type": note.event_type,
        "title": note.title,
        "body": note.body,
        "signal_id": note.signal_id,
        "payload": note.payload,
        "read_at": _dt(note.read_at),
        "created_at": _dt(note.created_at),
    }


def serialize_device(device) -> dict:
    return {
        "id": device.id,
        "token": device.token,
        "platform": device.platform,
        "label": device.label,
        "is_active": device.is_active,
        "created_at": _dt(device.created_at),
        "last_seen_at": _dt(device.last_seen_at),
    }
