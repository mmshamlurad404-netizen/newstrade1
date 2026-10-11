import httpx
import pytest

from app.core.config import settings
from app.services.analysis import llm


VALID_JSON = (
    '{"is_tradable": true, "coins": ["BTC"], "sentiment_score": 0.5, '
    '"certainty": 0.7, "summary": "ok"}'
)


def _usage(prompt=100, completion=20):
    return {"prompt_tokens": prompt, "completion_tokens": completion}


async def test_analyze_uses_primary_provider(monkeypatch):
    calls = []

    async def fake_post(provider, messages):
        calls.append(provider.name)
        return VALID_JSON, _usage()

    monkeypatch.setattr(llm, "_post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_model", "")

    result = await llm.analyze("text", "chan", "2024-01-01")

    assert calls == ["primary"]
    assert result.provider == "primary"
    assert result.model == settings.llm_model
    assert result.analysis.coins == ["BTC"]


async def test_transport_error_falls_back_to_secondary(monkeypatch):
    calls = []

    async def fake_post(provider, messages):
        calls.append(provider.name)
        if provider.name == "primary":
            raise httpx.ConnectError("boom")
        return VALID_JSON, _usage()

    monkeypatch.setattr(llm, "_post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_model", "backup-model")

    result = await llm.analyze("text", "chan", "2024-01-01")

    assert calls == ["primary", "fallback"]
    assert result.provider == "fallback"
    assert result.model == "backup-model"


async def test_invalid_json_exhausts_retries_then_falls_back(monkeypatch):
    calls = []

    async def fake_post(provider, messages):
        calls.append(provider.name)
        if provider.name == "primary":
            return "not json", _usage()
        return VALID_JSON, _usage()

    monkeypatch.setattr(llm, "_post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_model", "backup-model")
    monkeypatch.setattr(settings, "llm_max_retries", 2)

    result = await llm.analyze("text", "chan", "2024-01-01")

    assert calls == ["primary", "primary", "primary", "fallback"]
    assert result.provider == "fallback"


async def test_no_fallback_raises_analysis_error(monkeypatch):
    async def fake_post(provider, messages):
        return "not json", _usage()

    monkeypatch.setattr(llm, "_post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_model", "")
    monkeypatch.setattr(settings, "llm_max_retries", 1)

    with pytest.raises(llm.AnalysisError):
        await llm.analyze("text", "chan", "2024-01-01")


async def test_cost_is_computed_from_usage_and_prices(monkeypatch):
    async def fake_post(provider, messages):
        return VALID_JSON, _usage(prompt=2000, completion=1000)

    monkeypatch.setattr(llm, "_post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_model", "")
    monkeypatch.setattr(settings, "llm_input_cost_per_1k", 0.5)
    monkeypatch.setattr(settings, "llm_output_cost_per_1k", 1.5)

    result = await llm.analyze("text", "chan", "2024-01-01")

    assert result.prompt_tokens == 2000
    assert result.completion_tokens == 1000
    assert result.cost_usd == pytest.approx(0.5 * 2 + 1.5 * 1)


def test_estimate_cost_zero_when_prices_unset(monkeypatch):
    monkeypatch.setattr(settings, "llm_input_cost_per_1k", 0.0)
    monkeypatch.setattr(settings, "llm_output_cost_per_1k", 0.0)
    assert llm.estimate_cost(1000, 1000) == 0.0
