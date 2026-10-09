import asyncio
import json

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.models.news import News
from app.services.analysis import filter as relevance
from app.services.analysis import jev, market, validator
from app.services.analysis.enrich import build_enrichment
from app.services.analysis.llm import AnalysisError, analyze
from app.services.analysis.prompt import PROMPT_VERSION
from app.services.ingestion.queue import (
    CLUSTERED_STREAM,
    CONSUMER_GROUP,
    close,
    ensure_groups,
    get_client,
    publish_analyzed,
    publish_dlq,
    publish_fast_alert,
)

log = get_logger("analysis.worker")

CONSUMER = "analyzer-1"


async def analyze_news(payload: dict) -> None:
    news_id = payload["news_id"]
    text = payload.get("text") or ""
    posted_at = payload.get("posted_at")

    async with async_session_factory() as session:
        news = await session.get(News, news_id)
        if news is None:
            return
        if news.analysis_status == "analyzed":
            return

        if settings.fast_path_enabled:
            fast = relevance.detect_fast_alert(text)
            if fast is not None:
                await publish_fast_alert(
                    {**fast, "news_id": news_id, "posted_at": posted_at}
                )

        score = relevance.relevance_score(text)
        if score < settings.analysis_relevance_min:
            news.analysis_status = "discarded"
            news.discarded_reason = f"low_relevance:{score:.2f}"
            await session.commit()
            return

        jev_client = jev.get_jev_client()
        assessment = (
            await jev_client.assess(text) if jev_client.available else None
        )
        jev_hint = assessment.as_dict() if assessment is not None else None
        if assessment is not None and settings.jev_gate_enabled:
            if not assessment.is_useful:
                news.jev_assessment = jev_hint
                news.analysis_status = "discarded"
                news.discarded_reason = f"low_usefulness:{assessment.useful:.2f}"
                await session.commit()
                return

        injections = validator.detect_injection(text)
        try:
            result = await analyze(
                text,
                payload.get("channel_title") or "",
                posted_at or "",
                [],
                jev_hint,
            )
        except AnalysisError as exc:
            news.jev_assessment = jev_hint
            news.analysis_status = "failed"
            news.discarded_reason = f"llm:{exc}"
            await session.commit()
            await publish_dlq(payload, str(exc))
            return

        anomalous = validator.is_anomalous(result, 0.5, injections)
        result = validator.apply_caps(result, anomalous)

        price = None
        if result.coins:
            try:
                price = await market.fetch_price(result.coins[0])
            except Exception:
                price = None

        enrichment = build_enrichment(result, price, news.source_count)

        news.coins = result.coins
        news.event_type = result.event_type.value
        news.sentiment = result.sentiment.value
        news.sentiment_score = result.sentiment_score
        news.urgency = result.urgency.value
        news.certainty = result.certainty
        news.impact_timeframe = result.impact_timeframe
        news.market_scope = result.market_scope
        news.asset_resolved = bool(result.coins)
        news.prompt_version = PROMPT_VERSION
        news.model_name = settings.llm_model
        news.jev_assessment = jev_hint
        news.analysis_status = "analyzed"
        news.discarded_reason = None
        await session.commit()

        await publish_analyzed(
            {
                "news_id": news_id,
                "coins": result.coins,
                "event_type": result.event_type.value,
                "sentiment": result.sentiment.value,
                "sentiment_score": result.sentiment_score,
                "urgency": result.urgency.value,
                "certainty": result.certainty,
                "is_tradable": result.is_tradable,
                "summary": result.summary,
                "posted_at": posted_at,
                "source_count": news.source_count,
                "injections": injections,
                "anomalous": anomalous,
                "enrichment": enrichment,
                "jev": jev_hint,
            }
        )


async def run() -> None:
    configure_logging(settings.log_level)
    await ensure_groups()
    client = get_client()
    log.info("analysis worker started", extra={"stage": "analysis"})

    while True:
        try:
            response = await client.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER,
                {CLUSTERED_STREAM: ">"},
                count=10,
                block=5000,
            )
        except Exception as exc:
            log.error("read failed: %s" % exc, extra={"stage": "analysis"})
            await asyncio.sleep(1)
            continue

        if not response:
            continue

        for _stream, entries in response:
            for entry_id, fields in entries:
                payload = json.loads(fields["payload"])
                try:
                    await analyze_news(payload)
                except Exception as exc:
                    log.error(
                        "analysis failed: %s" % exc, extra={"stage": "analysis"}
                    )
                    await publish_dlq(payload, str(exc))
                finally:
                    await client.xack(CLUSTERED_STREAM, CONSUMER_GROUP, entry_id)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
