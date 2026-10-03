from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class SignalStatus(str, Enum):
    new = "new"
    active = "active"
    filled = "filled"
    closed = "closed"
    expired = "expired"
    rejected = "rejected"
    cancelled = "cancelled"


class Mode(str, Enum):
    paper = "paper"
    manual_live = "manual_live"
    auto_live = "auto_live"


class Signal(BaseModel):
    signal_id: str
    news_id: int
    asset: str
    direction: Direction
    entry_low: float
    entry_high: float
    order_type: str = "limit"
    stop_loss: float
    take_profits: list[float]
    leverage_suggested: int = 1
    timeframe: str = "1h"
    confidence: int
    market_risk_factor: float = 1.0
    risk_pct: float = 0.0
    rationale: str = ""
    source_news_ids: list[str] = Field(default_factory=list)
    prompt_version: str = ""
    created_at: datetime
    expires_at: datetime
    risk_reward: float = 0.0
    status: SignalStatus = SignalStatus.new
