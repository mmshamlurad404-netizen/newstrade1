# 16 - Crypto News Website Feeds (Additional Ingestion Source)

In addition to Telegram channels, the platform ingests crypto news website
feeds (RSS 2.0, Atom, and JSON Feed). Feed entries are normalized into the same
`RawItem` shape as Telegram messages and published onto the `raw_news` stream,
so clustering, analysis, signals, and trading all run unchanged.

## Pipeline position

```
                 +-------------------+        +-----------------------------+
Telegram  ---->  |                   |        |  cluster_worker             |
listener         |    raw_news       |  --->  |  (channel/raw_messages/news) | ---> clustered_news
feed_worker ---> |    (Redis stream) |        |                             |      (analysis queue)
                 +-------------------+        +-----------------------------+
```

Both the Telegram listener and the feed worker write `raw_news`. No analyzer,
signaler, or executor changes are required.

## How feeds are modeled

Feeds are stored in the existing `channels` table with `kind = 'feed'`:

| column                  | purpose                                             |
|-------------------------|-----------------------------------------------------|
| `kind`                  | `telegram` (default) or `feed`                      |
| `feed_url`              | RSS / Atom / JSON feed URL                          |
| `poll_interval_seconds` | per-feed polling cadence (default 300s)             |
| `last_polled_at`        | last successful poll                                |
| `telegram_id`           | deterministic negative id derived from the URL hash |

The synthetic negative `telegram_id` keeps the unique constraint intact and
lets the Telegram listener ignore feeds: `load_tracked_channels()` filters on
`kind = 'telegram'`.

## Deduplication

- Each entry maps to a stable `message_id = sha1(guid)[:15]`, so re-polling a
  feed produces the same id and the `raw_messages (channel_id, message_id)`
  unique constraint drops the duplicate.
- `content_hash` (normalized text) also clusters a feed story with the same
  story from Telegram/another site, increasing corroboration.

## Configuration (`Settings`)

- `feed_request_timeout` (default 20s)
- `feed_user_agent` (browser User-Agent; reduces WAF 403s)
- `feed_max_entries` (max entries handled per poll, default 40)
- `feed_max_age_hours` (skip entries older than this, default 168)
- `feed_poll_concurrency` (feeds fetched in parallel per cycle, default 8)

Redirects are followed (`follow_redirects=True`), needed for e.g. CoinDesk.

## Running

```bash
# register/refresh the default crypto feeds (idempotent)
python scripts/seed_feeds.py

# also deactivate feed channels no longer in the catalog
python scripts/seed_feeds.py --prune

# start the poller (compose service: feeds)
python -m app.services.ingestion.feed_worker
```

## Catalog

`app/services/ingestion/feed_catalog.py` ships a curated **top-100** catalog
(`DEFAULT_FEEDS`), grouped into six buckets: crypto media, news aggregators,
macro/regulation, on-chain/analytics research, exchange/company/protocol
blogs, and mainstream finance/tech. Every URL was verified to return a
parseable feed with a recent (< 7 days) item; the current run publishes
content from 99/100 sources (Reddit intermittently 429s). The catalog replaced
the earlier 4-feed default and the initial auto-discovered list, which
contained many stale mirrors.

## API

- `GET /api/feeds` - list feed sources
- `POST /api/feeds` - register `{title, url, credibility?, poll_interval_seconds?}`
- `POST /api/feeds/{id}/active` - `{active: bool}` pause/resume
- `GET /api/channels` - all sources (includes `kind` and `feed_url`)

The dashboard **Channels** tab lists all sources and lets you add/pause feeds.
