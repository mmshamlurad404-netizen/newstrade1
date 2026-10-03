import re

from app.schemas.analysis import Analysis

INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"ignore (all |previous |prior )?instructions",
        r"disregard (all |previous |prior )",
        r"you are now",
        r"\bsystem\s*:",
        r"\bassistant\s*:",
        r"return (only )?(the )?json",
        r"(buy|long|short) now",
        r"guaranteed (profit|win)",
        r"override",
    )
)


def detect_injection(text: str) -> list[str]:
    return [pattern.pattern for pattern in INJECTION_PATTERNS if pattern.search(text)]


def is_anomalous(
    analysis: Analysis,
    channel_credibility: float,
    injection_matches: list[str],
) -> bool:
    if analysis.certainty >= 0.98 and channel_credibility < 0.6:
        return True
    if injection_matches and analysis.certainty >= 0.8:
        return True
    return False


def apply_caps(analysis: Analysis, anomalous: bool) -> Analysis:
    if not anomalous:
        return analysis
    return analysis.model_copy(
        update={"certainty": min(analysis.certainty, 0.3), "is_tradable": False}
    )
