# 18 - Observability Runbook

Operational guide for the metrics and alerting added in Phase 4. Use this when
an alert fires to diagnose and remediate quickly.

## Surfaces

| Surface | Purpose |
| :--- | :--- |
| `GET /metrics` | Prometheus text exposition (unauthenticated, for scrapers) |
| `GET /api/metrics` | JSON snapshot (token-protected, used by the System tab) |
| System tab (dashboard) | Human view of streams, ingestor, trading, and sources |
| Notifications (Alerts tab / push) | Fired and recovered alerts |

The `monitor` worker evaluates rules every `alert_interval_seconds` and writes
a notification per fired alert; it also writes a recovery notice when a
condition clears. Alerts are de-duplicated per key for
`alert_cooldown_seconds`.

## Alert catalog

| Alert key | Event type | Severity | Meaning |
| :--- | :--- | :--- | :--- |
| `backlog:<stream>` | `alert_backlog` | warning | Undelivered entries on a pipeline stream exceed `alert_backlog_threshold` |
| `dlq` | `alert_dlq` | critical | Dead-letter queue length exceeds `alert_dlq_threshold` |
| `daily_loss` | `alert_daily_loss` | critical | Realized day PnL breaches `-max_daily_loss_pct` of equity |
| `risk_limit` | `alert_risk_limit` | warning | Open paper risk exceeds `alert_open_risk_pct_max` |
| `ingestor_down` | `alert_ingestor_down` | critical | No ingestor heartbeat for `alert_ingestor_stale_seconds` |
| `ingestor_disconnected` | `alert_ingestor_disconnected` | warning | Heartbeat is fresh but the Telegram session is offline |
| `ingestor_reconnecting` | `alert_ingestor_reconnecting` | warning | Reconnects jumped by `alert_ingestor_reconnect_spike` since last check |
| any recovered | `alert_recovered` | info | A previously-firing condition cleared |

## Triage commands

Inspect the raw metrics:

```bash
# Prometheus text (no auth)
curl -s localhost:8080/metrics

# JSON snapshot (token required)
curl -s -H "Authorization: Bearer $API_TOKEN" localhost:8080/api/metrics
```

Inspect Redis streams and consumer lag:

```bash
# Entries per stream
redis-cli xlen raw_news
redis-cli xlen clustered_news
redis-cli xlen analyzed_news
redis-cli xlen signals
redis-cli xlen dlq

# Consumer group lag and pending
redis-cli xinfo groups clustered_news
```

Inspect the ingestor hash:

```bash
redis-cli hgetall runtime:ingestor
```

Check worker container health:

```bash
# From the deploy directory
docker compose ps
docker compose logs --tail=100 analyzer
```

## Incident: `backlog:clustered_news` / `backlog:analyzed_news`

Cause: the downstream worker is slower than the upstream producer, or it is
down. A large, steady `lag` with zero `pending` means the consumer is not
keeping up; a growing `pending` means in-flight reads are stalling.

1. `docker compose ps` to confirm the analyzer/signaler is running.
2. `docker compose logs --tail=200 analyzer` to check for repeated errors
   (LLM failures, DB errors, credential errors).
3. If the worker is down, restart it: `docker compose restart analyzer`.
4. If it is up but slow, check LLM latency/cost logs and the DLQ. A backlog
   that drains after a restart is usually a transient upstream burst.
5. Ensure only one consumer name per worker; duplicate `CONSUMER` ids cause
   reads to be split unpredictably.

`clustered_news` lag above the threshold with the analyzer healthy and
idle typically means the analyzer is failing to `xack` (it acks in a
`finally`, so a stuck DB transaction is the usual suspect).

## Incident: `dlq`

Cause: messages that exhausted retries. Each DLQ entry stores the payload and
the error.

```bash
# Inspect the most recent failures
redis-cli xrevrange dlq + - COUNT 10
```

Common causes and fixes:

- LLM invalid JSON / provider outage: check `analysis` logs; the provider
  fallback should absorb transient failures. Configure `llm_fallback_model`.
- DB constraint or migration drift: run `alembic upgrade head` and check
  `docker compose logs migrator`.
- Bad payload from a source: fix the producer (feed parser / listener).

After fixing the root cause, the DLQ can be trimmed deliberately. Prefer
leaving it as an audit trail and draining only after review.

## Incident: `ingestor_down` / `ingestor_disconnected`

`ingestor_disconnected` (fresh heartbeat, offline) self-heals: the listener
monitor calls `client.connect()` on the next tick. Watch
`newstrade_ingestor_reconnects_total`.

`ingestor_down` (stale heartbeat) means the listener process is gone or
stalled:

1. `docker compose ps` and `docker compose logs --tail=100 ingestor`.
2. If the process is dead, restart it: `docker compose restart ingestor`.
3. If it is alive but not heartbeating, the event loop is blocked; capture a
   stack trace before restarting.
4. `ingestor_reconnecting` firing repeatedly indicates network instability or
   a revoked/expired Telegram session; re-run `python -m
   app.services.ingestion.login` if authentication fails.

## Incident: `daily_loss` / `risk_limit`

These are risk guardrails.

1. Confirm the figure against the Portfolio tab / `GET /api/portfolio`.
2. `daily_loss`: the risk engine already rejects new signals for the day.
   Verify `max_daily_loss_pct` and investigate the losing trades in
   `GET /api/trades?status=closed`.
3. `risk_limit`: reduce exposure with `POST /api/portfolio/flatten` (paper) or
   wait for positions to close. Check `newstrade_paper_open_risk_pct` in the
   metrics snapshot.
4. If behavior is wrong, hit the kill switch: `POST /api/kill-switch
   {"enabled": true}`.

## Recovery notices

Every fired alert produces an `alert_recovered` notification once the
condition clears on a later evaluation. A recovery with no matching fire (for
example after a monitor restart, which resets in-memory state) is benign.
