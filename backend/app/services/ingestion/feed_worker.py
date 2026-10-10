import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.services.ingestion import feeds
from app.services.ingestion.queue import close, ensure_groups, publish_raw
from app.services.ingestion.state import load_feed_channels, update_feed_polled

log = get_logger("ingestion.feeds")

TICK_SECONDS = 30
MAX_SEEN_PER_CHANNEL = 5000

_seen: dict[int, set[int]] = {}


def is_due(channel, now: datetime) -> bool:
    if channel.last_polled_at is None:
        return True
    elapsed = (now - channel.last_polled_at).total_seconds()
    return elapsed >= (channel.poll_interval_seconds or TICK_SECONDS)


async def poll_channel(client: httpx.AsyncClient, channel, now: datetime) -> int:
    try:
        content = await feeds.fetch_feed(channel.feed_url, client)
    except Exception as exc:
        log.error(
            "feed fetch failed %s: %s" % (channel.feed_url, exc),
            extra={"stage": "feeds"},
        )
        return 0

    entries = feeds.parse_feed(content)
    seen = _seen.setdefault(channel.id, set())
    cutoff = now - timedelta(hours=settings.feed_max_age_hours)
    newest: datetime | None = None
    published = 0

    for entry in entries[: settings.feed_max_entries]:
        message_id = feeds.stable_message_id(entry.guid)
        if message_id in seen:
            continue
        seen.add(message_id)
        if entry.published is not None and entry.published < cutoff:
            continue
        item = feeds.build_raw_item(channel, entry)
        if item is None:
            continue
        await publish_raw(item)
        published += 1
        if entry.published is not None and (
            newest is None or entry.published > newest
        ):
            newest = entry.published

    await update_feed_polled(channel.id, newest)
    if len(seen) > MAX_SEEN_PER_CHANNEL:
        seen.clear()
        seen.update(feeds.stable_message_id(e.guid) for e in entries)
    if published:
        log.info(
            "feed %s published %s new items" % (channel.title, published),
            extra={"stage": "feeds"},
        )
    return published


async def run() -> None:
    configure_logging(settings.log_level)
    await ensure_groups()
    log.info("feed worker started", extra={"stage": "feeds"})

    async with httpx.AsyncClient(
        timeout=settings.feed_request_timeout, follow_redirects=True
    ) as client:
        semaphore = asyncio.Semaphore(settings.feed_poll_concurrency)

        async def guarded(channel, now):
            async with semaphore:
                await poll_channel(client, channel, now)

        while True:
            try:
                channels = await load_feed_channels()
                now = datetime.now(timezone.utc)
                due = [
                    channel
                    for channel in channels
                    if channel.feed_url and is_due(channel, now)
                ]
                if due:
                    await asyncio.gather(
                        *(guarded(channel, now) for channel in due),
                        return_exceptions=True,
                    )
            except Exception as exc:
                log.error(
                    "feed cycle failed: %s" % exc, extra={"stage": "feeds"}
                )
            await asyncio.sleep(TICK_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(close())
