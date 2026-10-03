from dataclasses import dataclass, field

from app.schemas.signal import Signal


@dataclass(frozen=True)
class RiskConfig:
    min_confidence: int = 60
    low_confidence: int = 75
    high_confidence: int = 85
    low_risk_pct: float = 0.005
    medium_risk_pct: float = 0.01
    high_risk_pct: float = 0.02
    max_positions: int = 3
    max_open_risk_pct: float = 0.05
    max_leverage: int = 5
    max_daily_loss_pct: float = 3.0
    max_weekly_loss_pct: float = 8.0
    max_spread_pct: float = 0.5
    max_position_vs_volume: float = 0.01
    min_risk_reward: float = 1.5


@dataclass
class RiskState:
    equity: float
    open_positions: int = 0
    open_risk_amount: float = 0.0
    correlated_risk_amount: float = 0.0
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    kill_switch: bool = False


@dataclass
class RiskDecision:
    approved: bool
    risk_pct: float = 0.0
    size: float = 0.0
    reasons: list[str] = field(default_factory=list)


def base_risk_pct(confidence: int, config: RiskConfig) -> float:
    if confidence < config.min_confidence:
        return 0.0
    if confidence < config.low_confidence:
        return config.low_risk_pct
    if confidence < config.high_confidence:
        return config.medium_risk_pct
    return config.high_risk_pct


def position_size(equity: float, risk_pct: float, entry: float, stop: float) -> float:
    per_unit_risk = abs(entry - stop)
    if per_unit_risk <= 0:
        raise ValueError("stop must differ from entry")
    return (equity * risk_pct) / per_unit_risk


def evaluate(
    signal: Signal,
    config: RiskConfig,
    state: RiskState,
    *,
    market_risk_factor: float,
    spread_pct: float,
    depth_ok: bool,
    beta_to_btc: float,
    volume_ok: bool = True,
) -> RiskDecision:
    reasons: list[str] = []

    if state.kill_switch:
        reasons.append("kill_switch")
    if state.daily_pnl_pct <= -abs(config.max_daily_loss_pct):
        reasons.append("daily_loss_limit")
    if state.weekly_pnl_pct <= -abs(config.max_weekly_loss_pct):
        reasons.append("weekly_loss_limit")
    if signal.confidence < config.min_confidence:
        reasons.append("low_confidence")
    if state.open_positions >= config.max_positions:
        reasons.append("max_positions")
    if signal.leverage_suggested > config.max_leverage:
        reasons.append("max_leverage")
    if spread_pct > config.max_spread_pct:
        reasons.append("spread")
    if not depth_ok:
        reasons.append("insufficient_depth")
    if not volume_ok:
        reasons.append("position_vs_volume")
    if signal.risk_reward < config.min_risk_reward:
        reasons.append("risk_reward")

    if reasons:
        return RiskDecision(approved=False, reasons=reasons)

    risk_pct = base_risk_pct(signal.confidence, config) * market_risk_factor
    size = position_size(state.equity, risk_pct, signal.entry_low, signal.stop_loss)
    if size <= 0:
        return RiskDecision(approved=False, reasons=["zero_size"])

    risk_amount = state.equity * risk_pct
    if state.open_risk_amount + risk_amount > state.equity * config.max_open_risk_pct:
        return RiskDecision(approved=False, reasons=["aggregate_open_risk"])

    projected_correlated = state.correlated_risk_amount + risk_amount * abs(beta_to_btc)
    if projected_correlated > state.equity * config.max_open_risk_pct:
        return RiskDecision(approved=False, reasons=["correlation"])

    return RiskDecision(approved=True, risk_pct=risk_pct, size=size)
