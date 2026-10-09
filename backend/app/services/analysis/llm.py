import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.analysis import Analysis
from app.services.analysis import prompt as prompt_module


class AnalysisError(RuntimeError):
    pass


async def _post(messages: list[dict]) -> str:
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]


async def analyze(
    cleaned_text: str,
    channel_name: str,
    timestamp: str,
    coins_hint: list[str] | None = None,
    jev_hint: dict | None = None,
) -> Analysis:
    messages = prompt_module.build_messages(
        cleaned_text, channel_name, timestamp, coins_hint, jev_hint
    )
    last_error: Exception | None = None

    for attempt in range(settings.llm_max_retries + 1):
        content = await _post(messages)
        try:
            return Analysis.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            last_error = exc
            if attempt == settings.llm_max_retries:
                break
            messages = prompt_module.repair_messages(messages, content)

    raise AnalysisError(f"invalid analysis response: {last_error}")
