import re

COIN_ALIASES = {
    "BTC": ["btc", "bitcoin"],
    "ETH": ["eth", "ethereum", "ether"],
    "SOL": ["sol", "solana"],
    "XRP": ["xrp", "ripple"],
    "BNB": ["bnb", "binance coin"],
    "DOGE": ["doge", "dogecoin"],
    "ADA": ["ada", "cardano"],
    "AVAX": ["avax", "avalanche"],
    "LINK": ["link", "chainlink"],
    "MATIC": ["matic", "polygon"],
    "ARB": ["arb", "arbitrum"],
    "OP": ["optimism"],
}

EVENT_KEYWORDS = {
    "listing": ["listing", "will list", "spot listing", "lists "],
    "delisting": ["delist", "delisting", "removal"],
    "hack": ["hack", "exploit", "breach", "drained", "stolen"],
    "regulation": ["sec", "cftc", "regulation", "lawsuit", "ban", "etf"],
    "partnership": ["partnership", "collaboration", "integrates", "teams up"],
    "unlock": ["unlock", "vesting", "token release"],
    "whale": ["whale", "large transfer", "moved to exchange"],
    "macro": ["cpi", "fed", "interest rate", "inflation", "powell"],
}

LISTING_PATTERNS = (
    re.compile(r"\bwill list\s+\$?([A-Z0-9]{2,10})\b", re.I),
    re.compile(r"\blisting of\s+\$?([A-Z0-9]{2,10})\b", re.I),
    re.compile(r"\blists?\s+\$?([A-Z0-9]{2,10})\s+(?:on|for)\b", re.I),
)

DELIST_PATTERNS = (
    re.compile(r"\bwill delist\s+\$?([A-Z0-9]{2,10})\b", re.I),
    re.compile(r"\bdelist(?:ing)?\s+\$?([A-Z0-9]{2,10})\b", re.I),
)

STOP_COINS = {
    "ON",
    "FOR",
    "THE",
    "AND",
    "WILL",
    "LIST",
    "LISTS",
    "SPOT",
    "NEW",
    "USD",
    "USDT",
}


def relevance_score(text: str) -> float:
    lowered = text.lower()
    score = 0.0
    if any(any(alias in lowered for alias in aliases) for aliases in COIN_ALIASES.values()):
        score += 0.4
    if any(any(word in lowered for word in words) for words in EVENT_KEYWORDS.values()):
        score += 0.4
    if len(lowered) > 40:
        score += 0.2
    return min(score, 1.0)


def _match_fast(patterns, text: str, event_type: str) -> dict | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        coin = match.group(1).upper()
        if coin in STOP_COINS:
            continue
        return {
            "event_type": event_type,
            "coin": coin,
            "matched_text": match.group(0),
        }
    return None


def detect_fast_alert(text: str) -> dict | None:
    listing = _match_fast(LISTING_PATTERNS, text, "listing")
    if listing is not None:
        return listing
    return _match_fast(DELIST_PATTERNS, text, "delisting")
