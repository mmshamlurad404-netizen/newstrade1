from datetime import datetime, timedelta, timezone

from app.schemas.signal import Direction
from app.services.trading.manage import evaluate_exit, rollup_pnl_pct

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _exit(direction, entry, stop, tp, candle, *, fees=0.0, quantity=1.0, expires_at=None):
    return evaluate_exit(
        direction=direction,
        entry_price=entry,
        quantity=quantity,
        fees=fees,
        stop_loss=stop,
        take_profit=tp,
        candle=candle,
        now=NOW,
        expires_at=expires_at,
    )


def test_long_stop_loss():
    decision = _exit(Direction.LONG, 100, 98, 104, {"high": 101, "low": 97, "close": 99})
    assert decision.reason == "stop_loss"
    assert decision.exit_price == 98
    assert decision.pnl == -2.0
    assert decision.pnl_pct == -2.0


def test_long_take_profit():
    decision = _exit(Direction.LONG, 100, 98, 104, {"high": 105, "low": 99, "close": 104})
    assert decision.reason == "take_profit"
    assert decision.pnl == 4.0


def test_short_stop_loss():
    decision = _exit(Direction.SHORT, 100, 102, 96, {"high": 103, "low": 99, "close": 101})
    assert decision.reason == "stop_loss"
    assert decision.exit_price == 102
    assert decision.pnl == -2.0


def test_short_take_profit():
    decision = _exit(Direction.SHORT, 100, 102, 96, {"high": 101, "low": 95, "close": 96})
    assert decision.reason == "take_profit"
    assert decision.pnl == 4.0


def test_fees_reduce_pnl():
    decision = _exit(
        Direction.LONG, 100, 98, 104, {"high": 105, "low": 99, "close": 104}, fees=1.0
    )
    assert decision.pnl == 3.0


def test_no_exit_returns_none():
    decision = _exit(Direction.LONG, 100, 98, 104, {"high": 101, "low": 99, "close": 100})
    assert decision is None


def test_expiry_closes_at_close():
    decision = _exit(
        Direction.LONG,
        100,
        98,
        104,
        {"high": 101, "low": 99, "close": 100.5},
        expires_at=NOW - timedelta(minutes=1),
    )
    assert decision.reason == "expired"
    assert decision.exit_price == 100.5


def test_rollup_pnl_pct():
    assert rollup_pnl_pct(150, 10000) == 1.5
    assert rollup_pnl_pct(-300, 10000) == -3.0
    assert rollup_pnl_pct(150, 0) == 0.0
