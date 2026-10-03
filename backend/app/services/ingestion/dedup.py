import hashlib
import re
from datetime import datetime

WORD_RE = re.compile(r"[a-z0-9]+")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.lower().encode("utf-8")).hexdigest()


def token_set(text: str, k: int = 1) -> frozenset[str]:
    words = WORD_RE.findall(text.lower())
    if k <= 1:
        return frozenset(words)
    return frozenset(
        " ".join(words[i : i + k]) for i in range(len(words) - k + 1)
    )


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_duplicate(a: str, b: str, threshold: float = 0.9, k: int = 1) -> bool:
    return jaccard(token_set(a, k), token_set(b, k)) >= threshold


def structured_key(
    event_type: str, coin: str, ts: datetime, bucket_minutes: int = 30
) -> str:
    bucket = int(ts.timestamp()) // (bucket_minutes * 60)
    return f"{event_type}:{coin.upper()}:{bucket}"
