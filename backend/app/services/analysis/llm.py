from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.analysis import Analysis
from app.services.analysis import prompt as prompt_module

log = get_logger("analysis.llm")


class AnalysisError(RuntimeError):
    pass


class _ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResult:
    analysis: Analysis
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class _Provider:
    name: str
    base_url: str
    api_key: str
    model: str


def _providers() -> list[_Provider]:
    primary = _Provider(
        "primary", settings.llm_base_url, settings.llm_api_key, settings.llm_model
    )
    providers = [primary]
    if settings.llm_fallback_model:
        providers.append(
            _Provider(
                "fallback",
                settings.llm_fallback_base_url or settings.llm_base_url,
                settings.llm_fallback_api_key or settings.llm_api_key,
                settings.llm_fallback_model,
            )
        )
    return providers


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens / 1000.0 * settings.llm_input_cost_per_1k
        + completion_tokens / 1000.0 * settings.llm_output_cost_per_1k
    )


async def _post(provider: _Provider, messages: list[dict]) -> tuple[str, dict]:
    url = f"{provider.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {provider.api_key}"}
    payload = {
        "model": provider.model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"], data.get("usage") or {}


async def _call_provider(
    provider: _Provider, messages: list[dict]
) -> LLMResult:
    for attempt in range(settings.llm_max_retries + 1):
        try:
            content, usage = await _post(provider, messages)
        except httpx.HTTPError as exc:
            raise _ProviderError(f"{provider.name}: {exc}") from exc

        try:
            analysis = Analysis.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            if attempt == settings.llm_max_retries:
                raise _ProviderError(
                    f"{provider.name}: invalid analysis response: {exc}"
                ) from exc
            messages = prompt_module.repair_messages(messages, content)
            continue

        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cost = estimate_cost(prompt_tokens, completion_tokens)
        log.info(
            "llm call: %s/%s in=%s out=%s cost=$%.6f"
            % (
                provider.name,
                provider.model,
                prompt_tokens,
                completion_tokens,
                cost,
            ),
            extra={
                "stage": "analysis",
                "provider": provider.name,
                "model": provider.model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost,
            },
        )
        return LLMResult(
            analysis=analysis,
            provider=provider.name,
            model=provider.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )

    raise _ProviderError(f"{provider.name}: exhausted retries")


async def analyze(
    cleaned_text: str,
    channel_name: str,
    timestamp: str,
    coins_hint: list[str] | None = None,
    jev_hint: dict | None = None,
) -> LLMResult:
    original_messages = prompt_module.build_messages(
        cleaned_text, channel_name, timestamp, coins_hint, jev_hint
    )
    providers = _providers()
    last_error: _ProviderError | None = None

    for index, provider in enumerate(providers):
        messages = list(original_messages)
        try:
            return await _call_provider(provider, messages)
        except _ProviderError as exc:
            last_error = exc
            if index + 1 < len(providers):
                log.warning(
                    "llm provider %s failed (%s); falling back to %s"
                    % (provider.name, exc, providers[index + 1].model),
                    extra={"stage": "analysis", "provider": provider.name},
                )

    raise AnalysisError(f"invalid analysis response: {last_error}")
