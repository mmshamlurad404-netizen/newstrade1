import pytest

from app.schemas.signal import Direction
from app.services.signals.levels import (
    atr,
    build_levels,
    entry_zone,
    risk_reward,
)


def _candles() -> list[dict]:
    candles = []
    price = 100.0
    for index in range(20):
        candles.append(
            {"high": price + 2 + index, "low": price - 2, "close": price}
        )
    return candles


def test_atr_requires_history():
    with pytest.raises(ValueError):
        atr([{"high": 1, "low": 0, "close": 0.5}])


def test_atr_positive():
    assert atr(_candles()) > 0


def test_build_levels_long_ordering():
    stop, tps = build_levels(Direction.LONG, 100.0, 2.0)
    assert stop < 100 < tps[0] < tps[1] < tps[2]


def test_build_levels_short_ordering():
    stop, tps = build_levels(Direction.SHORT, 100.0, 2.0)
    assert stop > 100 > tps[0] > tps[1] > tps[2]


def test_entry_zone_brackets_price():
    low, high = entry_zone(100.0, 2.0)
    assert low < 100 < high


def test_risk_reward():
    assert risk_reward(100, 98, 103) == pytest.approx(1.5)
    assert risk_reward(100, 100, 103) == 0.0
