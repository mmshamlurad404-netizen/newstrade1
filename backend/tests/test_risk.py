from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.signal import Direction, Signal
from app.services.trading.risk import (
    RiskConfig,
    RiskState,
    base_risk_pct,
    evaluate,
    position_size,
)


def _signal(confidence: int = 80, reward_risk: float = 2.0, leverage: int = 3) -> Signal:
    now = datetime.now(timezone.utc)
    return Signal(
        signal_id="s1",
        news_id=1,
        asset="SOL/USDT",
        direction=Direction.LONG,
        entry_low=100.0,
        entry_high=101.0,
        stop_loss=98.0,
        take_profits=[104.0, 106.0, 110.0],
        leverage_suggested=leverage,
        timeframe="15m",
        confidence=confidence,
        market_risk_factor=1.0,
        risk_reward=reward_risk,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )


def test_position_size():
    assert position_size(10000, 0.01, 100, 98) == pytest.approx(50)


def test_base_risk_buckets():
    config = RiskConfig()
    assert base_risk_pct(50, config) == 0.0
    assert base_risk_pct(65, config) == 0.005
    assert base_risk_pct(80, config) == 0.01
    assert base_risk_pct(90, config) == 0.02


def test_evaluate_approves_healthy():
    decision = evaluate(
        _signal(),
        RiskConfig(),
        RiskState(equity=10000),
        market_risk_factor=1.0,
        spread_pct=0.1,
        depth_ok=True,
        beta_to_btc=1.0,
    )
    assert decision.approved
    assert decision.size > 0


def test_evaluate_rejects_kill_switch():
    decision = evaluate(
        _signal(),
        RiskConfig(),
        RiskState(equity=10000, kill_switch=True),
        market_risk_factor=1.0,
        spread_pct=0.1,
        depth_ok=True,
        beta_to_btc=1.0,
    )
    assert not decision.approved
    assert "kill_switch" in decision.reasons


def test_evaluate_rejects_low_confidence():
    decision = evaluate(
        _signal(confidence=55),
        RiskConfig(),
        RiskState(equity=10000),
        market_risk_factor=1.0,
        spread_pct=0.1,
        depth_ok=True,
        beta_to_btc=1.0,
    )
    assert "low_confidence" in decision.reasons


def test_evaluate_rejects_correlation_when_crowded():
    decision = evaluate(
        _signal(confidence=90),
        RiskConfig(),
        RiskState(equity=10000, correlated_risk_amount=450),
        market_risk_factor=1.0,
        spread_pct=0.1,
        depth_ok=True,
        beta_to_btc=1.0,
    )
    assert "correlation" in decision.reasons
