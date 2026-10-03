from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from app.services.ingestion.dedup import content_hash
from app.services.ingestion.normalize import normalize
from app.services.ingestion.queue import publish_raw


def channel_ref(channel) -> str | int:
    return channel.username or channel.telegram_id


def media_type_of(message) -> str | None:
    if isinstance(message.media, MessageMediaPhoto):
        return "photo"
    if isinstance(message.media, MessageMediaDocument):
        return "document"
    return None


def build_item(channel, message) -> dict:
    original = message.message or ""
    text, links = normalize(original)
    return {
        "channel_telegram_id": channel.telegram_id,
        "channel_title": channel.title,
        "is_private": channel.is_private,
        "message_id": message.id,
        "posted_at": message.date.isoformat(),
        "original_text": original,
        "normalized_text": text,
        "links": links,
        "media_type": media_type_of(message),
        "views": getattr(message, "views", None),
        "forwards": getattr(message, "forwards", None),
        "content_hash": content_hash(text),
    }


async def backfill_channel(
    client, channel, min_id: int = 0, limit: int = 2000, publish: bool = True
) -> list[dict]:
    items: list[dict] = []
    async for message in client.iter_messages(
        channel_ref(channel), min_id=min_id, limit=limit
    ):
        if not message.message and not message.media:
            continue
        item = build_item(channel, message)
        items.append(item)
        if publish:
            await publish_raw(item)
    return items
