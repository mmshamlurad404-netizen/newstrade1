# 02 - Phase 1: Telegram News Extraction

This phase answers the core question: how to feed news into the app. Get this
right first; everything downstream depends on a clean, reliable message stream.

## Phase 0: Account and credential setup (3-5 days)

Checklist:

- [ ] Get `api_id` and `api_hash` from https://my.telegram.org under
      "API Development Tools".
- [ ] Create a dedicated Telegram account for ingestion (do not use your
      personal main account).
- [ ] Log in once interactively to produce a session file.
- [ ] Enable two-step verification (2FA) on the dedicated account.
- [ ] Join every channel you want to follow with that account.
- [ ] Record the channel list in a config table (see `06-data-model-and-api.md`).

Store secrets in environment variables or a secrets manager. Never commit the
session file, `api_hash`, or any `.env` with real keys.

Required environment variables:

```text
TG_API_ID=123456
TG_API_HASH=your_api_hash
TG_SESSION_NAME=newstrade_ingestor
```

## Phase 1: Ingestion engine

### 1.1 Library choice

Use **Telethon** (Python, MTProto user client).

**Do not use the Bot API.** A bot can only read channels where it is added, and
it cannot read arbitrary private channels. Private channel access requires a user
session, which is exactly what the MTProto user API provides.

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

Run it and complete the phone/code prompt once. This writes
`newstrade_ingestor.session`. Back it up securely and reuse it; do not log in
again from a different IP too often or Telegram may flag the account.

### 1.4 Real-time listener

File: `backend/app/services/ingestion/listener.py`

```python
import asyncio
import json
import os
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION_NAME", "newstrade_ingestor")


def build_raw_item(event) -> dict:
    msg = event.message
    return {
        "channel_id": event.chat_id,
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
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    from app.services.ingestion.queue import publish_raw

    @client.on(events.NewMessage())
    async def handler(event):
        item = build_raw_item(event)
        if not item["text"] and not item["has_media"]:
            return
        await publish_raw(item)

    print("Listening for new messages. Ctrl+C to stop.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
```

Key point: use `events.NewMessage` so messages arrive in seconds, instead of
polling `get_messages` on a timer.

### 1.5 History backfill

On first run, scrape history for each tracked channel so you can display
timelines and backtest.

File: `backend/app/services/ingestion/backfill.py`

```python
import os
from telethon import TelegramClient

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION_NAME", "newstrade_ingestor")
HISTORY_LIMIT = int(os.environ.get("TG_HISTORY_LIMIT", "2000"))


async def backfill(channel: str, limit: int = HISTORY_LIMIT) -> list[dict]:
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()
    items = []
    async for msg in client.iter_messages(channel, limit=limit):
        if not msg.message and not msg.media:
            continue
        items.append({
            "channel_id": msg.chat_id,
            "message_id": msg.id,
            "date": msg.date.isoformat(),
            "text": msg.message or "",
            "has_media": msg.media is not None,
        })
    await client.disconnect()
    return items
```

Track the last seen `message_id` per channel so backfill resumes without
re-processing old messages.

### 1.6 Media handling (OCR and vision)

Many channels post screenshots of charts or announcements. Handle them:

1. Download the media with `client.download_media`.
2. Run Tesseract OCR for text-heavy images.
3. For charts and complex images, call a vision-capable LLM to describe the
   image and extract coins, numbers, and direction.
4. Merge the extracted text into the message text before analysis.

```python
import pytesseract
from PIL import Image


def ocr_image(path: str) -> str:
    return pytesseract.image_to_string(Image.open(path))
```

Only fetch media for messages that pass a cheap relevance gate, to control
bandwidth and cost.

### 1.7 Normalization

File: `backend/app/services/ingestion/normalize.py`

Steps:

1. Strip emojis, zero-width characters, and excessive whitespace.
2. Extract and remove URLs; keep a list of links as metadata.
3. Detect language with `fastText` or `langdetect`.
4. Translate to English when needed using the LLM or a translation API.
5. Return a normalized record with both original and normalized text.

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
    text = re.sub(r"\s+", " ", text).strip()
    return text, links
```

### 1.8 Deduplication

Crypto channels forward the same news constantly. Three layers:

1. **Exact hash**: SHA-256 of the normalized lowercase text.
2. **Near-duplicate**: MinHash or SimHash with a similarity threshold
   (for example, drop if Jaccard similarity is above 0.9).
3. **Windowed**: ignore duplicates within a configurable window, default 30
   minutes, but keep the list of channels that reported it (for corroboration).

```python
import hashlib


def content_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.lower().encode("utf-8")).hexdigest()
```

When a duplicate arrives from a different channel, do not discard it silently:
record the channel as a corroborating source on the existing news item.

### 1.9 Rate limiting and session safety

- Telethon raises `FloodWaitError`. Catch it, sleep for the requested number of
  seconds, then retry. Never ignore it.
- Run exactly one client session per account.
- Do not join hundreds of channels instantly; spread joins over time.
- Use a proxy only if allowed in your environment and in line with the rules.

```python
from telethon.errors import FloodWaitError

try:
    await client.get_messages(channel, limit=100)
except FloodWaitError as exc:
    await asyncio.sleep(exc.seconds + 1)
```

### 1.10 Metrics and health

Emit to logs or Prometheus:

- messages ingested per minute, per channel
- duplicates dropped
- media processed
- flood waits encountered
- last successful message timestamp per channel (stale detector)

Send an alert if a channel has not produced a message when it normally would, or
if the client disconnects and cannot reconnect.

## Deliverables for Phase 1

- [ ] A running ingestor that writes normalized messages to Redis Streams.
- [ ] History backfill for all tracked channels.
- [ ] Media OCR and vision pipeline.
- [ ] Deduplication with corroboration tracking.
- [ ] Health metrics and stale-channel alerts.
- [ ] Documented session backup and restoration procedure.

## Phase 1 acceptance tests

1. Post a test message in a private test channel; it appears in Redis within 5
   seconds.
2. Re-post the same text; only one news item exists and the second channel is
   recorded as a corroborator.
3. Send an image-only post; OCR text is extracted and stored.
4. Restart the ingestor; it reconnects and resumes without re-processing.
