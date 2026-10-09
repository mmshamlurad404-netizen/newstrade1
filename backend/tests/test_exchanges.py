import pytest

from app.services.trading import exchanges


class FakeExchange:
    def __init__(self, markets=None, rows=None, fail_times=0, load_fails=False):
        self._markets = markets if markets is not None else {}
        self._rows = rows if rows is not None else []
        self._fail_times = fail_times
        self._load_fails = load_fails
        self.ohlcv_calls = 0

    async def load_markets(self, refresh=False):
        if self._load_fails:
            raise RuntimeError("markets unavailable")
        return self._markets

    async def fetch_ohlcv(self, symbol, timeframe=None, limit=None):
        self.ohlcv_calls += 1
        if self.ohlcv_calls <= self._fail_times:
            raise RuntimeError("transient network error")
        return self._rows

    async def fetch_ticker(self, symbol):
        return {"bid": 99.0, "ask": 101.0, "last": 100.0}


async def test_retry_succeeds_after_transient_failures():
    fake = FakeExchange(rows=[[1, 2, 3, 4, 5, 6]], fail_times=2)
    result = await exchanges.call_with_retry(
        fake.fetch_ohlcv, "SOL/USDT", attempts=3, base_delay=0
    )
    assert result == [[1, 2, 3, 4, 5, 6]]
    assert fake.ohlcv_calls == 3


async def test_retry_raises_after_exhausting_attempts():
    fake = FakeExchange(fail_times=5)
    with pytest.raises(RuntimeError):
        await exchanges.call_with_retry(
            fake.fetch_ohlcv, "SOL/USDT", attempts=3, base_delay=0
        )
    assert fake.ohlcv_calls == 3


async def test_fetch_candles_maps_rows_to_dicts():
    fake = FakeExchange(rows=[[1700000000000, 1.0, 2.0, 0.5, 1.5, 10.0]])
    candles = await exchanges.fetch_candles(fake, "SOL/USDT", "15m")
    assert candles == [
        {
            "ts": 1700000000000,
            "open": 1.0,
            "high": 2.0,
            "low": 0.5,
            "close": 1.5,
            "volume": 10.0,
        }
    ]


async def test_symbol_allowed_true_for_active_market():
    fake = FakeExchange(markets={"SOL/USDT": {"active": True}})
    assert await exchanges.symbol_allowed(fake, "SOL/USDT") is True


async def test_symbol_allowed_false_when_missing():
    fake = FakeExchange(markets={"BTC/USDT": {"active": True}})
    assert await exchanges.symbol_allowed(fake, "SOL/USDT") is False


async def test_symbol_allowed_false_when_inactive():
    fake = FakeExchange(markets={"SOL/USDT": {"active": False}})
    assert await exchanges.symbol_allowed(fake, "SOL/USDT") is False


async def test_symbol_allowed_false_when_markets_unavailable():
    fake = FakeExchange(load_fails=True)
    assert await exchanges.symbol_allowed(fake, "SOL/USDT") is False


async def test_snapshot_computes_spread_pct():
    fake = FakeExchange()
    snap = await exchanges.snapshot(fake, "SOL/USDT")
    assert snap["bid"] == 99.0
    assert snap["ask"] == 101.0
    assert snap["price"] == 100.0
    assert round(snap["spread_pct"], 2) == 2.0
