from dataclasses import dataclass
from datetime import datetime

from app.schemas.signal import Direction
from app.services.trading.paper import check_exit, compute_pnl


@dataclass(frozen=True)
class ExitDecision:
    reason: str
    exit_price: float
    pnl: float
    pnl_pct: float


def evaluate_exit(
    *,
    direction: Direction,
    entry_price: float,
    quantity: float,
    fees: float,
    stop_loss: float,
    take_profit: float,
    candle: dict,
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> ExitDecision | None:
    reason, exit_price = check_exit(direction, candle, stop_loss, take_profit)
    if reason is None:
        if expires_at is not None and now is not None and now >= expires_at:
            reason = "expired"
            exit_price = candle["close"]
        else:
            return None
    pnl, pnl_pct = compute_pnl(
        direction, entry_price, float(exit_price), quantity, fees
    )
    return ExitDecision(
        reason=reason, exit_price=float(exit_price), pnl=pnl, pnl_pct=pnl_pct
    )


def rollup_pnl_pct(realized_pnl: float, equity: float) -> float:
    if equity <= 0:
        return 0.0
    return realized_pnl / equity * 100.0
