from app.services.observability import metrics


class FakeRedis:
    def __init__(self, lengths=None, groups=None, fail=(), ingestor=None):
        self._lengths = lengths or {}
        self._groups = groups or {}
        self._fail = set(fail)
        self._ingestor = ingestor or {}

    async def xlen(self, stream):
        if stream in self._fail:
            raise RuntimeError("no redis")
        return self._lengths.get(stream, 0)

    async def xinfo_groups(self, stream):
        if stream in self._fail:
            raise RuntimeError("no redis")
        return self._groups.get(stream, [])

    async def hgetall(self, key):
        return self._ingestor


def _patch(session_val, monkeypatch):
    async def news(_s):
        return {"analyzed": 12, "discarded": 3, "pending": 1}

    async def signals(_s):
        return {"active": 4, "rejected": 2}

    async def orders(_s):
        return {"filled": 5, "pending": 1}

    async def paper(_s):
        return {
            "open": 2,
            "closed": 6,
            "realized_pnl": 123.5,
            "realized_pnl_day": -50.0,
            "realized_pnl_week": 10.0,
            "open_risk_pct": 1.25,
            "wins": 4,
            "losses": 2,
        }

    async def trades(_s):
        return {"open": 1, "closed": 0, "realized_pnl": 0.0}

    async def channels(_s):
        return {"total": 101, "feed_active": 99, "telegram_active": 2}

    monkeypatch.setattr(metrics, "_news_counts", news)
    monkeypatch.setattr(metrics, "_signal_counts", signals)
    monkeypatch.setattr(metrics, "_order_counts", orders)
    monkeypatch.setattr(metrics, "_paper_stats", paper)
    monkeypatch.setattr(metrics, "_trade_stats", trades)
    monkeypatch.setattr(metrics, "_channel_stats", channels)


async def test_collect_assembles_db_and_redis_samples(monkeypatch):
    _patch(None, monkeypatch)
    redis = FakeRedis(
        lengths={metrics.queue.RAW_STREAM: 42},
        groups={
            metrics.queue.RAW_STREAM: [
                {"name": "pipeline", "pending": 3, "lag": 7}
            ]
        },
    )

    samples = await metrics.collect(None, redis)
    data = metrics.to_dict(samples)

    assert data["newstrade_news_total{status=\"analyzed\"}"] == 12
    assert data["newstrade_signals_total{status=\"active\"}"] == 4
    assert data["newstrade_orders_total{status=\"filled\"}"] == 5
    assert data["newstrade_paper_trades_open"] == 2
    assert data["newstrade_paper_realized_pnl"] == 123.5
    assert data["newstrade_paper_realized_pnl_day"] == -50.0
    assert data["newstrade_paper_open_risk_pct"] == 1.25
    assert data["newstrade_trades_open"] == 1
    assert data["newstrade_channels_total"] == 101
    assert data["newstrade_channels_active{kind=\"feed\"}"] == 99
    assert data["newstrade_stream_length{stream=\"raw_news\"}"] == 42
    assert data["newstrade_stream_pending{stream=\"raw_news\",group=\"pipeline\"}"] == 3
    assert data["newstrade_stream_lag{stream=\"raw_news\",group=\"pipeline\"}"] == 7


async def test_collect_degrades_when_redis_unavailable(monkeypatch):
    _patch(None, monkeypatch)
    redis = FakeRedis(fail={metrics.queue.RAW_STREAM})

    samples = await metrics.collect(None, redis)
    data = metrics.to_dict(samples)

    assert data["newstrade_stream_length{stream=\"raw_news\"}"] == 0
    assert "newstrade_stream_pending{stream=\"raw_news\",group=\"pipeline\"}" not in data


async def test_collect_includes_ingestor_state(monkeypatch):
    _patch(None, monkeypatch)
    import time as _time

    now = _time.time()
    redis = FakeRedis(
        ingestor={
            "connected": "1",
            "reconnects": "3",
            "heartbeat": str(now - 5),
            "last_event": str(now - 30),
        }
    )

    samples = await metrics.collect(None, redis)
    data = metrics.to_dict(samples)

    assert data["newstrade_ingestor_connected"] == 1
    assert data["newstrade_ingestor_reconnects_total"] == 3
    assert 0 <= data["newstrade_ingestor_seconds_since_heartbeat"] < 10
    assert 25 <= data["newstrade_ingestor_seconds_since_event"] < 40


async def test_collect_omits_ingestor_when_absent(monkeypatch):
    _patch(None, monkeypatch)
    redis = FakeRedis()
    data = metrics.to_dict(await metrics.collect(None, redis))
    assert "newstrade_ingestor_connected" not in data


def test_render_prometheus_format():
    samples = [
        metrics.Sample(
            "newstrade_news_total",
            12,
            type="counter",
            help="News items",
            labels=(("status", "analyzed"),),
        ),
        metrics.Sample("newstrade_build_info", 1),
    ]
    text = metrics.render(samples)

    assert "# HELP newstrade_news_total News items" in text
    assert "# TYPE newstrade_news_total counter" in text
    assert 'newstrade_news_total{status="analyzed"} 12' in text
    assert "newstrade_build_info 1" in text
    assert text.endswith("\n")


def test_fmt_handles_ints_and_floats():
    assert metrics._fmt(3.0) == "3"
    assert metrics._fmt(123.5) == "123.5"
