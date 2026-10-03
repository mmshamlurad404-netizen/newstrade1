import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.models.ingestion import Channel
from app.models.news import News, NewsSource, RawMessage
from app.schemas.raw import RawItem
from app.services.ingestion.dedup import is_duplicate
from app.services.ingestion.queue import (
    CONSUMER_GROUP,
    RAW_STREAM,
    close,
    ensure_groups,
    get_client,
    publish_clustered,
    publish_dlq,
)

log = get_logger("ingestion.cluster")

CONSUMER = "clusterer-1"
WINDOW_MINUTES = 30
SIMILARITY = 0.9


async def load_or_create_channel(session, item: RawItem) -> Channel:
    result = await session.execute(
        select(Channel).where(Channel.telegram_id == item.channel_telegram_id)
    )
    channel = result.scalar_one_or_none()
    if channel is not None:
        return channel
    channel = Channel(
        telegram_id=item.channel_telegram_id,
        title=item.channel_title or str(item.channel_telegram_id),
        is_private=item.is_private,
    )
    session.add(channel)
    await session.flush()
    return channel


async def store_raw_message(session, channel, item: RawItem) -> RawMessage | None:
    statement = (
        pg_insert(RawMessage)
        .values(
            channel_id=channel.id,
            message_id=item.message_id,
            posted_at=item.posted_at,
            original_text=item.original_text,
            normalized_text=item.normalized_text,
            links=item.links,
            media_type=item.media_type,
            views=item.views,
            forwards=item.forwards,
            content_hash=item.content_hash,
        )
        .on_conflict_do_nothing(constraint="uq_raw_channel_msg")
        .returning(RawMessage.id)
    )
    result = await session.execute(statement)
    row = result.first()
    if row is None:
        return None
    stored = await session.execute(
        select(RawMessage).where(RawMessage.id == row.id)
    )
    return stored.scalar_one()


async def find_cluster(session, item: RawItem) -> News | None:
    exact = await session.execute(
        select(News).where(News.canonical_hash == item.content_hash)
    )
    found = exact.scalar_one_or_none()
    if found is not None:
        return found

    since = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    recent = await session.execute(
        select(News).where(News.first_seen_at >= since)
    )
    for candidate in recent.scalars().all():
        if candidate.body_text and is_duplicate(
            candidate.body_text, item.normalized_text, SIMILARITY
        ):
            return candidate
    return None


async def attach_source(session, news, raw, channel, item: RawItem) -> None:
    await session.execute(
        pg_insert(NewsSource)
        .values(
            news_id=news.id,
            raw_message_id=raw.id,
            channel_id=channel.id,
            is_origin=False,
            similarity=1.0,
        )
        .on_conflict_do_nothing()
    )

    if item.posted_at < news.first_seen_at:
        news.first_seen_at = item.posted_at
        news.origin_channel_id = channel.id
        await session.execute(
            update(NewsSource)
            .where(
                NewsSource.news_id == news.id,
                NewsSource.raw_message_id == raw.id,
            )
            .values(is_origin=True)
        )
    elif item.posted_at == news.first_seen_at and news.origin_channel_id is None:
        news.origin_channel_id = channel.id
        await session.execute(
            update(NewsSource)
            .where(
                NewsSource.news_id == news.id,
                NewsSource.raw_message_id == raw.id,
            )
            .values(is_origin=True)
        )

    channel_count = await session.scalar(
        select(func.count(func.distinct(NewsSource.channel_id))).where(
            NewsSource.news_id == news.id
        )
    )
    news.source_count = max(1, channel_count or 1)
    if item.posted_at > news.last_seen_at:
        news.last_seen_at = item.posted_at


async def process_item(payload: dict) -> None:
    item = RawItem.model_validate(payload)
    async with async_session_factory() as session:
        channel = await load_or_create_channel(session, item)
        raw = await store_raw_message(session, channel, item)
        if raw is None:
            await session.commit()
            return

        news = await find_cluster(session, item)
        if news is None:
            news = News(
                canonical_hash=item.content_hash,
                headline=item.normalized_text[:140] or "(media)",
                body_text=item.normalized_text,
                coins=[],
                first_seen_at=item.posted_at,
                last_seen_at=item.posted_at,
                origin_channel_id=channel.id,
                source_count=1,
            )
            session.add(news)
            await session.flush()
        else:
            if item.posted_at > news.last_seen_at:
                news.last_seen_at = item.posted_at

        await attach_source(session, news, raw, channel, item)
        await session.commit()

        await publish_clustered(
            {
                "news_id": news.id,
                "canonical_hash": news.canonical_hash,
                "text": news.body_text,
                "channel_id": channel.id,
                "channel_title": channel.title,
                "is_private": channel.is_private,
                "posted_at": item.posted_at.isoformat(),
                "source_count": news.source_count,
            }
        )


async def run() -> None:
    configure_logging(settings.log_level)
    await ensure_groups()
    client = get_client()
    log.info("cluster worker started", extra={"stage": "cluster"})

    while True:
        try:
            response = await client.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER,
                {RAW_STREAM: ">"},
                count=10,
                block=5000,
            )
        except Exception as exc:
            log.error("read failed: %s" % exc, extra={"stage": "cluster"})
            await asyncio.sleep(1)
            continue

        if not response:
            continue

        for _stream, entries in response:
            for entry_id, fields in entries:
                payload = json.loads(fields["payload"])
                try:
                    await process_item(payload)
                except Exception as exc:
                    log.error(
                        "processing failed: %s" % exc, extra={"stage": "cluster"}
                    )
                    await publish_dlq(payload, str(exc))
                finally:
                    await client.xack(RAW_STREAM, CONSUMER_GROUP, entry_id)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
