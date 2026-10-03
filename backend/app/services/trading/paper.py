from datetime import datetime, timezone

from app.schemas.signal import Direction


def simulate_entry(
    *,
    signal_id: str,
    asset: str,
    direction: Direction,
    entry_price: float,
    quantity: float,
    fee_bps: float = 5.0,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    fees = entry_price * quantity * (fee_bps / 10_000.0)
    return {
        "signal_id": signal_id,
        "asset": asset,
        "direction": direction.value,
        "entry_price": entry_price,
        "quantity": quantity,
        "fees": fees,
        "opened_at": now.isoformat(),
    }


def check_exit(
    direction: Direction,
    candle: dict,
    stop_loss: float,
    take_profit: float,
) -> tuple[str | None, float | None]:
    if direction == Direction.LONG:
        if candle["low"] <= stop_loss:
            return "stop_loss", stop_loss
        if candle["high"] >= take_profit:
            return "take_profit", take_profit
    else:
        if candle["high"] >= stop_loss:
            return "stop_loss", stop_loss
        if candle["low"] <= take_profit:
            return "take_profit", take_profit
    return None, None


def compute_pnl(
    direction: Direction,
    entry_price: float,
    exit_price: float,
    quantity: float,
    fees: float = 0.0,
) -> tuple[float, float]:
    if direction == Direction.LONG:
        gross = (exit_price - entry_price) * quantity
    else:
        gross = (entry_price - exit_price) * quantity
    pnl = gross - fees
    notional = entry_price * quantity
    pnl_pct = (pnl / notional * 100) if notional else 0.0
    return pnl, pnl_pct
