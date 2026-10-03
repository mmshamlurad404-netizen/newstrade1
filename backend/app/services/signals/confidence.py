EVENT_SEVERITY = {
    "listing": 0.8,
    "delisting": 0.8,
    "hack": 0.9,
    "partnership": 0.5,
    "regulation": 0.7,
    "unlock": 0.6,
    "whale_movement": 0.5,
    "macro": 0.7,
    "adoption": 0.5,
    "other": 0.3,
}

W_SOURCE = 0.30
W_CERTAINTY = 0.25
W_CORROBORATION = 0.25
W_CONVICTION = 0.20


def corroboration_score(independent_origins: int) -> float:
    return min(1.0, independent_origins / 4.0)


def conviction_strength(sentiment_score: float, event_type: str) -> float:
    severity = EVENT_SEVERITY.get(event_type, 0.3)
    value = 0.6 * abs(sentiment_score) + 0.4 * severity
    return max(0.0, min(1.0, value))


def compute_confidence(
    source_credibility: float,
    llm_certainty: float,
    independent_origins: int,
    sentiment_score: float,
    event_type: str,
) -> int:
    corroboration = corroboration_score(independent_origins)
    conviction = conviction_strength(sentiment_score, event_type)
    raw = (
        W_SOURCE * max(0.0, min(1.0, source_credibility))
        + W_CERTAINTY * max(0.0, min(1.0, llm_certainty))
        + W_CORROBORATION * corroboration
        + W_CONVICTION * conviction
    )
    return int(round(100 * max(0.0, min(1.0, raw))))


def market_risk_factor(
    btc_atr_pct: float,
    asset_atr_pct: float,
    spread_pct: float,
    macro_window: bool,
) -> float:
    penalty = 0.0
    if btc_atr_pct > 5.0:
        penalty += 0.2
    if asset_atr_pct > 8.0:
        penalty += 0.2
    if spread_pct > 0.3:
        penalty += 0.2
    if macro_window:
        penalty += 0.1
    return max(0.3, min(1.0, 1.0 - penalty))


def veto_reasons(
    spread_pct: float,
    max_spread_pct: float,
    depth_ok: bool,
    kill_switch: bool,
    daily_pnl_pct: float,
    max_daily_loss_pct: float,
    weekly_pnl_pct: float,
    max_weekly_loss_pct: float,
) -> list[str]:
    reasons: list[str] = []
    if kill_switch:
        reasons.append("kill_switch")
    if spread_pct > max_spread_pct:
        reasons.append("spread")
    if not depth_ok:
        reasons.append("insufficient_depth")
    if daily_pnl_pct <= -abs(max_daily_loss_pct):
        reasons.append("daily_loss_limit")
    if weekly_pnl_pct <= -abs(max_weekly_loss_pct):
        reasons.append("weekly_loss_limit")
    return reasons
