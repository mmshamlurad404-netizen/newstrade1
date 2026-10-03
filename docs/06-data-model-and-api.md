# 06 - Data Model and API Reference

## 1. Storage layout

| Store | Purpose |
| :--- | :--- |
| PostgreSQL | Accounts, channels, news, signals, orders, trades, evals, settings |
| TimescaleDB | OHLCV candles for levels, correlation, and backtesting |
| pgvector | News embeddings for semantic search and clustering |
| Redis | Cache, counters, and durable streams for pipelines |

## 2. PostgreSQL schema

Every write uses an idempotency key, because Redis Streams are at-least-once.
Use `INSERT ... ON CONFLICT` on the natural keys below.

### 2.1 ingestion_accounts

Supports multiple dedicated Telegram sessions if one account hits limits.

```sql
CREATE TABLE ingestion_accounts (
    id             BIGSERIAL PRIMARY KEY,
    label          TEXT NOT NULL UNIQUE,
    session_ref    TEXT NOT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    last_flood_wait_at TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.2 channels

```sql
CREATE TABLE channels (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        TEXT,
    title           TEXT NOT NULL,
    is_private      BOOLEAN NOT NULL DEFAULT FALSE,
    redistribute_content BOOLEAN NOT NULL DEFAULT FALSE,
    credibility     NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    account_id      BIGINT REFERENCES ingestion_accounts(id),
    last_message_id BIGINT,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`redistribute_content` defaults to false so private-channel text is not shown
publicly without an explicit decision.

### 2.3 raw_messages

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

### 2.4 news (clustered, deduplicated events)

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
    asset_resolved   BOOLEAN NOT NULL DEFAULT FALSE,
    embedding        vector(1536),
    source_count     INTEGER NOT NULL DEFAULT 1,
    origin_channel_id BIGINT REFERENCES channels(id),
    first_seen_at    TIMESTAMPTZ NOT NULL,
    last_seen_at     TIMESTAMPTZ NOT NULL,
    prompt_version   TEXT,
    model_name       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_news_coins ON news USING GIN (coins);
CREATE INDEX idx_news_first_seen ON news (first_seen_at DESC);
CREATE INDEX idx_news_embedding ON news USING ivfflat (embedding vector_cosine_ops);
```

### 2.5 news_sources (corroboration and provenance)

```sql
CREATE TABLE news_sources (
    news_id        BIGINT NOT NULL REFERENCES news(id),
    raw_message_id BIGINT NOT NULL REFERENCES raw_messages(id),
    channel_id     BIGINT NOT NULL REFERENCES channels(id),
    is_origin      BOOLEAN NOT NULL DEFAULT FALSE,
    similarity     NUMERIC(4,3) NOT NULL DEFAULT 1.000,
    PRIMARY KEY (news_id, raw_message_id)
);
```

Corroboration counts only rows where `is_origin` is true.

### 2.6 signals with a lifecycle

```sql
CREATE TABLE signals (
    id                TEXT PRIMARY KEY,
    news_id           BIGINT REFERENCES news(id),
    asset             TEXT NOT NULL,
    direction         TEXT NOT NULL,
    entry_low         NUMERIC NOT NULL,
    entry_high        NUMERIC NOT NULL,
    order_type        TEXT NOT NULL DEFAULT 'limit',
    stop_loss         NUMERIC NOT NULL,
    take_profits      NUMERIC[] NOT NULL,
    leverage_suggested INTEGER NOT NULL DEFAULT 1,
    timeframe         TEXT NOT NULL,
    confidence        INTEGER NOT NULL,
    market_risk_factor NUMERIC(4,3) NOT NULL DEFAULT 1.000,
    rationale         TEXT,
    risk_reward       NUMERIC(6,2),
    status            TEXT NOT NULL DEFAULT 'new',
    prompt_version    TEXT,
    expires_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_signals_confidence ON signals (confidence DESC, created_at DESC);
```

Signal status lifecycle:

```text
new -> active -> filled -> closed
          \-> expired
          \-> rejected  (risk gate or user)
          \-> cancelled (entry not filled)
```

### 2.7 orders

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
    role             TEXT NOT NULL DEFAULT 'entry',
    quantity         NUMERIC NOT NULL,
    price            NUMERIC,
    status           TEXT NOT NULL DEFAULT 'pending',
    raw_response     JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`client_order_id` is unique for idempotency. `role` is entry, stop, or
take_profit so protective orders can be repaired on reconciliation.

### 2.8 trades and paper_trades

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
    fees           NUMERIC,
    funding        NUMERIC,
    opened_at      TIMESTAMPTZ NOT NULL,
    closed_at      TIMESTAMPTZ,
    close_reason   TEXT
);
```

`paper_trades` uses the same shape and is the default sink in paper mode.

### 2.9 candles (TimescaleDB hypertable)

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

### 2.10 prompt_versions and analysis evaluation

```sql
CREATE TABLE prompt_versions (
    id          TEXT PRIMARY KEY,
    template    TEXT NOT NULL,
    model_name  TEXT NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE eval_labels (
    id               BIGSERIAL PRIMARY KEY,
    raw_message_id   BIGINT REFERENCES raw_messages(id),
    label_coins      TEXT[],
    label_event_type TEXT,
    label_sentiment  TEXT,
    label_tradable   BOOLEAN,
    is_adversarial   BOOLEAN NOT NULL DEFAULT FALSE,
    labeled_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE eval_runs (
    id             BIGSERIAL PRIMARY KEY,
    prompt_version TEXT REFERENCES prompt_versions(id),
    coin_f1        NUMERIC(5,4),
    event_accuracy NUMERIC(5,4),
    tradable_f1    NUMERIC(5,4),
    injection_pass BOOLEAN,
    run_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.11 channel_stats (weekly credibility inputs)

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

Only originator signals count toward a channel's accuracy.

## 3. Redis streams

| Stream | Producer | Consumer | Payload |
| :--- | :--- | :--- | :--- |
| `raw_news` | Ingestor | Cluster worker | normalized message with metadata |
| `clustered_news` | Cluster worker | Analyzer (fast path plus LLM) | deduplicated news cluster reference |
| `fast_alerts` | Analyzer fast path | API, notifier | immediate high-precision event alert |
| `analyzed_news` | Analyzer | Signal engine | analysis plus enrichment |
| `signals` | Signal engine | API, executor | full signal object |
| `orders` | Executor | API, audit | order state transitions |
| `dlq` | Any stage | Ops | failed payload plus error |

Use consumer groups plus `XACK`; on repeated failure move to the DLQ.

```text
XADD raw_news * channel_id 123 message_id 456 text "..."
XGROUP CREATE raw_news pipeline 0 MKSTREAM
XREADGROUP GROUP pipeline clusterer-1 COUNT 10 BLOCK 5000 STREAMS raw_news >
XACK raw_news pipeline <id>
```

## 4. REST API contracts

### GET /api/news

Query: `coin`, `event_type`, `urgency`, `channel_id`, `since`, `limit`.

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
  "origin_channel": "ExampleChannel",
  "first_seen_at": "2026-01-01T10:00:00Z"
}
```

### GET /api/signals

Query: `confidence_min`, `direction`, `asset`, `status`, `limit`.

```json
{
  "signal_id": "uuid",
  "asset": "SOL/USDT",
  "direction": "LONG",
  "entry_low": 145.2,
  "entry_high": 146.0,
  "order_type": "limit",
  "stop_loss": 143.5,
  "take_profits": [148.0, 150.5, 155.0],
  "leverage_suggested": 3,
  "timeframe": "1h",
  "confidence": 78,
  "market_risk_factor": 0.8,
  "status": "new",
  "risk_reward": 2.8,
  "rationale": "Binance listing plus corroboration from four origin channels",
  "expires_at": "2026-01-01T14:00:00Z"
}
```

## 5. Authentication and authorization (v1 = single operator)

- v1: a small number of operator accounts with strong auth and 2FA.
- Short-lived session tokens; refresh tokens rotate.
- `execute`, `flatten`, and `kill-switch` require re-auth or 2FA.
- Per-account settings: mode, risk limits, muted channels.
- Multi-user tenancy is a later product with a separate design.

## 6. Data retention

- Raw messages: keep for backtesting; archive after 12 months if needed.
- Private-channel content: internal by default; never redistributed unless the
  channel explicitly allows it.
- Candles: 1-minute for 90 days, 1-hour indefinitely.
- Orders and trades audit rows: keep indefinitely.
- Embeddings: recompute when the embedding model changes.
