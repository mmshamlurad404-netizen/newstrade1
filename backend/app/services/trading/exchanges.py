import ccxt.pro as ccxtpro


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


async def fetch_candles(exchange, symbol: str, timeframe: str, limit: int = 200) -> list[dict]:
    rows = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
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
    ticker = await exchange.fetch_ticker(symbol)
    bid = ticker.get("bid") or 0.0
    ask = ticker.get("ask") or 0.0
    mid = (bid + ask) / 2 if bid and ask else ticker.get("last", 0.0)
    spread_pct = ((ask - bid) / mid * 100) if mid and ask and bid else 0.0
    return {"price": ticker.get("last"), "bid": bid, "ask": ask, "spread_pct": spread_pct}
