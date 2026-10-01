# 09 - Implementation Guide

A concrete build order from empty repository to a validated MVP. Follow the
phases and respect the go/no-go gates in `08-roadmap-costs-and-security.md`.

## 1. Development environment

Prerequisites:

- Python 3.11 or newer
- Flutter SDK (for the app)
- Docker and Docker Compose
- PostgreSQL and Redis (via Docker is fine)

Setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --break-system-packages fastapi uvicorn sqlalchemy alembic asyncpg redis telethon ccxt pydantic pydantic-settings python-dotenv httpx
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
    max_leverage: int = 5
    kill_switch: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
```

Provide `.env.example` with placeholders only. The project reads its own
project-scoped variables; never hardcode platform credentials.

## 3. Build order

### Step 0: Decisions and scaffolding (do this before coding)

1. Confirm scope: single operator, self-hosted v1.
2. Set up the repo layout from `01-overview-and-architecture.md`.
3. Set up Docker Compose and the database.
4. Create the labeled evaluation set skeleton (you will fill it as data arrives).

### Step 1: Database and migrations

1. Define SQLAlchemy models from `06-data-model-and-api.md`.
2. Set up Alembic; create the initial migration.
3. Add idempotency constraints (unique keys) before writing any consumers.

### Step 2: Telegram ingestor

1. `login.py`; log in once and store the session.
2. `queue.py` with `publish_raw` to Redis `raw_news`.
3. `listener.py` with gap recovery using `min_id`.
4. `backfill.py` for history and reconnect recovery.
5. `normalize.py` and dedup/clustering with origin attribution.
6. Media OCR and vision handling.
7. Dead-letter stream and health metrics.

### Step 3: Analysis

1. Fast relevance filter and the fast path templates.
2. Hardened, versioned LLM prompt with schema validation and injection checks.
3. Coin resolution against exchange markets.
4. Enrichment (price, liquidity, corroboration, macro window).
5. Persist and publish to `analyzed_news`.
6. Build the labeled evaluation set and run metrics per prompt version.

### Step 4: Signals, confidence, risk

1. Confidence formula from `07` with confidence and market risk kept separate.
2. Technical level calculation with ATR.
3. Risk manager with limits, correlation cap, and kill switch.
4. Publish signals to the `signals` stream.
5. Paper trading with full logging.

### Step 5: API and read-only app (ship early)

1. REST endpoints for news, signals, portfolio, channels.
2. Authenticated WebSocket push.
3. Flutter screens and connection.
4. Notifications (Android push, Windows toast fallback).

### Step 6: Trading executor

1. CCXT adapter with sandbox mode, depth, funding, and spread checks.
2. Paper trading first.
3. Idempotent order placement with a deterministic `client_order_id`.
4. Startup reconciliation and protective-order repair.
5. Live order placement behind an explicit toggle, max-notional cap, and the
   kill switch.

### Step 7: Backtesting and tuning

1. Replay harness over stored history.
2. Walk-forward validation; report metrics on held-out data.
3. Calibrate confidence weights to realized outcomes.
4. Paper trade for 4-6 weeks and compare to the backtest.

## 4. Testing strategy

- Unit tests for normalization, dedup/clustering, the confidence formula, and
  the risk manager (pure functions).
- Integration tests for the Redis stream pipeline with test containers.
- Mock the LLM; record real responses as fixtures for representative cases.
- **Injection tests**: feed adversarial messages and assert the model does not
  comply and the anomaly detector flags them.
- **Idempotency tests**: deliver the same message twice; assert one news cluster
  and one signal.
- Never call a real exchange with live keys in tests; use sandbox or mocks.

Example confidence test:

```python
from app.services.signals.confidence import compute_confidence


def test_confidence_increases_with_corroboration():
    base = compute_confidence(
        source_credibility=0.5,
        llm_certainty=0.5,
        independent_origins=1,
        sentiment_score=0.5,
        event_type="other",
    )
    more = compute_confidence(
        source_credibility=0.5,
        llm_certainty=0.5,
        independent_origins=4,
        sentiment_score=0.5,
        event_type="other",
    )
    assert more > base
```

Example commands (comments go on their own line):

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

- [ ] Ingestor reads public and private channels with gap recovery.
- [ ] News is normalized, deduplicated, clustered, and analyzed into JSON.
- [ ] Analysis quality is measured on a labeled set with injection tests passing.
- [ ] Signals have entry, stop, partial TPs, and a calibrated confidence score.
- [ ] A deterministic risk gate with correlation limits controls every order.
- [ ] Paper trading runs end to end with an audit log.
- [ ] The app shows the feed and signals on Windows and Android.
- [ ] A backtest report exists with walk-forward metrics on held-out data.

## 7. Common pitfalls

- Using the Bot API for private channels; it will not work.
- Scraping without clustering, so forwards inflate apparent corroboration.
- Letting the LLM invent price levels or sizes.
- Multiplying confidence by volatility and silently disabling high-confidence
  signals.
- Storing exchange keys on the client.
- Assuming FCM works on Windows desktop.
- Skipping the risk gate, the evaluation set, or the paper-trading gate.
- Committing secrets or the session file to git.
