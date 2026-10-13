from app.services.observability import alerts


def _config(**over):
    base = dict(
        backlog_threshold=500,
        dlq_threshold=50,
        daily_loss_pct=3.0,
        open_risk_pct_max=5.0,
        cooldown_seconds=1800,
        ingestor_stale_seconds=120,
        ingestor_reconnect_spike=5,
    )
    base.update(over)
    return alerts.AlertConfig(**base)


def _eval(metrics, now=1000.0, state=None, equity=10000.0, **cfg):
    return alerts.evaluate(
        metrics, now, _config(**cfg), state or alerts.AlertState(), equity
    )


def test_healthy_metrics_fire_nothing():
    metrics = {
        "newstrade_stream_lag{stream=\"clustered_news\",group=\"pipeline\"}": 10,
        "newstrade_stream_length{stream=\"dlq\"}": 0,
        "newstrade_paper_realized_pnl_day": 5.0,
        "newstrade_paper_open_risk_pct": 1.0,
    }
    assert _eval(metrics) == []


def test_backlog_alert_fires_over_threshold():
    metrics = {
        "newstrade_stream_lag{stream=\"clustered_news\",group=\"pipeline\"}": 5615,
    }
    assert [a.key for a in _eval(metrics)] == ["backlog:clustered_news"]


def test_backlog_alert_sums_all_groups_for_stream():
    metrics = {
        "newstrade_stream_lag{stream=\"signals\",group=\"pipeline\"}": 300,
        "newstrade_stream_lag{stream=\"signals\",group=\"notifications\"}": 400,
    }
    assert [a.key for a in _eval(metrics)] == ["backlog:signals"]


def test_dlq_alert_is_critical():
    fired = _eval({"newstrade_stream_length{stream=\"dlq\"}": 120})
    assert len(fired) == 1
    assert fired[0].event_type == "alert_dlq"
    assert fired[0].severity == "critical"


def test_daily_loss_alert_uses_percent_of_equity():
    metrics = {"newstrade_paper_realized_pnl_day": -350.0}
    assert [a.key for a in _eval(metrics)] == ["daily_loss"]


def test_daily_loss_small_move_does_not_fire():
    assert _eval({"newstrade_paper_realized_pnl_day": -100.0}) == []


def test_risk_limit_alert():
    assert [a.key for a in _eval({"newstrade_paper_open_risk_pct": 6.5})] == [
        "risk_limit"
    ]


def test_cooldown_suppresses_repeat_alerts():
    metrics = {"newstrade_stream_length{stream=\"dlq\"}": 120}
    state = alerts.AlertState()

    first = alerts.evaluate(metrics, 1000.0, _config(), state, 10000.0)
    second = alerts.evaluate(metrics, 1100.0, _config(), state, 10000.0)
    third = alerts.evaluate(metrics, 3000.0, _config(), state, 10000.0)

    assert len(first) == 1
    assert second == []
    assert len(third) == 1


def test_ingestor_down_when_heartbeat_stale():
    metrics = {
        "newstrade_ingestor_seconds_since_heartbeat": 300,
        "newstrade_ingestor_connected": 1,
    }
    assert [a.key for a in _eval(metrics)] == ["ingestor_down"]


def test_ingestor_disconnected_when_fresh_but_offline():
    metrics = {
        "newstrade_ingestor_seconds_since_heartbeat": 10,
        "newstrade_ingestor_connected": 0,
    }
    fired = _eval(metrics)
    assert [a.key for a in fired] == ["ingestor_disconnected"]
    assert fired[0].event_type == "alert_ingestor_disconnected"


def test_ingestor_healthy_is_silent():
    metrics = {
        "newstrade_ingestor_seconds_since_heartbeat": 5,
        "newstrade_ingestor_connected": 1,
    }
    assert _eval(metrics) == []


def test_reconnect_spike_requires_two_samples():
    state = alerts.AlertState()
    first = _eval(
        {"newstrade_ingestor_reconnects_total": 2}, now=1000.0, state=state
    )
    second = _eval(
        {"newstrade_ingestor_reconnects_total": 9}, now=1060.0, state=state
    )
    assert first == []
    assert [a.key for a in second] == ["ingestor_reconnecting"]


def test_recovery_notice_on_falling_edge():
    state = alerts.AlertState()
    firing = {"newstrade_stream_length{stream=\"dlq\"}": 120}
    healed = {"newstrade_stream_length{stream=\"dlq\"}": 0}

    assert [a.key for a in _eval(firing, now=1000.0, state=state)] == ["dlq"]
    recovered = _eval(healed, now=1060.0, state=state)
    assert len(recovered) == 1
    assert recovered[0].event_type == "alert_recovered"
    assert recovered[0].key == "dlq"
    assert recovered[0].severity == "info"
    assert _eval(healed, now=1120.0, state=state) == []
