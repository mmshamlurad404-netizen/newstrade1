# 05 - Phase 4: Application, Notifications and Deployment

This phase delivers the user-facing app on Windows and Android and the
infrastructure to run everything reliably.

## 1. Backend API (FastAPI)

The API is the only bridge between the database and the apps. It also exposes
manual actions and real-time push.

### 1.1 Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/news` | List news, filter by coin, event, urgency, channel, time |
| GET | `/api/news/{id}` | News detail with analysis and source messages |
| GET | `/api/signals` | List signals, filter by confidence and direction |
| GET | `/api/signal/{id}` | Signal detail with rationale and source news |
| POST | `/api/signal/{id}/execute` | Execute a signal (auth plus explicit confirm) |
| POST | `/api/portfolio/flatten` | Flatten all positions (dangerous, 2FA) |
| POST | `/api/kill-switch` | Enable or disable the kill switch |
| GET | `/api/portfolio` | Open positions and PnL from the exchange |
| GET | `/api/trades` | Historical trades and paper trades |
| GET | `/api/channels` | Tracked channels with credibility scores |
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

### 1.3 WebSocket push with authentication

Do not expose an unauthenticated WebSocket that leaks trading data.

```python
@router.websocket("/ws/signals")
async def ws_signals(ws: WebSocket, token: str = Query(...)):
    if not auth.verify(token):
        await ws.close(code=4401)
        return
    await ws.accept()
    async for signal in pubsub.subscribe("signals"):
        await ws.send_json(serialize(signal))
```

Add heartbeat/ping and reconnect-with-backoff on the client.

## 2. Secrets and key custody (critical)

**Exchange API keys never leave the server.** The Flutter app must not store
exchange keys, even in OS secure storage. If the client is compromised, it must
not be able to move funds.

- Client authenticates to your backend and receives a short-lived session token.
- The backend holds exchange keys, encrypted at rest, and is the only component
  that calls the exchange.
- Use exchange keys with trading enabled only if needed, **withdrawals disabled**,
  and an IP allowlist.
- Store secrets in a secrets manager or encrypted Docker secrets.
- Add 2FA or re-authentication on `execute`, `flatten`, and `kill-switch`.

## 3. Mobile and desktop app (Flutter)

One Dart codebase builds for Windows and Android.

### 3.1 Screens

1. **News feed**: real-time list with filters by coin, urgency, channel;
   sentiment badges; tap-through to source messages.
2. **Signal card**: asset, direction badge (green LONG, red SHORT), confidence
   bar, entry zone, stop loss, take profits, rationale, source links, expiry
   countdown, and an Execute button (disabled in paper mode). Show a
   "fast alert, unverified" state for fast-path events.
3. **Portfolio**: open positions, unrealized and realized PnL, trade history,
   from the exchange through the backend.
4. **Channels**: tracked channels with credibility score and performance.
5. **Settings**: risk settings, notification preferences, trading mode toggle,
   and the kill switch.

### 3.2 Trading safety in the UI

- Default mode is Paper; switching to live requires a deliberate confirmation.
- The kill switch is always one tap away and clearly visible in live mode.
- Show current open risk and remaining daily loss budget at the top.
- Never show an "auto trade" toggle without a max-notional cap alongside it.

### 3.3 Build targets

```bash
flutter build windows
flutter build apk --release
```

## 4. Notifications

FCM officially targets Android, iOS, and web. **Windows desktop is not
officially supported by Flutter's FCM plugin.** Plan for this:

- Android: Firebase Cloud Messaging.
- Windows: local notifications driven by the existing WebSocket connection
  (for example a Windows toast via a notification package), or a push provider
  that supports Windows. Fall back to the WebSocket-based toast.
- Always also show in-app badges so a missed OS notification is not a missed
  signal.

Backend triggers a notification when a signal crosses the confidence threshold
(default 75) or a high-urgency news item arrives. Users can mute per channel,
coin, or globally. Debounce and group to avoid notification fatigue.

## 5. Deployment

### 5.1 Docker Compose

File: `deploy/docker-compose.yml`

```yaml
services:
  postgres:
    image: timescale/timescaledb-ha:pg16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/home/postgres/pgdata/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
    restart: unless-stopped

  ingestor:
    build: ../backend
    command: ["python", "-m", "app.services.ingestion.listener"]
    env_file: ../backend/.env
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    restart: unless-stopped

  analyzer:
    build: ../backend
    command: ["python", "-m", "app.services.analysis.worker"]
    env_file: ../backend/.env
    restart: unless-stopped

  signaler:
    build: ../backend
    command: ["python", "-m", "app.services.signals.worker"]
    env_file: ../backend/.env
    restart: unless-stopped

  executor:
    build: ../backend
    command: ["python", "-m", "app.services.trading.worker"]
    env_file: ../backend/.env
    restart: unless-stopped

  api:
    build: ../backend
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
    env_file: ../backend/.env
    ports:
      - "8080:8080"
    depends_on: [postgres, redis]
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

### 5.2 Deployment hardening

- Run migrations as a one-shot job before starting workers.
- Set `restart: unless-stopped` and container memory/CPU limits.
- Add log rotation and structured JSON logs with correlation ids.
- Expose only the API port; keep Postgres and Redis on the internal network.
- Put the API behind TLS (reverse proxy) and require auth on all routes.
- Do not run the executor with live keys until the go-live gates in `08` pass.

### 5.3 Environments and secrets

- `.env` is never committed; provide `.env.example` with placeholders.
- Development, staging, and production use separate keys and databases.
- Staging runs real ingestion but paper trading only.

### 5.4 Server sizing

| Stage | Suggested VPS | Notes |
| :--- | :--- | :--- |
| Development | 2 vCPU, 4 GB | Local or small cloud instance |
| Staging | 4 vCPU, 8 GB | Real ingestion, paper trading |
| Production | 8 vCPU, 16 GB | 100+ channels, low latency |

Consider a region close to the exchange matching engines if execution latency
matters.

### 5.5 Observability and alerting

- Metrics: per-stage queue lag, LLM latency/cost, signal counts, order failures,
  reconnect count, DLQ size.
- Alerts: ingestor disconnected, no messages from a channel, queue backlog,
  risk limit hit, daily loss stop, executor position mismatch.

### 5.6 Backups

- Nightly Postgres dumps to object storage; test the restore.
- Session file and secrets backed up securely, separately from code.

## 6. Development roadmap

| Phase | Duration | Deliverable |
| :--- | :--- | :--- |
| Phase 0 | Week 1 | Telegram credentials, dedicated account, channel list |
| Phase 1 | Weeks 2-3 | Ingestor writing normalized messages to queue and DB |
| Phase 2 | Weeks 4-6 | Analysis plus a read-only news app (ship early) |
| Phase 3 | Weeks 7-10 | Signals, confidence, risk, paper trading |
| Phase 4 | Weeks 11-13 | App on Windows and Android, notifications, deployment |
| Phase 5 | Weeks 14-18 | Backtesting, tuning, staging at scale |
| Phase 6 | Week 19+ | Small-capital live trading with monitoring |

Note the change from the first draft: ship a read-only news app during Phase 2
to validate the feed early, before building trading.

Full gates, KPIs, and costs are in `08-roadmap-costs-and-security.md`.

## Deliverables for Phase 4

- [ ] FastAPI service with authenticated REST and WebSocket endpoints.
- [ ] Flutter app building for Windows and Android.
- [ ] Android push plus a Windows notification fallback.
- [ ] Docker Compose deployment with migrations, health checks, restarts.
- [ ] Observability dashboards and alerts.
- [ ] Backup and restore procedure verified.

## Phase 4 acceptance tests

1. A new high-confidence signal appears in the app within 5 seconds via
   WebSocket.
2. An Android push arrives when a signal crosses the threshold, and a Windows
   toast appears as well.
3. The Windows build connects, shows the feed, and can execute a paper trade.
4. Killing the ingestor container triggers an alert; restarting it resumes
   ingestion without data loss.
5. The app cannot access exchange keys or place an order without the backend.
