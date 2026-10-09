import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("analysis.jev")

EVENT_TYPE_OPTIONS: dict[str, str] = {
    "listing": "An exchange or platform listing a token for trading.",
    "delisting": "An exchange removing or suspending a token.",
    "hack": "A hack, exploit, breach, or funds drained or stolen.",
    "partnership": "A partnership, integration, or collaboration.",
    "regulation": "Regulatory action, lawsuit, ban, or ETF decision.",
    "unlock": "Token unlock, vesting release, or treasury movement.",
    "whale_movement": "Large on-chain transfer or whale positioning.",
    "macro": "Macro events such as CPI, rates, or central bank policy.",
    "adoption": "Institutional or mainstream adoption of crypto.",
    "other": "Crypto-relevant news that fits none of the categories above.",
}

SENTIMENT_OPTIONS: dict[str, str] = {
    "bullish": "The news is likely positive for prices.",
    "bearish": "The news is likely negative for prices.",
    "neutral": "The news is directional but not clearly positive or negative.",
}

URGENCY_OPTIONS: dict[str, str] = {
    "low": "Informational only, no near-term action needed.",
    "medium": "Worth watching within the day.",
    "high": "Likely to move markets within hours.",
    "critical": "Immediate, time-sensitive market-moving event.",
}

IMPACT_LEVELS = [
    "No market impact",
    "Minor, limited to a single small asset",
    "Moderate, visible price move likely",
    "Significant, broad asset or sector move",
    "Major, market-wide move",
]


@dataclass
class JevAssessment:
    useful: float
    event_type: str
    event_type_confidence: float
    sentiment: str
    sentiment_confidence: float
    urgency: str
    impact_score: float
    model: str = ""
    probabilities: dict[str, Any] = field(default_factory=dict)

    @property
    def is_useful(self) -> bool:
        return self.useful >= settings.jev_usefulness_min

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["is_useful"] = self.is_useful
        return data


def _load_sdk() -> Any | None:
    try:
        import typesafe_sdk
    except ImportError:
        return None
    return typesafe_sdk


class JevClient:
    """Thin async wrapper around TypeSafe's JEV ``system_one`` endpoint.

    The wrapper degrades gracefully: when no API key is configured, the SDK
    is not installed, or the request fails, ``assess`` returns ``None`` and
    the caller falls back to the keyword gate and the LLM analyzer.
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._sdk: Any | None = None

    @property
    def available(self) -> bool:
        if not settings.typesafe_api_key:
            return False
        return _load_sdk() is not None

    def _get_client(self) -> Any:
        if self._client is None:
            sdk = _load_sdk()
            if sdk is None:
                raise RuntimeError("typesafe-sdk is not installed")
            self._sdk = sdk
            self._client = sdk.TypeSafeClient(
                api_key=settings.typesafe_api_key,
                base_url=settings.typesafe_base_url,
                model=settings.typesafe_model,
                timeout=settings.typesafe_timeout_seconds,
            )
        return self._client

    def reset(self) -> None:
        self._client = None
        self._sdk = None

    def _build_questions(self) -> dict[str, Any]:
        sdk = _load_sdk()
        if sdk is None:
            raise RuntimeError("typesafe-sdk is not installed")
        return {
            "useful": sdk.Noul(
                instructions=(
                    "Is this news item useful and actionable for a crypto "
                    "trading decision, rather than spam, marketing, price "
                    "recaps, or unrelated content?"
                ),
                criteria={
                    "true": "Concrete, crypto-relevant, and potentially tradable.",
                    "false": "Spam, advertisement, recap, or not crypto-relevant.",
                },
            ),
            "event_type": sdk.Choice(
                instructions="What type of crypto market event is this news about?",
                criteria=EVENT_TYPE_OPTIONS,
            ),
            "sentiment": sdk.Choice(
                instructions="What is the market sentiment implied by this news?",
                criteria=SENTIMENT_OPTIONS,
            ),
            "urgency": sdk.Choice(
                instructions="How urgent is this news for a trader?",
                criteria=URGENCY_OPTIONS,
            ),
            "impact": sdk.Score(
                instructions="How large a market impact is this news likely to have?",
                criteria=IMPACT_LEVELS,
            ),
        }

    def _assess_sync(self, text: str) -> JevAssessment:
        client = self._get_client()
        response = client.system_one(state=text, questions=self._build_questions())

        useful = float(response.nouls["useful"].noul)
        event = response.choices["event_type"]
        sentiment = response.choices["sentiment"]
        urgency = response.choices["urgency"]
        impact = response.scores["impact"]

        return JevAssessment(
            useful=useful,
            event_type=event.choice,
            event_type_confidence=float(getattr(event, "confidence", 0.0) or 0.0),
            sentiment=sentiment.choice,
            sentiment_confidence=float(
                getattr(sentiment, "confidence", 0.0) or 0.0
            ),
            urgency=urgency.choice,
            impact_score=float(impact.score),
            model=getattr(response, "model", "") or "",
            probabilities={
                "event_type": dict(event.probabilities),
                "sentiment": dict(sentiment.probabilities),
                "urgency": dict(urgency.probabilities),
            },
        )

    async def assess(self, text: str) -> JevAssessment | None:
        if not self.available:
            return None
        if not text.strip():
            return None
        try:
            return await asyncio.to_thread(self._assess_sync, text)
        except Exception as exc:  # noqa: BLE001 - fall back to LLM/keyword path
            log.warning("jev assess failed: %s" % exc, extra={"stage": "analysis"})
            return None


_client: JevClient | None = None


def get_jev_client() -> JevClient:
    global _client
    if _client is None:
        _client = JevClient()
    return _client
