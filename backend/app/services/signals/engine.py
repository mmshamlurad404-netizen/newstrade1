import uuid
from datetime import datetime, timedelta, timezone

from app.schemas.signal import Direction, Signal, SignalStatus
from app.services.signals.confidence import (
    compute_confidence,
    market_risk_factor,
)
from app.services.signals.levels import atr, build_levels, entry_zone, risk_reward

TIMEFRAME_EXPIRY_MINUTES = {"scalp": 15, "intraday": 240, "swing": 4320}
TIMEFRAME_CANDLE = {"scalp": "1m", "intraday": "15m", "swing": "1h"}

EVENT_DIRECTION = {
    "listing": "LONG",
    "delisting": "SHORT",
    "hack": "SHORT",
    "partnership": "LONG",
    "unlock": "SHORT",
    "adoption": "LONG",
}


def direction_for(event_type: str, sentiment: str) -> Direction:
    mapped = EVENT_DIRECTION.get(event_type)
    if mapped is not None:
        return Direction(mapped)
    if sentiment == "bullish":
        return Direction.LONG
    if sentiment == "bearish":
        return Direction.SHORT
    return Direction.NO_TRADE


def deterministic_signal_id(
    news_id: int, asset: str, direction: Direction, timeframe: str
) -> str:
    key = f"{news_id}:{asset}:{direction.value}:{timeframe}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def build_signal(
    *,
    news_id: int,
    asset: str,
    event_type: str,
    sentiment: str,
    sentiment_score: float,
    certainty: float,
    source_credibility: float,
    independent_origins: int,
    price: float,
    candles: list[dict],
    impact_timeframe: str,
    prompt_version: str,
    leverage_suggested: int = 1,
    now: datetime | None = None,
) -> tuple[Signal | None, str | None]:
    now = now or datetime.now(timezone.utc)
    direction = direction_for(event_type, sentiment)
    if direction == Direction.NO_TRADE:
        return None, "no_direction"

    if len(candles) < 15:
        return None, "insufficient_candles"

    atr_value = atr(candles)
    if atr_value <= 0:
        return None, "zero_atr"

    stop, take_profits = build_levels(direction, price, atr_value)
    entry_low, entry_high = entry_zone(price, atr_value)
    reward_risk = risk_reward(price, stop, take_profits[0])
    if reward_risk < 1.5:
        return None, "low_risk_reward"

    confidence = compute_confidence(
        source_credibility=source_credibility,
        llm_certainty=certainty,
        independent_origins=independent_origins,
        sentiment_score=sentiment_score,
        event_type=event_type,
    )
    asset_atr_pct = (atr_value / price * 100) if price else 0.0
    mrf = market_risk_factor(
        btc_atr_pct=0.0,
        asset_atr_pct=asset_atr_pct,
        spread_pct=0.0,
        macro_window=False,
    )

    timeframe = TIMEFRAME_CANDLE.get(impact_timeframe, "15m")
    expires_at = now + timedelta(
        minutes=TIMEFRAME_EXPIRY_MINUTES.get(impact_timeframe, 240)
    )
    signal = Signal(
        signal_id=deterministic_signal_id(news_id, asset, direction, timeframe),
        news_id=news_id,
        asset=asset,
        direction=direction,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop,
        take_profits=take_profits,
        leverage_suggested=leverage_suggested,
        timeframe=timeframe,
        confidence=confidence,
        market_risk_factor=mrf,
        rationale=f"{event_type} {sentiment}",
        prompt_version=prompt_version,
        created_at=now,
        expires_at=expires_at,
        risk_reward=reward_risk,
        status=SignalStatus.new,
    )
    return signal, None
