import re

KNOWN_SYMBOLS = frozenset(
    {
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "BNB",
        "DOGE",
        "ADA",
        "AVAX",
        "LINK",
        "MATIC",
        "ARB",
        "OP",
        "TON",
        "TRX",
        "DOT",
        "LTC",
        "BCH",
        "NEAR",
        "APT",
        "SUI",
    }
)

SYMBOL_RE = re.compile(r"\$?([A-Za-z]{2,10})\b")


def extract_symbols(text: str) -> list[str]:
    return [match.group(1).upper() for match in SYMBOL_RE.finditer(text)]


def canonicalize(symbol: str, allowed: frozenset[str]) -> str | None:
    candidate = symbol.upper().lstrip("$")
    return candidate if candidate in allowed else None


def resolve_coins(
    text: str, allowed: frozenset[str] | None = None
) -> list[str]:
    universe = allowed or KNOWN_SYMBOLS
    resolved: list[str] = []
    for symbol in extract_symbols(text):
        if symbol in universe and symbol not in resolved:
            resolved.append(symbol)
    return resolved
