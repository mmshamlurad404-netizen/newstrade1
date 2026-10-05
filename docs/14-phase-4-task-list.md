# 14 - Phase 4 Implementation Task List

Bite-sized tasks for Phase 4 (API, app, notifications, deployment). Each task
ends with something testable. The Flutter client and observability tasks are the
remaining large items.

## Task 0: API foundation

- [x] Add `api_token` and `cors_origins` settings.
- [x] Implement `backend/app/api/deps.py` with bearer-token auth.
- [x] Implement `backend/app/api/serializers.py` for news, signals, trades,
      channels (Decimal/datetime safe).
- [x] Add `backend/app/schemas/api.py`.
- [x] Wire routers and CORS in `backend/app/main.py`.

## Task 1: REST endpoints

- [x] `GET /api/news` with coin, event_type, urgency, channel_id, since, limit.
- [x] `GET /api/news/{id}` with provenance; private-channel text hidden unless
      `redistribute_content`.
- [x] `GET /api/signals` with confidence_min, direction, asset, status, limit.
- [x] `GET /api/signal/{id}` with linked news.
- [x] `POST /api/signal/{id}/execute` (blocked in paper mode).
- [x] `GET /api/portfolio` with open trades, open risk, realized PnL day/week.
- [x] `GET /api/trades` across paper and live modes.
- [x] `GET /api/channels` with credibility.
- [x] `GET /api/health` (public liveness).

## Task 2: Kill switch

- [x] Implement `backend/app/core/runtime.py` backed by Redis.
- [x] `GET`/`POST /api/kill-switch`.
- [x] Signaler reads the runtime kill switch each cycle.

## Task 3: WebSocket push

- [x] Authenticated `WS /ws/news` on `fast_alerts`.
- [x] Authenticated `WS /ws/signals` on `signals`.
- [x] Reject unauthenticated sockets with close code 4401.
- [x] Heartbeat ping when idle.
- [ ] Client reconnect with backoff (Flutter).

## Task 4: API tests

- [x] Health is public; protected routes return 401 without/with bad token.
- [x] WebSocket rejects a bad token.
- [x] Serializer tests for signal and news edge cases.

## Task 5: Flutter app (Windows + Android)

- [ ] Project scaffold with REST client and short-lived session token.
- [ ] News feed screen with filters and sentiment badges.
- [ ] Signal card with confidence bar, levels, expiry countdown, fast-alert
      state.
- [ ] Portfolio screen (positions, realized/unrealized PnL, history).
- [ ] Channels and settings screens; kill switch always reachable.
- [ ] Paper default; live toggle behind explicit confirmation and 2FA.
- [ ] `flutter build windows` and `flutter build apk --release`.

## Task 6: Notifications

- [ ] Android via FCM for signals above the confidence threshold.
- [ ] Windows toast via the WebSocket fallback.
- [ ] In-app badges and per-channel/coin mute; debounce and group.

## Task 7: Deployment and observability

- [ ] Verify migrations run before workers in compose.
- [ ] Queue-lag, LLM cost, signal-count, order-failure metrics.
- [ ] Alerts for disconnect, backlog, risk-limit hit, daily loss stop.
- [ ] Nightly Postgres backup and a tested restore.

## Phase 4 acceptance tests

1. A new high-confidence signal appears in the app within 5 seconds over
   WebSocket.
2. An Android push arrives and a Windows toast appears.
3. The Windows build shows the feed and can run a paper trade.
4. Killing the ingestor alerts; restarting resumes without data loss.
5. The app cannot access exchange keys or place an order without the backend.
