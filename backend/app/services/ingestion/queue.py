import json

import redis.asyncio as redis

from app.core.config import settings

RAW_STREAM = "raw_news"
CLUSTERED_STREAM = "clustered_news"
ANALYZED_STREAM = "analyzed_news"
DLQ_STREAM = "dlq"
FAST_ALERTS_STREAM = "fast_alerts"
CONSUMER_GROUP = "pipeline"

_client = redis.from_url(settings.redis_url, decode_responses=True)


def get_client() -> redis.Redis:
    return _client


async def ensure_groups() -> None:
    for stream in (RAW_STREAM, CLUSTERED_STREAM, ANALYZED_STREAM):
        try:
            await _client.xgroup_create(
                stream, CONSUMER_GROUP, id="0", mkstream=True
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise


async def _publish(stream: str, item: dict) -> str:
    return await _client.xadd(stream, {"payload": json.dumps(item, default=str)})


async def publish_raw(item: dict) -> str:
    return await _publish(RAW_STREAM, item)


async def publish_clustered(item: dict) -> str:
    return await _publish(CLUSTERED_STREAM, item)


async def publish_analyzed(item: dict) -> str:
    return await _publish(ANALYZED_STREAM, item)


async def publish_fast_alert(item: dict) -> str:
    return await _publish(FAST_ALERTS_STREAM, item)


async def publish_dlq(item: dict, error: str) -> str:
    return await _client.xadd(
        DLQ_STREAM,
        {"payload": json.dumps(item, default=str), "error": error},
    )


async def close() -> None:
    await _client.aclose()
