# 09 - Implementation Guide

A concrete build order so you can go from empty repository to a working MVP.
Follow the phases, and do not skip ahead: each stage depends on the previous one.

## 1. Development environment

Prerequisites:

- Python 3.11 or newer
- Node.js only if you add web tooling
- Flutter SDK for the app
- Docker and Docker Compose
- PostgreSQL and Redis (via Docker is fine)

Initial setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --break-system-packages fastapi uvicorn sqlalchemy alembic asyncpg redis telethon ccxt pydantic python-dotenv httpx
```

## 2. Configuration

File: `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tg_api_id: int
    tg_api_hash: str
    tg_session_name: str = "newstrade_ingestor"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    llm_api_key: str
    llm_model: str = "gpt-4o-mini"
    trading_mode: str = "paper"
    confidence_min: int = 60
    max_daily_loss_pct: float = 3.0

    class Config:
        env_file = ".env"


settings = Settings()
```

Provide `.env.example` with placeholder values only. The project must read its
own `USER_`- or project-scoped variables; never hardcode platform credentials.

## 3. Build order

### Step 1: Database and migrations

1. Define SQLAlchemy models matching `06-data-model-and-api.md`.
2. Set up Alembic and create the initial migration.
3. Run migrations against a local Postgres.

### Step 2: Telegram ingestor

1. Implement `login.py` and log in once to create the session.
2. Implement `queue.py` with `publish_raw` writing to Redis `raw_news`.
3. Implement `listener.py` and verify a live post arrives.
4. Implement `backfill.py` and load history for one channel.
5. Add `normalize.py` and `dedup.py`.
6. Add media OCR and vision handling.

### Step 3: Analysis worker

1. Implement the relevance filter.
2. Implement the LLM client with JSON validation and retries.
3. Implement enrichment (price, market cap, corroboration).
4. Persist news items and publish to `analyzed_news`.

### Step 4: Signal engine

1. Implement the confidence formula from `07-confidence-risk-and-backtesting.md`.
2. Implement technical level calculation with ATR.
3. Implement the risk manager.
4. Publish signals to the Redis `signals` stream.

### Step 5: API and app

1. Implement REST endpoints for news, signals, portfolio, channels.
2. Implement WebSocket push.
3. Build the Flutter screens and connect them.
4. Add FCM notifications.

### Step 6: Trading executor

1. Implement the CCXT adapter with sandbox mode.
2. Implement paper trading first, with full logging.
3. Implement live order placement behind an explicit toggle.
4. Add reconciliation on startup.

### Step 7: Backtesting and tuning

1. Build the replay harness over stored history.
2. Produce the metrics report.
3. Tune confidence weights and thresholds.
4. Run paper trading for 4-6 weeks.

## 4. Testing strategy

- Unit tests for normalization, deduplication, the confidence formula, and the
  risk manager, since these are pure functions and easy to test.
- Integration tests for the Redis stream pipeline using a test container.
- Mock the LLM in tests; record real responses in fixtures for a few cases.
- Never let tests call a real exchange with live keys; use sandbox or mocks.

Example unit test:

```python
from app.services.signals.confidence import compute_confidence


def test_confidence_increases_with_corroboration():
    base = compute_confidence(
        source_credibility=0.5,
        llm_certainty=0.5,
        corroboration_count=1,
        sentiment_score=0.5,
        btc_atr_pct=2.0,
    )
    more = compute_confidence(
        source_credibility=0.5,
        llm_certainty=0.5,
        corroboration_count=4,
        sentiment_score=0.5,
        btc_atr_pct=2.0,
    )
    assert more > base
```

Examples of commands to run (comments go on their own line):

```bash
pytest backend/tests -q
alembic upgrade head
```

## 5. Local run

Start dependencies:

```bash
docker compose -f deploy/docker-compose.yml up -d postgres redis
```

Run the pipeline in separate terminals:

```bash
python -m app.services.ingestion.listener
python -m app.services.analysis.worker
python -m app.services.signals.worker
uvicorn app.main:app --reload --port 8080
```

## 6. Definition of done for the MVP

- [ ] Ingestor reads public and private channels in real time.
- [ ] News is normalized, deduplicated, and analyzed into structured JSON.
- [ ] Signals have entry, stop loss, take profits, and a confidence score.
- [ ] A risk manager gates every order.
- [ ] Paper trading runs end to end with an audit log.
- [ ] The Flutter app shows the feed and signals on Windows and Android.
- [ ] Backtest report exists with the standard metrics.

## 7. Common pitfalls

- Using the Bot API for private channels. It will not work; use a user session.
- Scraping without deduplication, which inflates confidence from forwarded news.
- Letting the LLM invent price levels. Anchor levels to real market data.
- Skipping the risk manager. It is the difference between a tool and a liability.
- Going live before backtest and paper trading. Do not skip this.
- Committing secrets or the session file to git.
