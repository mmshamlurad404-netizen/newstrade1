# 02 - Phase 1: Telegram News Extraction

This phase answers the core question: how to feed news into the app. Get it
right first; everything downstream depends on a clean, reliable stream.

## Phase 0: Account and credential setup (3-5 days)

Checklist:

- [ ] Get `api_id` and `api_hash` from https://my.telegram.org under
      "API Development Tools".
- [ ] Create a **dedicated** Telegram account for ingestion (not your personal
      account).
- [ ] Log in once interactively to create the session file.
- [ ] Enable two-step verification (2FA).
- [ ] Join every channel you want to follow with that account.
- [ ] Record the channel list in the `channels` table (see `06`).

Required environment variables:

```text
TG_API_ID=123456
TG_API_HASH=your_api_hash
TG_SESSION_NAME=newstrade_ingestor
```

Never commit the session file, `api_hash`, or a populated `.env`.

## Phase 1: Ingestion engine

### 1.1 Library and mechanism

Use **Telethon** (Python, MTProto user client).

**Do not use the Bot API.** A bot only sees channels where it is added, and it
cannot read arbitrary private channels. Reading private channels requires a user
session, which is what the MTProto user API provides.

Access rules:

- Public channels: readable by username or invite link.
- Private channels: the account must already be a member (invited). The API
  cannot grant access you do not have.
- Never attempt to access channels the account is not a member of.

### 1.2 Install

```bash
pip install --break-system-packages telethon redis asyncpg python-dotenv
```

### 1.3 First login (interactive, run once)

File: `backend/app/services/ingestion/login.py`

```python
import asyncio
import os
from telethon import TelegramClient

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION_NAME", "newstrade_ingestor")


async def main() -> None:
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print("Logged in as:", me.username or me.id)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

This writes `newstrade_ingestor.session`. Encrypt it at rest and back it up
securely. Re-logging frequently from new IPs can trigger Telegram flags.

### 1.4 Real-time listener with gap handling

The subtle bug: `events.NewMessage` only delivers messages while connected. If
the client is briefly offline, those messages are lost. On every (re)connect you
must backfill using `min_id` = the last stored `message_id` for each channel.

File: `backend/app/services/ingestion/listener.py`

```python
import asyncio
import os
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION_NAME", "newstrade_ingestor")


def build_raw_item(msg, chat_id) -> dict:
    return {
        "channel_id": chat_id,
        "message_id": msg.id,
        "date": msg.date.replace(tzinfo=timezone.utc).isoformat(),
        "text": msg.message or "",
        "has_media": msg.media is not None,
        "media_type": (
            "photo" if isinstance(msg.media, MessageMediaPhoto)
            else "document" if isinstance(msg.media, MessageMediaDocument)
            else None
        ),
        "views": getattr(msg, "views", None),
        "forwards": getattr(msg, "forwards", None),
    }


async def main() -> None:
    from app.services.ingestion.queue import publish_raw
    from app.services.ingestion.state import load_last_ids, save_last_id
    from app.services.ingestion.backfill import backfill_channel

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    # Close the disconnect gap before listening.
    for channel_id, last_id in (await load_last_ids()).items():
        await backfill_channel(client, channel_id, min_id=last_id, publish=True)

    @client.on(events.NewMessage())
    async def handler(event):
        item = build_raw_item(event.message, event.chat_id)
        if not item["text"] and not item["has_media"]:
            return
        await publish_raw(item)
        await save_last_id(event.chat_id, event.message.id)

    print("Listening. Ctrl+C to stop.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
```

### 1.5 History backfill (first run and gap recovery)

File: `backend/app/services/ingestion/backfill.py`

```python
import os
from telethon import TelegramClient

HISTORY_LIMIT = int(os.environ.get("TG_HISTORY_LIMIT", "2000"))


async def backfill_channel(client, channel_id, min_id=0, limit=HISTORY_LIMIT,
                           publish=False):
    from app.services.ingestion.queue import publish_raw

    items = []
    async for msg in client.iter_messages(channel_id, min_id=min_id, limit=limit):
        if not msg.message and not msg.media:
            continue
        item = {
            "channel_id": channel_id,
            "message_id": msg.id,
            "date": msg.date.isoformat(),
            "text": msg.message or "",
            "has_media": msg.media is not None,
        }
        items.append(item)
        if publish:
            await publish_raw(item)
    return items
```

Persist `last_message_id` per channel so backfill resumes without reprocessing.

### 1.6 Idempotency (at-least-once queue, exactly-once effect)

Redis Streams give at-least-once delivery, so a message can be processed twice.
Make every write idempotent:

- Raw message: unique on `(channel_id, message_id)`; upsert.
- News cluster: unique on `canonical_hash`; upsert and update `last_seen_at`.
- Signal: unique on a deterministic `signal_id` derived from the news id and
  direction.

Use `INSERT ... ON CONFLICT DO NOTHING/UPDATE` in Postgres.

### 1.7 Media handling (OCR and vision)

1. Gate media by the relevance score before downloading (control cost).
2. Download with `client.download_media`.
3. Tesseract OCR for text-heavy images.
4. Vision LLM for charts and complex images to extract coins, numbers, or
   direction.
5. Merge extracted text into the message before analysis.

```python
import pytesseract
from PIL import Image


def ocr_image(path: str) -> str:
    return pytesseract.image_to_string(Image.open(path))
```

### 1.8 Normalization

File: `backend/app/services/ingestion/normalize.py`

1. Strip emojis, zero-width and control characters.
2. Extract URLs to metadata, remove them from the text.
3. Detect language (`fastText`/`langdetect`); translate to English when needed.
4. Keep both original and normalized text for audit and for the app.

```python
import re
import unicodedata

URL_RE = re.compile(r"https?://\S+")
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]+"
)


def normalize(text: str) -> tuple[str, list[str]]:
    links = URL_RE.findall(text)
    text = URL_RE.sub(" ", text)
    text = EMOJI_RE.sub(" ", text)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if ch == "\n" or ch >= " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text, links
```

### 1.9 Deduplication and corroboration clustering

Duplicate detection and corroboration are the same mechanism: cluster near-
identical messages, then count independent origin channels.

1. **Exact**: SHA-256 of the normalized lowercase text.
2. **Near-duplicate**: SimHash/MinHash with a similarity threshold (drop
   candidate duplicates above ~0.9 Jaccard).
3. **Clustering window**: default 30 minutes. Link the message to an existing
   `news` cluster instead of creating a new one.
4. **Origin attribution**: the earliest post in the cluster is the originator.
   Forwards of the same origin do not increase independent corroboration.
5. **Structured events**: for events like listings, also key on
   `(event_type, coin, time_bucket)` so differently-worded reports cluster.

```python
import hashlib


def content_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.lower().encode("utf-8")).hexdigest()
```

### 1.10 Telegram account safety

Automation can get an account limited or banned. Mitigations:

- Use a dedicated account; never risk the personal account.
- Throttle joins; do not join hundreds of channels at once. Spread over days.
- Reuse the session file; do not log in repeatedly from new IPs.
- Catch `FloodWaitError`, sleep the requested seconds plus a margin, then retry.
- Never send messages, react, or otherwise behave like a spammer.
- If you need many channels, consider a second dedicated account with its own
  session, but do not use accounts for bulk access you are not entitled to.
- Monitor for `PeerFloodError` and `UserDeactivatedBanError`; alert and stop.

```python
from telethon.errors import FloodWaitError

try:
    await client.get_messages(channel, limit=100)
except FloodWaitError as exc:
    await asyncio.sleep(exc.seconds + 1)
```

### 1.11 Poison messages and dead letters

A malformed message or media file must not stall a worker.

- Validate each record against a schema before publishing.
- On repeated processing failure, move to a dead-letter stream `raw_news_dlq`
  with the error and the original payload.
- Alert when the DLQ grows.

### 1.12 Metrics and health

Emit per channel and globally:

- messages ingested per minute
- duplicates clustered
- media processed
- flood waits and errors
- last successful message timestamp (stale detector)
- reconnect count and messages recovered by gap backfill

Alert if a channel that normally posts goes silent, or if the client cannot
reconnect.

## Deliverables for Phase 1

- [ ] Running ingestor writing normalized messages to Redis Streams.
- [ ] History backfill and reconnect gap recovery using `min_id`.
- [ ] Media OCR and vision pipeline.
- [ ] Dedup plus corroboration clustering with origin attribution.
- [ ] Idempotent upserts and a dead-letter stream.
- [ ] Health metrics and stale-channel alerts.
- [ ] Documented encrypted session backup and restore procedure.

## Phase 1 acceptance tests

1. Post in a private test channel; it reaches the database within 5 seconds.
2. Disconnect for 60 seconds while messages are posted; on reconnect all missed
   messages are recovered exactly once.
3. Repost the same text from another channel; no new news cluster; the second
   channel is linked but does not increase independent corroboration if it is a
   forward of the same origin.
4. Send an image-only post; OCR text is extracted and stored.
5. Publish a deliberately malformed record; it lands in the DLQ and the worker
   keeps running.
