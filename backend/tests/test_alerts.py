from app.services.observability import alerts


def _config(**over):
    base = dict(
        backlog_threshold=500,
        dlq_threshold=50,
        daily_loss_pct=3.0,
        open_risk_pct_max=5.0,
        cooldown_seconds=1800,
    )
    base.update(over)
    return alerts.AlertConfig(**base)


def test_healthy_metrics_fire_nothing():
    metrics = {
        "newstrade_stream_lag{stream=\"clustered_news\",group=\"pipeline\"}": 10,
        "newstrade_stream_length{stream=\"dlq\"}": 0,
        "newstrade_paper_realized_pnl_day": 5.0,
        "newstrade_paper_open_risk_pct": 1.0,
    }
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    assert fired == []


def test_backlog_alert_fires_over_threshold():
    metrics = {
        "newstrade_stream_lag{stream=\"clustered_news\",group=\"pipeline\"}": 5615,
    }
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    keys = [a.key for a in fired]
    assert "backlog:clustered_news" in keys


def test_backlog_alert_sums_all_groups_for_stream():
    metrics = {
        "newstrade_stream_lag{stream=\"signals\",group=\"pipeline\"}": 300,
        "newstrade_stream_lag{stream=\"signals\",group=\"notifications\"}": 400,
    }
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    assert [a.key for a in fired] == ["backlog:signals"]


def test_dlq_alert_is_critical():
    metrics = {"newstrade_stream_length{stream=\"dlq\"}": 120}
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    assert len(fired) == 1
    assert fired[0].event_type == "alert_dlq"
    assert fired[0].severity == "critical"


def test_daily_loss_alert_uses_percent_of_equity():
    metrics = {"newstrade_paper_realized_pnl_day": -350.0}
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    assert [a.key for a in fired] == ["daily_loss"]


def test_daily_loss_small_move_does_not_fire():
    metrics = {"newstrade_paper_realized_pnl_day": -100.0}
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    assert fired == []


def test_risk_limit_alert():
    metrics = {"newstrade_paper_open_risk_pct": 6.5}
    fired = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired={}, equity=10000.0)
    assert [a.key for a in fired] == ["risk_limit"]


def test_cooldown_suppresses_repeat_alerts():
    metrics = {"newstrade_stream_length{stream=\"dlq\"}": 120}
    last_fired: dict[str, float] = {}

    first = alerts.evaluate(metrics, now=1000.0, config=_config(), last_fired=last_fired, equity=10000.0)
    second = alerts.evaluate(metrics, now=1100.0, config=_config(), last_fired=last_fired, equity=10000.0)
    third = alerts.evaluate(metrics, now=3000.0, config=_config(), last_fired=last_fired, equity=10000.0)

    assert len(first) == 1
    assert second == []
    assert len(third) == 1
