# 15 - Web Dashboard and Flutter Client

Two clients share the same backend API:

- `frontend/` - a Vite + React + TypeScript dashboard used for development and
  browser preview. It proxies `/api` and `/ws` to the backend.
- `client/` - the Flutter app for Windows and Android described in `05`.

## 1. Web dashboard (`frontend/`)

### Screens

| Tab | Purpose |
| :--- | :--- |
| News | Filter by coin, event, urgency; live push over `WS /ws/news` |
| Signals | Confidence slider and direction filter; live push over `WS /ws/signals` |
| Portfolio | Equity, open risk, realized PnL day/week/total, positions and history |
| Channels | Tracked channels with credibility and privacy |
| Settings | API token, backend health, kill switch |

### Reverse proxy

`frontend/vite.config.ts` forwards requests so the browser only needs one port:

```ts
server: {
  allowedHosts: [".monkeycode-ai.live"],
  proxy: {
    "/api": { target: "http://localhost:8080", changeOrigin: true },
    "/ws": { target: "ws://localhost:8080", ws: true },
  },
}
```

### Auth

The backend `API_TOKEN` is entered in Settings and stored in `localStorage`.
REST requests send `Authorization: Bearer <token>`; WebSockets pass `?token=`.

### Run

```bash
cd frontend
npm install
npm run dev
```

Build for production:

```bash
npm run build
```

## 2. Flutter app (`client/`)

- `lib/services/api_client.dart` - REST client with bearer auth.
- `lib/services/ws_service.dart` - reconnecting WebSocket used for live news and
  signals, and the Windows notification fallback.
- `lib/screens/` - news, signals, portfolio, channels, settings.
- `lib/widgets/` - confidence bar, direction badge, signal card, news tile.

Platform folders are generated, not committed:

```bash
cd client
flutter create --platforms=android,windows .
flutter pub get
flutter run -d windows --dart-define=API_BASE_URL=http://localhost:8080
```

## 3. Safety invariants in both clients

- Paper mode is the default; live requires an explicit confirmation.
- The kill switch is always reachable and shown in the header when engaged.
- Exchange API keys are never stored on the client; the backend is the only
  component that calls an exchange.
- Private-channel text is hidden unless the channel allows redistribution.

## 4. Local development stack (no Docker)

```bash
# Postgres 15 with pgvector and Redis
apt-get install -y postgresql redis-server
# pgvector is not in the default repo; use the PGDG repo
# then: apt-get install -y postgresql-15-pgvector
service postgresql start
service redis-server start

# Create the database
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE newstrade;"

# Configure backend/.env, then apply migrations
python3 -m alembic upgrade head

# Optional demo rows for the dashboard
psql -h 127.0.0.1 -U postgres -d newstrade -f scripts/seed_demo.sql

# Run the API and the dashboard
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

`backend/.env` is gitignored; use `backend/.env.example` as the template and set
`API_TOKEN` to match `frontend/.env` (`VITE_API_TOKEN`).

## 5. Remaining

- Android FCM wiring and `google-services.json`.
- Windows toast plugin and in-app badge grouping.
- Widget and integration tests against a running backend.
