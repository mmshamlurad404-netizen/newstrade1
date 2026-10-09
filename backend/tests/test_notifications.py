from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api import serializers
from app.schemas.api import DeviceRegister
from app.services.notifications.dispatcher import build_notification
from app.services.notifications.senders import LogSender


def test_build_notification_active_signal():
    note = build_notification(
        {
            "signal_id": "s1",
            "asset": "SOL/USDT",
            "direction": "LONG",
            "entry_low": 100.0,
            "entry_high": 101.0,
            "confidence": 82,
            "risk_reward": 1.5,
            "status": "active",
        }
    )
    assert note["event_type"] == "signal_new"
    assert note["signal_id"] == "s1"
    assert "SOL/USDT" in note["title"]
    assert "82" in note["body"]


def test_build_notification_rejected_signal():
    note = build_notification(
        {
            "signal_id": "s2",
            "asset": "ETH/USDT",
            "status": "rejected",
            "reasons": ["low_confidence"],
        }
    )
    assert note["event_type"] == "signal_rejected"
    assert "low_confidence" in note["body"]


def test_build_notification_closed_signal():
    note = build_notification(
        {
            "signal_id": "s3",
            "asset": "BTC/USDT",
            "status": "closed",
            "close_reason": "take_profit",
            "pnl": 40.0,
            "pnl_pct": 2.5,
        }
    )
    assert note["event_type"] == "signal_closed"
    assert "take_profit" in note["title"]


def test_build_notification_news_alert():
    note = build_notification({"headline": "Big news", "event_type": "listing"})
    assert note["event_type"] == "news"
    assert note["title"] == "Big news"


def test_build_notification_unknown_returns_none():
    assert build_notification({"foo": "bar"}) is None
    assert build_notification("not-a-dict") is None


async def test_log_sender_returns_true():
    assert await LogSender().send("token-123", "title", "body") is True


def test_serialize_notification():
    note = SimpleNamespace(
        id=1,
        channel="inapp",
        event_type="signal_new",
        title="t",
        body="b",
        signal_id="s1",
        payload={"a": 1},
        read_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    data = serializers.serialize_notification(note)
    assert data["id"] == 1
    assert data["signal_id"] == "s1"
    assert data["read_at"] is None
    assert data["created_at"].startswith("2026-01-01")


def test_serialize_device():
    device = SimpleNamespace(
        id=5,
        token="tok",
        platform="android",
        label="pixel",
        is_active=True,
        created_at=None,
        last_seen_at=None,
    )
    data = serializers.serialize_device(device)
    assert data["platform"] == "android"
    assert data["is_active"] is True


def test_device_register_validation():
    body = DeviceRegister(token="1234567890", platform="windows", label="pc")
    assert body.platform == "windows"

    with pytest.raises(ValidationError):
        DeviceRegister(token="short")
    with pytest.raises(ValidationError):
        DeviceRegister(token="1234567890", platform="ios")
