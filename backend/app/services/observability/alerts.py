"""Rule-based alerts over the shared-state metrics.

Alerts are evaluated on a fixed interval by ``monitor.py``. Rules are pure
functions of the metric snapshot plus a per-key ``last_fired`` timestamp map
used for debouncing, so they are easy to unit test.
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
    backlog_streams: tuple[str, ...] = (
        "clustered_news",
        "analyzed_news",
        "signals",
    )


def _val(metrics: dict[str, float], name: str) -> float:
    return float(metrics.get(name, 0.0))


def _stream_lag(metrics: dict[str, float], stream: str) -> float:
    prefix = f'newstrade_stream_lag{{stream="{stream}"'
    return float(sum(v for k, v in metrics.items() if k.startswith(prefix)))


def _stream_length(metrics: dict[str, float], stream: str) -> float:
    return _val(metrics, f'newstrade_stream_length{{stream="{stream}"}}')


def evaluate(
    metrics: dict[str, float],
    now: float,
    config: AlertConfig,
    last_fired: dict[str, float],
    equity: float,
) -> list[Alert]:
    candidates: list[Alert] = []

    for stream in config.backlog_streams:
        lag = _stream_lag(metrics, stream)
        if lag > config.backlog_threshold:
            candidates.append(
                Alert(
                    key=f"backlog:{stream}",
                    event_type="alert_backlog",
                    title=f"Queue backlog on {stream}",
                    body=f"{int(lag)} undelivered entries exceed {config.backlog_threshold}",
                    payload={"stream": stream, "lag": lag},
                )
            )

    dlq = _stream_length(metrics, "dlq")
    if dlq > config.dlq_threshold:
        candidates.append(
            Alert(
                key="dlq",
                event_type="alert_dlq",
                title="Dead-letter queue growing",
                body=f"{int(dlq)} failed items in the DLQ exceed {config.dlq_threshold}",
                severity="critical",
                payload={"dlq": dlq},
            )
        )

    if equity > 0:
        day_pnl = _val(metrics, "newstrade_paper_realized_pnl_day")
        day_pct = day_pnl / equity * 100.0
        if day_pct <= -abs(config.daily_loss_pct):
            candidates.append(
                Alert(
                    key="daily_loss",
                    event_type="alert_daily_loss",
                    title="Daily loss limit hit",
                    body=f"Realized day PnL {day_pct:.2f}% breaches -{config.daily_loss_pct:.2f}%",
                    severity="critical",
                    payload={"day_pnl": day_pnl, "day_pct": day_pct},
                )
            )

    open_risk = _val(metrics, "newstrade_paper_open_risk_pct")
    if open_risk > config.open_risk_pct_max:
        candidates.append(
            Alert(
                key="risk_limit",
                event_type="alert_risk_limit",
                title="Open risk above cap",
                body=f"Open risk {open_risk:.2f}% exceeds {config.open_risk_pct_max:.2f}%",
                payload={"open_risk_pct": open_risk},
            )
        )

    fired: list[Alert] = []
    for alert in candidates:
        previous = last_fired.get(alert.key)
        if previous is not None and now - previous < config.cooldown_seconds:
            continue
        last_fired[alert.key] = now
        fired.append(alert)
    return fired
