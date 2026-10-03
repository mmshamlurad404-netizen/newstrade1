from datetime import datetime, timezone

from app.services.ingestion.dedup import (
    content_hash,
    is_duplicate,
    jaccard,
    structured_key,
)


def test_content_hash_is_case_insensitive():
    assert content_hash("BTC Listing") == content_hash("btc listing")


def test_identical_text_is_duplicate():
    assert is_duplicate("Binance will list SOL", "Binance will list SOL")


def test_near_duplicate_is_detected():
    a = "Binance will list SOL on spot market tomorrow"
    b = "Binance will list SOL on the spot market tomorrow"
    assert is_duplicate(a, b, threshold=0.75)


def test_unrelated_text_is_not_duplicate():
    assert not is_duplicate("Binance will list SOL", "ETH hack drained funds")


def test_jaccard_boundaries():
    assert jaccard(frozenset(), frozenset()) == 1.0
    assert jaccard(frozenset({"a"}), frozenset()) == 0.0


def test_structured_key_is_case_and_time_bucketed():
    left = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    right = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)
    assert structured_key("listing", "sol", left) == structured_key(
        "listing", "SOL", right
    )
