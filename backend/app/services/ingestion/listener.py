import asyncio

from telethon import TelegramClient, events

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.services.ingestion.backfill import backfill_channel, build_item
from app.services.ingestion.queue import close, ensure_groups, publish_raw
from app.services.ingestion.state import (
    load_tracked_channels,
    update_last_message_id,
)

log = get_logger("ingestion.listener")


async def main() -> None:
    configure_logging(settings.log_level)
    channels = await load_tracked_channels()
    by_telegram_id = {channel.telegram_id: channel for channel in channels}

    client = TelegramClient(
        settings.tg_session_name, settings.tg_api_id, settings.tg_api_hash
    )
    await client.start()
    await ensure_groups()

    for channel in channels:
        if not channel.last_message_id:
            continue
        recovered = await backfill_channel(
            client, channel, min_id=channel.last_message_id, publish=True
        )
        if recovered:
            newest = max(item["message_id"] for item in recovered)
            await update_last_message_id(channel.telegram_id, newest)

    @client.on(events.NewMessage())
    async def handler(event) -> None:
        channel = by_telegram_id.get(event.chat_id)
        if channel is None:
            return
        if not event.message.message and not event.message.media:
            return
        item = build_item(channel, event.message)
        await publish_raw(item)
        await update_last_message_id(channel.telegram_id, event.message.id)

    log.info("listener started", extra={"stage": "ingestion"})
    await client.run_until_disconnected()
    await close()


if __name__ == "__main__":
    asyncio.run(main())
