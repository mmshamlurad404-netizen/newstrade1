# 05 - Phase 4: Application, Notifications and Deployment

This phase delivers the user-facing app on Windows and Android and the
infrastructure to run everything reliably.

## 1. Backend API (FastAPI)

The API is the only bridge between the database and the apps. It also exposes
manual trade execution and real-time push.

### 1.1 Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/news` | List news, filter by coin, event, urgency, channel, time |
| GET | `/api/news/{id}` | News detail with analysis and source messages |
| GET | `/api/signals` | List signals, filter by confidence and direction |
| GET | `/api/signal/{id}` | Signal detail with rationale and source news |
| POST | `/api/signal/{id}/execute` | Execute a signal manually (auth + confirm) |
| GET | `/api/portfolio` | Open positions and PnL from the exchange |
| GET | `/api/trades` | Historical trades and paper trades |
| GET | `/api/channels` | Tracked channels with credibility scores |
| POST | `/api/channels` | Add or remove a tracked channel |
| GET | `/api/health` | Liveness and stage lag metrics |
| WS | `/ws/news` | Real-time news push |
| WS | `/ws/signals` | Real-time signal push |

### 1.2 Skeleton

File: `backend/app/api/routes.py`

```python
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api")


@router.get("/signals")
async def list_signals(
    confidence_min: int = Query(0, ge=0, le=100),
    direction: str | None = None,
    limit: int = Query(50, le=200),
    session=Depends(get_session),
):
    return await signal_service.list_signals(
        session, confidence_min=confidence_min, direction=direction, limit=limit
    )
```

### 1.3 WebSocket push

```python
@router.websocket("/ws/signals")
async def ws_signals(ws: WebSocket):
    await ws.accept()
    async for signal in pubsub.subscribe("signals"):
        await ws.send_json(signal)
```

## 2. Mobile and desktop app (Flutter)

One Dart codebase builds for Windows and Android.

### 2.1 Screens

1. **News feed**: real-time list, filters by coin, urgency, channel; shows
   sentiment badges and a tap-through to the source message.
2. **Signal card**: asset, direction badge (green LONG, red SHORT), confidence
   bar, entry zone, stop loss, take profits, rationale, source links, and an
   "Execute" button (disabled in paper mode).
3. **Portfolio**: open positions, unrealized and realized PnL, trade history,
   pulled from the exchange through the backend.
4. **Channels**: list of tracked channels with credibility score and per-channel
   performance.
5. **Settings**: API keys (stored in the OS secure storage), risk settings, push
   preferences, and the global trading mode toggle.

### 2.2 State and networking

- HTTP client with retry and auth token.
- WebSocket connection for live updates with automatic reconnect.
- Local cache so the feed is readable offline.

### 2.3 Build targets

```bash
flutter build windows
flutter build apk --release
```

## 3. Push notifications

- Use Firebase Cloud Messaging (FCM) for Android and Windows.
- Backend publishes to FCM when a signal crosses the confidence threshold
  (default 75) or when a high-urgency news item arrives.
- Users can mute per channel, per coin, or globally.

Notification payload includes asset, direction, confidence, and a deep link to
the signal card.

## 4. Deployment

### 4.1 Docker Compose

File: `deploy/docker-compose.yml`

```yaml
services:
  postgres:
    image: timescale/timescaledb-ha:pg16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/home/postgres/pgdata/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "6379:6379"

  ingestor:
    build: ../backend
    command: ["python", "-m", "app.services.ingestion.listener"]
    env_file: ../backend/.env
    depends_on: [redis, postgres]

  analyzer:
    build: ../backend
    command: ["python", "-m", "app.services.analysis.worker"]
    env_file: ../backend/.env
    depends_on: [redis, postgres]

  signaler:
    build: ../backend
    command: ["python", "-m", "app.services.signals.worker"]
    env_file: ../backend/.env
    depends_on: [redis, postgres]

  api:
    build: ../backend
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
    env_file: ../backend/.env
    ports:
      - "8080:8080"
    depends_on: [postgres, redis]

volumes:
  pgdata:
```

### 4.2 Environments and secrets

- Keep `.env` out of git. Provide `.env.example` with placeholders only.
- Use a secrets manager or Docker secrets in production.
- Store exchange API keys encrypted at rest; never log them.
- Use read-only API keys where possible; disable withdrawal permission always.

### 4.3 Server sizing

| Stage | Suggested VPS | Notes |
| :--- | :--- | :--- |
| Development | 2 vCPU, 4 GB | Local or small cloud instance |
| Staging | 4 vCPU, 8 GB | Real ingestion, paper trading |
| Production | 8 vCPU, 16 GB | 100+ channels, low latency |

Consider a Tokyo or Frankfurt region close to exchange matching engines if
latency matters for the execution path.

### 4.4 Observability

- Structured JSON logs with correlation ids per message.
- Metrics: per-stage queue lag, LLM latency and cost, signal counts, order
  failures.
- Alerts: ingestor disconnected, queue backlog growing, risk limit hit, daily
  loss limit triggered.

### 4.5 Backups

- Nightly Postgres dumps to object storage.
- Session file and secrets backed up securely, separately from code.
- Test the restore procedure at least once.

## 5. Development roadmap

| Phase | Duration | Deliverable |
| :--- | :--- | :--- |
| Phase 0 | Week 1 | Telegram credentials, dedicated account, channel list |
| Phase 1 | Weeks 2-3 | Ingestor writing normalized messages to the queue and DB |
| Phase 2 | Weeks 4-6 | AI analysis working; news feed shows sentiment |
| Phase 3 | Weeks 7-10 | Position extraction, confidence, paper trading |
| Phase 4 | Weeks 11-14 | Flutter app on Windows and Android, notifications |
| Phase 5 | Weeks 15-18 | Backtesting report, tuning, staging at scale |
| Launch | Week 19+ | Small-capital live trading with monitoring |

Full detail, KPIs, and costs are in `08-roadmap-costs-and-security.md`.

## Deliverables for Phase 4

- [ ] FastAPI service with REST and WebSocket endpoints.
- [ ] Flutter app building for Windows and Android.
- [ ] Push notifications through FCM.
- [ ] Docker Compose deployment with Postgres, Redis, and workers.
- [ ] Observability dashboards and alerts.
- [ ] Backup and restore procedure verified.

## Phase 4 acceptance tests

1. A new high-confidence signal appears in the app in under 5 seconds via
   WebSocket.
2. A push notification arrives on Android when a signal crosses the threshold.
3. The Windows build connects, shows the feed, and can execute a paper trade.
4. Killing the ingestor container triggers an alert; restarting it resumes
   ingestion without data loss.
