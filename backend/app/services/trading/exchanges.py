import asyncio

import ccxt.pro as ccxtpro

from app.core.logging import get_logger

log = get_logger("trading.exchanges")

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 0.5


def build_exchange(name: str, api_key: str, secret: str, testnet: bool = True):
    klass = getattr(ccxtpro, name)
    exchange = klass(
        {
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
    )
    if testnet:
        exchange.set_sandbox_mode(True)
    return exchange


async def call_with_retry(
    fn,
    *args,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    retry_on=(Exception,),
    **kwargs,
):
    """Await ``fn(*args, **kwargs)`` with exponential backoff.

    ``fn`` is a zero-or-more-arg coroutine function. Retries transient
    failures up to ``attempts`` times, doubling the delay each time.
    """
    attempts = max(1, attempts)
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except retry_on as exc:  # type: ignore[misc]
            last = exc
            if attempt >= attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            log.warning(
                "exchange call failed (attempt %s/%s): %s; retrying in %.1fs"
                % (attempt, attempts, exc, delay),
                extra={"stage": "exchanges"},
            )
            await asyncio.sleep(delay)
    assert last is not None
    raise last


async def load_markets(exchange, refresh: bool = False) -> dict:
    return await call_with_retry(exchange.load_markets, refresh)


async def symbol_allowed(exchange, symbol: str) -> bool:
    """Return True only if the symbol exists and is active on the exchange."""
    try:
        markets = await load_markets(exchange)
    except Exception as exc:
        log.error(
            "load_markets failed: %s" % exc, extra={"stage": "exchanges"}
        )
        return False
    market = markets.get(symbol)
    if not market:
        return False
    return market.get("active", True) is not False


async def fetch_candles(
    exchange, symbol: str, timeframe: str, limit: int = 200
) -> list[dict]:
    rows = await call_with_retry(
        exchange.fetch_ohlcv, symbol, timeframe=timeframe, limit=limit
    )
    return [
        {
            "ts": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
        }
        for row in rows
    ]


async def snapshot(exchange, symbol: str) -> dict:
    ticker = await call_with_retry(exchange.fetch_ticker, symbol)
    bid = ticker.get("bid") or 0.0
    ask = ticker.get("ask") or 0.0
    mid = (bid + ask) / 2 if bid and ask else ticker.get("last", 0.0)
    spread_pct = ((ask - bid) / mid * 100) if mid and ask and bid else 0.0
    return {"price": ticker.get("last"), "bid": bid, "ask": ask, "spread_pct": spread_pct}
