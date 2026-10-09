# 17 - JEV (TypeSafe) for News Usefulness and Categorization

This document describes the JEV integration from TypeSafe. JEV adds a fast,
structured decision layer to the analysis stage that:

1. Checks whether an ingested news item is actually useful and actionable for
   crypto trading (so spam, ads, and price recaps never reach the LLM).
2. Pre-categorizes each item into an event type, sentiment, and urgency, and
   scores its likely market impact.

JEV advises; deterministic code still decides. JEV cannot place orders, set
position size, or change leverage. Final trading decisions remain in the
signaler and risk engine.

## Pipeline position

```
raw_news --> cluster_worker --> clustered_news --> analysis.worker
                                                     |
                       keyword relevance gate (filter.relevance_score)
                                                     |
                                       JEV system_one (usefulness + categories)
                                                     |
                             low usefulness --> discard (skip LLM)
                                                     |
                                       LLM analyzer (JEV categories as a hint)
                                                     |
                                             analyzed_news --> signals
```

JEV runs after the cheap keyword gate and before the LLM. Its usefulness Noul
acts as a second, semantic gate: items below `JEV_USEFULNESS_MIN` are discarded
with reason `low_usefulness:<prob>` and never consume LLM tokens.

## Questions sent to JEV

Every assessment is a single `system_one` call with these typed questions:

| key          | type   | purpose                                              |
|--------------|--------|------------------------------------------------------|
| `useful`     | Noul   | Is this useful and actionable for a trading decision? |
| `event_type` | Choice | One of the 10 platform event types                   |
| `sentiment`  | Choice | `bullish`, `bearish`, `neutral`                      |
| `urgency`    | Choice | `low`, `medium`, `high`, `critical`                  |
| `impact`     | Score  | 5 levels, from no impact to market-wide move         |

The Choice/Score criteria are defined in `app/services/analysis/jev.py` and
mirror `app/schemas/analysis.py`, so JEV output lines up with the existing
`EventType`, `Sentiment`, and `Urgency` enums.

## How the result is used

- The usefulness probability gates the item (see above).
- The categories are passed to the LLM prompt as a trusted hint
  (`build_messages(..., jev_hint=...)`). The LLM is told this is a suggestion
  only and must verify it against the data.
- The full assessment (probabilities, confidences, model name) is stored on
  `news.jev_assessment` (JSONB) and included in the published `analyzed_news`
  payload and the REST news serializer.

## Configuration

| setting                  | default                    | purpose                        |
|--------------------------|----------------------------|--------------------------------|
| `TYPESAFE_API_KEY`       | empty                      | Enables JEV when set           |
| `TYPESAFE_BASE_URL`      | `https://api.typesafe.ai`  | API root (no `/v1`)            |
| `TYPESAFE_MODEL`         | `jev-latest`               | Model alias                    |
| `TYPESAFE_TIMEOUT_SECONDS` | `20`                     | Per-request timeout            |
| `JEV_GATE_ENABLED`       | `true`                     | Discard low-usefulness items   |
| `JEV_USEFULNESS_MIN`     | `0.5`                      | Usefulness gate threshold      |

The API key is provided by the operator through the project environment; it is
never read from the agent runtime environment. When `TYPESAFE_API_KEY` is
empty, the SDK is not installed, or a request fails, `assess()` returns `None`
and the pipeline falls back to the keyword gate plus the LLM. JEV is therefore
fully optional.

## Data model

Migration `0006_jev` adds `news.jev_assessment` (JSONB, nullable). Example:

```json
{
  "useful": 0.92,
  "event_type": "listing",
  "event_type_confidence": 0.88,
  "sentiment": "bullish",
  "sentiment_confidence": 0.7,
  "urgency": "high",
  "impact_score": 3.1,
  "model": "jev-1.13.0",
  "is_useful": true,
  "probabilities": {
    "event_type": {"listing": 0.88, "other": 0.12},
    "sentiment": {"bullish": 0.7, "neutral": 0.2, "bearish": 0.1},
    "urgency": {"high": 0.6, "medium": 0.4}
  }
}
```

## Dependency

The integration uses the official SDK (`typesafe-sdk>=0.7`), which is imported
lazily. The call is synchronous in the SDK, so the async wrapper runs it in a
thread (`asyncio.to_thread`) to avoid blocking the analyzer event loop.
