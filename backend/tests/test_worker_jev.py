from types import SimpleNamespace

import app.services.analysis.filter as relevance
import app.services.analysis.jev as jev
import app.services.analysis.worker as worker
from app.core.config import settings
from app.schemas.analysis import Analysis
from app.services.analysis.jev import JevAssessment


class _FakeSession:
    def __init__(self, news):
        self.news = news
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, model, pk):
        return self.news

    async def commit(self):
        self.commits += 1


def _fake_news():
    return SimpleNamespace(
        analysis_status="pending",
        discarded_reason=None,
        jev_assessment=None,
        coins=[],
        event_type=None,
        sentiment=None,
        sentiment_score=None,
        urgency=None,
        certainty=None,
        impact_timeframe=None,
        market_scope=None,
        asset_resolved=False,
        prompt_version=None,
        model_name=None,
        source_count=1,
    )


def _assessment(useful):
    return JevAssessment(
        useful=useful,
        event_type="regulation",
        event_type_confidence=0.7,
        sentiment="bearish",
        sentiment_confidence=0.6,
        urgency="high",
        impact_score=2.0,
        model="jev-test",
    )


class _FakeJev:
    def __init__(self, useful):
        self._useful = useful
        self.available = True

    async def assess(self, text):
        return _assessment(self._useful)


def _wire(monkeypatch, news, useful):
    session = _FakeSession(news)
    monkeypatch.setattr(worker, "async_session_factory", lambda: session)
    monkeypatch.setattr(relevance, "relevance_score", lambda text: 1.0)
    monkeypatch.setattr(settings, "fast_path_enabled", False)
    monkeypatch.setattr(jev, "get_jev_client", lambda: _FakeJev(useful))
    return session


async def test_gate_discards_low_usefulness(monkeypatch):
    news = _fake_news()
    _wire(monkeypatch, news, useful=0.1)

    await worker.analyze_news({"news_id": 1, "text": "SEC sues exchange", "posted_at": None})

    assert news.analysis_status == "discarded"
    assert news.discarded_reason == "low_usefulness:0.10"
    assert news.jev_assessment["event_type"] == "regulation"


async def test_gate_disabled_allows_analysis(monkeypatch):
    news = _fake_news()
    session = _wire(monkeypatch, news, useful=0.1)
    monkeypatch.setattr(settings, "jev_gate_enabled", False)

    captured = {}

    async def fake_analyze(text, channel, ts, coins_hint, jev_hint):
        captured["jev_hint"] = jev_hint
        return Analysis(
            is_tradable=True,
            coins=[],
            sentiment_score=0.0,
            certainty=0.5,
            summary="s",
        )

    async def fake_publish(_payload):
        return None

    monkeypatch.setattr(worker, "analyze", fake_analyze)
    monkeypatch.setattr(worker, "publish_analyzed", fake_publish)

    await worker.analyze_news({"news_id": 1, "text": "SEC sues exchange", "posted_at": None})

    assert news.analysis_status == "analyzed"
    assert session.commits == 1
    assert captured["jev_hint"] is not None
    assert captured["jev_hint"]["event_type"] == "regulation"
    assert news.jev_assessment["sentiment"] == "bearish"


async def test_useful_assessment_passes_hint_to_llm(monkeypatch):
    news = _fake_news()
    _wire(monkeypatch, news, useful=0.95)

    captured = {}

    async def fake_analyze(text, channel, ts, coins_hint, jev_hint):
        captured["jev_hint"] = jev_hint
        return Analysis(
            is_tradable=True,
            coins=[],
            sentiment_score=0.1,
            certainty=0.6,
            summary="s",
        )

    async def fake_publish(payload):
        captured["payload"] = payload

    monkeypatch.setattr(worker, "analyze", fake_analyze)
    monkeypatch.setattr(worker, "publish_analyzed", fake_publish)

    await worker.analyze_news({"news_id": 1, "text": "SEC sues exchange", "posted_at": None})

    assert news.analysis_status == "analyzed"
    assert captured["jev_hint"]["useful"] == 0.95
    assert captured["payload"]["jev"]["event_type"] == "regulation"
