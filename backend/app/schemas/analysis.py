from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    listing = "listing"
    delisting = "delisting"
    hack = "hack"
    partnership = "partnership"
    regulation = "regulation"
    unlock = "unlock"
    whale_movement = "whale_movement"
    macro = "macro"
    adoption = "adoption"
    other = "other"


class Sentiment(str, Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AnalysisStatus(str, Enum):
    pending = "pending"
    discarded = "discarded"
    analyzed = "analyzed"
    failed = "failed"


class Analysis(BaseModel):
    is_tradable: bool
    coins: list[str] = Field(default_factory=list)
    event_type: EventType = EventType.other
    sentiment: Sentiment = Sentiment.neutral
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    urgency: Urgency = Urgency.low
    certainty: float = Field(ge=0.0, le=1.0)
    summary: str
    impact_timeframe: str = "intraday"
    market_scope: str = "single_asset"
    reasoning: str = ""

    @field_validator("coins")
    @classmethod
    def uppercase_coins(cls, value: list[str]) -> list[str]:
        return [coin.upper() for coin in value]


class FastAlert(BaseModel):
    event_type: str
    coin: str
    matched_text: str
    posted_at: datetime | None = None
