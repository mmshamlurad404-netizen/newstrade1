from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import serializers
from app.api.deps import verify_token
from app.main import app

client = TestClient(app)


def test_health_is_public():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_route_requires_token():
    assert client.get("/api/signals").status_code == 401


def test_protected_route_rejects_bad_token():
    response = client.get(
        "/api/signals", headers={"Authorization": "Bearer nope"}
    )
    assert response.status_code == 401


def test_verify_token():
    assert verify_token("test-token")
    assert not verify_token("bad")
    assert not verify_token(None)


def test_websocket_rejects_bad_token():
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/signals?token=bad") as ws:
            ws.receive_text()


def test_serialize_signal():
    signal = SimpleNamespace(
        id="s1",
        news_id=1,
        asset="SOL/USDT",
        direction="LONG",
        entry_low=Decimal("145.2"),
        entry_high=Decimal("146"),
        order_type="limit",
        stop_loss=Decimal("143.5"),
        take_profits=[Decimal("148"), Decimal("150.5")],
        leverage_suggested=3,
        timeframe="15m",
        confidence=78,
        market_risk_factor=Decimal("0.8"),
        risk_pct=Decimal("0.01"),
        risk_reward=Decimal("2.8"),
        rationale="x",
        status="active",
        prompt_version="v1",
        created_at=None,
        expires_at=None,
    )
    data = serializers.serialize_signal(signal)
    assert data["signal_id"] == "s1"
    assert data["entry_low"] == 145.2
    assert data["take_profits"] == [148.0, 150.5]
    assert data["confidence"] == 78


def test_serialize_news_handles_none_scores():
    news = SimpleNamespace(
        id=1,
        headline="h",
        coins=["SOL"],
        event_type="listing",
        sentiment="bullish",
        sentiment_score=None,
        urgency="high",
        certainty=None,
        impact_timeframe="intraday",
        market_scope="asset",
        source_count=2,
        asset_resolved=True,
        analysis_status="analyzed",
        first_seen_at=None,
        last_seen_at=None,
    )
    data = serializers.serialize_news(news, "SomeChannel")
    assert data["coins"] == ["SOL"]
    assert data["sentiment_score"] is None
    assert data["origin_channel"] == "SomeChannel"
