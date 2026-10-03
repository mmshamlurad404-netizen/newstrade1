from app.schemas.signal import Direction


def atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < period + 1:
        raise ValueError("not enough candles for ATR")
    ranges: list[float] = []
    for index in range(len(candles) - period, len(candles)):
        high = candles[index]["high"]
        low = candles[index]["low"]
        previous_close = candles[index - 1]["close"]
        ranges.append(
            max(high - low, abs(high - previous_close), abs(low - previous_close))
        )
    return sum(ranges) / period


def build_levels(
    direction: Direction,
    price: float,
    atr_value: float,
    atr_mult: float = 1.5,
    r_multiples: tuple[float, ...] = (1.5, 2.5, 4.0),
) -> tuple[float, list[float]]:
    risk = atr_mult * atr_value
    if direction == Direction.LONG:
        stop = price - risk
        take_profits = [price + risk * multiple for multiple in r_multiples]
    else:
        stop = price + risk
        take_profits = [price - risk * multiple for multiple in r_multiples]
    return stop, take_profits


def entry_zone(
    price: float, atr_value: float, band: float = 0.25
) -> tuple[float, float]:
    return price - band * atr_value, price + band * atr_value


def risk_reward(entry: float, stop: float, take_profit: float) -> float:
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0
    return abs(take_profit - entry) / risk
