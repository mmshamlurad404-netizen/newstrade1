from app.services.analysis.coins import (
    canonicalize,
    extract_symbols,
    resolve_coins,
)


def test_extract_symbols_uppercases():
    assert "BTC" in extract_symbols("buy $btc now")


def test_resolve_known_only():
    assert resolve_coins("BTC and ZZZ") == ["BTC"]


def test_canonicalize_respects_allowlist():
    assert canonicalize("btc", frozenset({"BTC"})) == "BTC"
    assert canonicalize("zzz", frozenset({"BTC"})) is None
