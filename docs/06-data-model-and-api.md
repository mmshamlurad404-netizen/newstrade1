# 06 - Data Model and API Reference

## 1. Storage layout

| Store | Purpose |
| :--- | :--- |
| PostgreSQL | Channels, news, analyses, signals, orders, trades, users, settings |
| TimescaleDB | OHLCV candles for technical levels and backtesting |
| pgvector | Embeddings of news for semantic search and deduplication |
| Redis | Cache, rate-limit counters, and streams for pipelines |

## 2. PostgreSQL schema

### 2.1 channels

```sql
CREATE TABLE channels (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        TEXT,
    title           TEXT NOT NULL,
    is_private      BOOLEAN NOT NULL DEFAULT FALSE,
    credibility     NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_message_id BIGINT,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.2 raw_messages

```sql
CREATE TABLE raw_messages (
    id              BIGSERIAL PRIMARY KEY,
    channel_id      BIGINT NOT NULL REFERENCES channels(id),
    message_id      BIGINT NOT NULL,
    posted_at       TIMESTAMPTZ NOT NULL,
    original_text   TEXT,
    normalized_text TEXT,
    links           JSONB NOT NULL DEFAULT '[]',
    media_type      TEXT,
    media_path      TEXT,
    ocr_text        TEXT,
    views           INTEGER,
    forwards        INTEGER,
    content_hash    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (channel_id, message_id)
);

CREATE INDEX idx_raw_messages_hash ON raw_messages (content_hash);
CREATE INDEX idx_raw_messages_posted ON raw_messages (posted_at DESC);
```

### 2.3 news (grouped, deduplicated events)

```sql
CREATE TABLE news (
    id               BIGSERIAL PRIMARY KEY,
    canonical_hash   TEXT UNIQUE NOT NULL,
    headline         TEXT NOT NULL,
    body_text        TEXT,
    coins            TEXT[] NOT NULL DEFAULT '{}',
    event_type       TEXT,
    sentiment        TEXT,
    sentiment_score  NUMERIC(4,3),
    urgency          TEXT,
    certainty        NUMERIC(4,3),
    impact_timeframe TEXT,
    market_scope     TEXT,
    embedding        vector(1536),
    source_count     INTEGER NOT NULL DEFAULT 1,
    first_seen_at    TIMESTAMPTZ NOT NULL,
    last_seen_at     TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_news_coins ON news USING GIN (coins);
CREATE INDEX idx_news_first_seen ON news (first_seen_at DESC);
CREATE INDEX idx_news_embedding ON news USING ivfflat (embedding vector_cosine_ops);
```

### 2.4 news_sources (corroboration join)

```sql
CREATE TABLE news_sources (
    news_id       BIGINT NOT NULL REFERENCES news(id),
    raw_message_id BIGINT NOT NULL REFERENCES raw_messages(id),
    channel_id    BIGINT NOT NULL REFERENCES channels(id),
    similarity    NUMERIC(4,3) NOT NULL DEFAULT 1.000,
    PRIMARY KEY (news_id, raw_message_id)
);
```

### 2.5 signals

```sql
CREATE TABLE signals (
    id                TEXT PRIMARY KEY,
    news_id           BIGINT REFERENCES news(id),
    asset             TEXT NOT NULL,
    direction         TEXT NOT NULL,
    entry_low         NUMERIC NOT NULL,
    entry_high        NUMERIC NOT NULL,
    stop_loss         NUMERIC NOT NULL,
    take_profits      NUMERIC[] NOT NULL,
    leverage_suggested INTEGER NOT NULL DEFAULT 1,
    timeframe         TEXT NOT NULL,
    confidence        INTEGER NOT NULL,
    rationale         TEXT,
    risk_reward       NUMERIC(6,2),
    status            TEXT NOT NULL DEFAULT 'new',
    expires_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_signals_confidence ON signals (confidence DESC, created_at DESC);
```

### 2.6 orders

```sql
CREATE TABLE orders (
    id               BIGSERIAL PRIMARY KEY,
    signal_id        TEXT REFERENCES signals(id),
    exchange         TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    client_order_id  TEXT UNIQUE NOT NULL,
    exchange_order_id TEXT,
    side             TEXT NOT NULL,
    order_type       TEXT NOT NULL,
    quantity         NUMERIC NOT NULL,
    price            NUMERIC,
    status           TEXT NOT NULL DEFAULT 'pending',
    raw_response     JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.7 trades and paper_trades

```sql
CREATE TABLE trades (
    id             BIGSERIAL PRIMARY KEY,
    signal_id      TEXT REFERENCES signals(id),
    mode           TEXT NOT NULL,
    asset          TEXT NOT NULL,
    direction      TEXT NOT NULL,
    entry_price    NUMERIC NOT NULL,
    exit_price     NUMERIC,
    quantity       NUMERIC NOT NULL,
    pnl            NUMERIC,
    pnl_pct        NUMERIC,
    opened_at      TIMESTAMPTZ NOT NULL,
    closed_at      TIMESTAMPTZ,
    close_reason   TEXT
);
```

`paper_trades` uses the same shape and is the default sink in paper mode.

### 2.8 candles (TimescaleDB hypertable)

```sql
CREATE TABLE candles (
    symbol     TEXT NOT NULL,
    timeframe  TEXT NOT NULL,
    ts         TIMESTAMPTZ NOT NULL,
    open       NUMERIC NOT NULL,
    high       NUMERIC NOT NULL,
    low        NUMERIC NOT NULL,
    close      NUMERIC NOT NULL,
    volume     NUMERIC NOT NULL
);

SELECT create_hypertable('candles', 'ts');
```

### 2.9 channel_stats (weekly credibility inputs)

```sql
CREATE TABLE channel_stats (
    channel_id       BIGINT PRIMARY KEY REFERENCES channels(id),
    period_start     DATE NOT NULL,
    signals          INTEGER NOT NULL DEFAULT 0,
    wins             INTEGER NOT NULL DEFAULT 0,
    losses           INTEGER NOT NULL DEFAULT 0,
    avg_confidence   NUMERIC(5,2),
    avg_pnl_pct      NUMERIC(6,3),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 3. Redis streams

| Stream | Producer | Consumer | Payload |
| :--- | :--- | :--- | :--- |
| `raw_news` | Ingestor | Analyzer | normalized message with metadata |
| `analyzed_news` | Analyzer | Signal engine | structured analysis plus enrichment |
| `signals` | Signal engine | API, executor | full signal object |
| `orders` | Executor | API, audit | order state transitions |

Use consumer groups so each stage can scale horizontally and replay on failure.

```text
XADD raw_news * channel_id 123 message_id 456 text "..."
XGROUP CREATE raw_news analyzers 0 MKSTREAM
XREADGROUP GROUP analyzers worker-1 COUNT 10 BLOCK 5000 STREAMS raw_news >
XACK raw_news analyzers <id>
```

## 4. REST API contracts

### GET /api/news

Query: `coin`, `event_type`, `urgency`, `channel_id`, `since`, `limit`.

Response item:

```json
{
  "id": 1,
  "headline": "Binance will list SOL on spot",
  "coins": ["SOL"],
  "event_type": "listing",
  "sentiment": "bullish",
  "sentiment_score": 0.82,
  "urgency": "high",
  "source_count": 4,
  "first_seen_at": "2026-01-01T10:00:00Z"
}
```

### GET /api/signals

Query: `confidence_min`, `direction`, `asset`, `status`, `limit`.

Response item:

```json
{
  "signal_id": "uuid",
  "asset": "SOL/USDT",
  "direction": "LONG",
  "entry_zone": [145.2, 146.0],
  "stop_loss": 143.5,
  "take_profits": [148.0, 150.5, 155.0],
  "leverage_suggested": 3,
  "timeframe": "1h",
  "confidence": 78,
  "risk_reward": 2.8,
  "rationale": "Binance listing plus corroboration from four channels",
  "expires_at": "2026-01-01T14:00:00Z"
}
```

## 5. Authentication and authorization

- Users authenticate with email plus a one-time code or OAuth.
- API tokens are short-lived; refresh tokens rotate.
- Trade execution endpoints require re-authentication or a 2FA confirm.
- Per-user settings include trading mode, risk limits, and muted channels.

## 6. Data retention

- Raw messages: keep indefinitely for backtesting, or archive after 12 months.
- Candles: keep 1-minute data for 90 days, 1-hour data indefinitely.
- Audit logs for orders and trades: keep indefinitely.
- Embeddings: recompute if the model changes.
