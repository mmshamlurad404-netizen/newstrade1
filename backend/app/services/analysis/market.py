import httpx

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "BNB": "binancecoin",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "ARB": "arbitrum",
    "OP": "optimism",
}


async def fetch_price(symbol: str) -> float | None:
    coin_id = SYMBOL_TO_ID.get(symbol.upper())
    if coin_id is None:
        return None
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"},
        )
        response.raise_for_status()
        data = response.json()
    return data.get(coin_id, {}).get("usd")


def cap_tier(market_cap: float | None) -> str:
    if market_cap is None:
        return "unknown"
    if market_cap >= 10_000_000_000:
        return "large"
    if market_cap >= 1_000_000_000:
        return "mid"
    return "small"
