"""Rule-based alerts over the shared-state metrics.

Alerts are evaluated on a fixed interval by ``monitor.py``. The rule set is a
pure function of the metric snapshot plus an ``AlertState`` that tracks which
conditions are currently firing (for recovery notices), when each key last
alerted (for debouncing), and the previous values of monotonic counters (for
spike detection).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Alert:
    key: str
    event_type: str
    title: str
    body: str
    severity: str = "warning"
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AlertConfig:
    backlog_threshold: int = 500
    dlq_threshold: int = 50
    daily_loss_pct: float = 3.0
    open_risk_pct_max: float = 5.0
    cooldown_seconds: int = 1800
    ingestor_stale_seconds: int = 120
    ingestor_reconnect_spike: int = 5
    backlog_streams: tuple[str, ...] = (
        "clustered_news",
        "analyzed_news",
        "signals",
    )


@dataclass
class AlertState:
    last_fired: dict[str, float] = field(default_factory=dict)
    active: dict[str, Alert] = field(default_factory=dict)
    prev: dict[str, float] = field(default_factory=dict)


def _val(metrics: dict[str, float], name: str) -> float:
    return float(metrics.get(name, 0.0))


def _has(metrics: dict[str, float], name: str) -> bool:
    return name in metrics


def _stream_lag(metrics: dict[str, float], stream: str) -> float:
    prefix = f'newstrade_stream_lag{{stream="{stream}"'
    return float(sum(v for k, v in metrics.items() if k.startswith(prefix)))


def _stream_length(metrics: dict[str, float], stream: str) -> float:
    return _val(metrics, f'newstrade_stream_length{{stream="{stream}"}}')


def _candidates(
    metrics: dict[str, float],
    config: AlertConfig,
    equity: float,
    reconnect_delta: float | None,
) -> dict[str, Alert]:
    found: dict[str, Alert] = {}

    for stream in config.backlog_streams:
        lag = _stream_lag(metrics, stream)
        if lag > config.backlog_threshold:
            found[f"backlog:{stream}"] = Alert(
                key=f"backlog:{stream}",
                event_type="alert_backlog",
                title=f"Queue backlog on {stream}",
                body=f"{int(lag)} undelivered entries exceed {config.backlog_threshold}",
                payload={"stream": stream, "lag": lag},
            )

    dlq = _stream_length(metrics, "dlq")
    if dlq > config.dlq_threshold:
        found["dlq"] = Alert(
            key="dlq",
            event_type="alert_dlq",
            title="Dead-letter queue growing",
            body=f"{int(dlq)} failed items in the DLQ exceed {config.dlq_threshold}",
            severity="critical",
            payload={"dlq": dlq},
        )

    if equity > 0:
        day_pnl = _val(metrics, "newstrade_paper_realized_pnl_day")
        day_pct = day_pnl / equity * 100.0
        if day_pct <= -abs(config.daily_loss_pct):
            found["daily_loss"] = Alert(
                key="daily_loss",
                event_type="alert_daily_loss",
                title="Daily loss limit hit",
                body=f"Realized day PnL {day_pct:.2f}% breaches -{config.daily_loss_pct:.2f}%",
                severity="critical",
                payload={"day_pnl": day_pnl, "day_pct": day_pct},
            )

    open_risk = _val(metrics, "newstrade_paper_open_risk_pct")
    if open_risk > config.open_risk_pct_max:
        found["risk_limit"] = Alert(
            key="risk_limit",
            event_type="alert_risk_limit",
            title="Open risk above cap",
            body=f"Open risk {open_risk:.2f}% exceeds {config.open_risk_pct_max:.2f}%",
            payload={"open_risk_pct": open_risk},
        )

    if _has(metrics, "newstrade_ingestor_seconds_since_heartbeat"):
        stale = _val(metrics, "newstrade_ingestor_seconds_since_heartbeat")
        connected = _val(metrics, "newstrade_ingestor_connected") == 1
        if stale > config.ingestor_stale_seconds:
            found["ingestor_down"] = Alert(
                key="ingestor_down",
                event_type="alert_ingestor_down",
                title="Ingestor is not reporting",
                body=f"No heartbeat for {int(stale)}s (limit {config.ingestor_stale_seconds}s)",
                severity="critical",
                payload={"seconds_since_heartbeat": stale},
            )
        elif not connected:
            found["ingestor_disconnected"] = Alert(
                key="ingestor_disconnected",
                event_type="alert_ingestor_disconnected",
                title="Ingestor disconnected",
                body="Telegram session is disconnected; reconnect in progress",
                payload={},
            )

    if (
        reconnect_delta is not None
        and reconnect_delta >= config.ingestor_reconnect_spike
    ):
        found["ingestor_reconnecting"] = Alert(
            key="ingestor_reconnecting",
            event_type="alert_ingestor_reconnecting",
            title="Ingestor reconnecting frequently",
            body=f"{int(reconnect_delta)} reconnects since the last check",
            payload={"reconnects": reconnect_delta},
        )

    return found


def evaluate(
    metrics: dict[str, float],
    now: float,
    config: AlertConfig,
    state: AlertState,
    equity: float,
) -> list[Alert]:
    reconnects = _val(metrics, "newstrade_ingestor_reconnects_total")
    previous = state.prev.get("reconnects")
    reconnect_delta = None if previous is None else reconnects - previous
    state.prev["reconnects"] = reconnects

    current = _candidates(metrics, config, equity, reconnect_delta)

    fired: list[Alert] = []
    for key, alert in current.items():
        entering = key not in state.active
        previous_fire = state.last_fired.get(key)
        if (
            entering
            or previous_fire is None
            or now - previous_fire >= config.cooldown_seconds
        ):
            state.last_fired[key] = now
            fired.append(alert)

    for key, alert in state.active.items():
        if key not in current:
            fired.append(
                Alert(
                    key=key,
                    event_type="alert_recovered",
                    title=f"Recovered: {alert.title}",
                    body=f"{alert.title} condition cleared",
                    severity="info",
                    payload=alert.payload,
                )
            )

    state.active = current
    return fired
