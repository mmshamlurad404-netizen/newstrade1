from types import SimpleNamespace

import app.services.analysis.jev as jev
from app.core.config import settings
from app.services.analysis.jev import JevAssessment, JevClient


class _StubQuestion:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _StubSDK(SimpleNamespace):
    Noul = _StubQuestion
    Choice = _StubQuestion
    Score = _StubQuestion


class _FakeResponse:
    def __init__(self, useful=0.91):
        self.model = "jev-test"
        self.nouls = {"useful": SimpleNamespace(noul=useful)}
        self.choices = {
            "event_type": SimpleNamespace(
                choice="listing",
                confidence=0.87,
                probabilities={"listing": 0.87, "other": 0.13},
            ),
            "sentiment": SimpleNamespace(
                choice="bullish",
                confidence=0.8,
                probabilities={"bullish": 0.8, "bearish": 0.05, "neutral": 0.15},
            ),
            "urgency": SimpleNamespace(
                choice="high",
                confidence=0.7,
                probabilities={"high": 0.7, "medium": 0.3},
            ),
        }
        self.scores = {
            "impact": SimpleNamespace(
                score=3.2,
                legend={str(i): name for i, name in enumerate(jev.IMPACT_LEVELS)},
                probabilities={"3": 0.6, "4": 0.2},
            )
        }


class _FakeClient:
    def __init__(self, response=None, error=None):
        self._response = response or _FakeResponse()
        self._error = error

    def system_one(self, state, questions):
        if self._error:
            raise self._error
        assert "useful" in questions
        assert set(jev.EVENT_TYPE_OPTIONS) == set(
            questions["event_type"].kwargs["criteria"]
        )
        return self._response


def _patch_sdk_and_key(monkeypatch):
    monkeypatch.setattr(jev, "_load_sdk", lambda: _StubSDK())
    monkeypatch.setattr(settings, "typesafe_api_key", "test-key")


def test_available_requires_key(monkeypatch):
    monkeypatch.setattr(jev, "_load_sdk", lambda: _StubSDK())
    monkeypatch.setattr(settings, "typesafe_api_key", "")
    client = JevClient()
    assert client.available is False

    monkeypatch.setattr(settings, "typesafe_api_key", "test-key")
    assert client.available is True


def test_available_false_without_sdk(monkeypatch):
    monkeypatch.setattr(jev, "_load_sdk", lambda: None)
    monkeypatch.setattr(settings, "typesafe_api_key", "test-key")
    assert JevClient().available is False


def test_assess_parses_response(monkeypatch):
    _patch_sdk_and_key(monkeypatch)
    client = JevClient()
    monkeypatch.setattr(client, "_get_client", lambda: _FakeClient())

    result = client._assess_sync("Binance will list SOL on spot")

    assert isinstance(result, JevAssessment)
    assert result.useful == 0.91
    assert result.event_type == "listing"
    assert result.event_type_confidence == 0.87
    assert result.sentiment == "bullish"
    assert result.urgency == "high"
    assert result.impact_score == 3.2
    assert result.model == "jev-test"
    assert result.probabilities["sentiment"]["bullish"] == 0.8
    assert result.is_useful is True


def test_is_useful_respects_threshold(monkeypatch):
    monkeypatch.setattr(settings, "jev_usefulness_min", 0.5)
    assert JevAssessment(0.4, "other", 0.5, "neutral", 0.5, "low", 0.0).is_useful is False
    assert JevAssessment(0.6, "other", 0.5, "neutral", 0.5, "low", 0.0).is_useful is True


async def test_assess_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "typesafe_api_key", "")
    client = JevClient()
    assert await client.assess("any text") is None


async def test_assess_returns_none_on_error(monkeypatch):
    _patch_sdk_and_key(monkeypatch)
    client = JevClient()
    monkeypatch.setattr(client, "_get_client", lambda: _FakeClient(error=RuntimeError("boom")))
    assert await client.assess("some news") is None


async def test_assess_returns_none_for_blank(monkeypatch):
    _patch_sdk_and_key(monkeypatch)
    client = JevClient()
    monkeypatch.setattr(client, "_get_client", lambda: _FakeClient())
    assert await client.assess("   ") is None


async def test_assess_runs_sync_call(monkeypatch):
    _patch_sdk_and_key(monkeypatch)
    client = JevClient()
    monkeypatch.setattr(client, "_get_client", lambda: _FakeClient())
    result = await client.assess("Binance will list SOL")
    assert result is not None
    assert result.event_type == "listing"
