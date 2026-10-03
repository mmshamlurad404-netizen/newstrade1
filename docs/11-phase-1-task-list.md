# 11 - Phase 1 Implementation Task List

Bite-sized tasks for Phase 1 (Telegram ingestion). Each task ends with something
testable. Check the box when done. Respect gate G1 in
`08-roadmap-costs-and-security.md` before moving to Phase 2.

## Task 0: Repository and environment

- [ ] Create `backend/` layout from `01-overview-and-architecture.md`.
- [ ] Add `backend/requirements.txt` and `backend/pyproject.toml`.
- [ ] Add `backend/.env.example` with placeholders only.
- [ ] Run `docker compose -f deploy/docker-compose.yml up -d postgres redis`.
- [ ] Verify `alembic upgrade head` creates the Phase 1 tables.

## Task 1: Configuration and logging

- [ ] Implement `backend/app/core/config.py` reading `TG_API_ID`, `TG_API_HASH`,
      `TG_SESSION_NAME`, `DATABASE_URL`, `REDIS_URL`, `LLM_API_KEY`.
- [ ] Implement `backend/app/core/logging.py` with JSON structured logs.
- [ ] Test: settings load from env and fail fast when required values are
      missing.

## Task 2: Database session and models

- [ ] Implement `backend/app/db/base.py` and `backend/app/db/session.py`.
- [ ] Implement models: `ingestion_accounts`, `channels`, `raw_messages`,
      `news`, `news_sources` in `backend/app/models/`.
- [ ] Add unique keys: `(channel_id, message_id)` on raw messages,
      `canonical_hash` on news.
- [ ] Generate and apply the initial Alembic migration.

## Task 3: Normalization

- [ ] Implement `backend/app/services/ingestion/normalize.py`:
      `normalize(text) -> (clean_text, links)`, control-character stripping,
      delimiter neutralization.
- [ ] Unit test emoji/URL/zero-width handling and idempotence.

## Task 4: Deduplication helpers

- [ ] Implement `backend/app/services/ingestion/dedup.py`:
      `content_hash`, `token_set`, `jaccard`, `is_duplicate`,
      `structured_key(event_type, coin, bucket_minutes)`.
- [ ] Unit test that near-identical text is a duplicate and unrelated text is
      not.

## Task 5: Queue

- [ ] Implement `backend/app/services/ingestion/queue.py` with Redis Streams:
      `publish_raw`, `publish_dlq`, `publish_analyzed`, `ensure_groups`.
- [ ] Test: publish then read back via a consumer group, and re-deliver the same
      id without duplication.

## Task 6: Channel state

- [ ] Implement `backend/app/services/ingestion/state.py`:
      `load_tracked_channels`, `update_last_message_id`, `record_flood_wait`.
- [ ] Test: update and reload `last_message_id`.

## Task 7: Telegram login and listener

- [ ] Implement `backend/app/services/ingestion/login.py` (interactive once).
- [ ] Implement `backend/app/services/ingestion/listener.py`:
      `events.NewMessage`, normalize, publish, persist last id.
- [ ] On startup, close the disconnect gap using `min_id` per channel.

## Task 8: Backfill and gap recovery

- [ ] Implement `backend/app/services/ingestion/backfill.py` using
      `iter_messages(channel, min_id=last_id, limit=N)`.
- [ ] Test: disconnect, post messages, reconnect, assert all recovered exactly
      once.

## Task 9: Media extraction

- [ ] Implement `backend/app/services/ingestion/media.py` OCR via Tesseract.
- [ ] Gate media downloads by relevance to control bandwidth.
- [ ] Vision-model extraction is a follow-up (Phase 2 enrichment).

## Task 10: Cluster worker (dedup and corroboration)

- [ ] Implement `backend/app/services/ingestion/cluster_worker.py`.
- [ ] Idempotent upsert of raw messages; skip already-processed.
- [ ] Exact-hash and near-duplicate clustering within the time window.
- [ ] Origin attribution: earliest post is the originator; forwards do not
      increase `source_count`.
- [ ] Publish to `analyzed_news`.

## Task 11: API health and metrics

- [ ] Implement `backend/app/main.py` with `GET /api/health`.
- [ ] Expose per-stage lag and last-message timestamps.

## Task 12: Observability

- [ ] Structured logs with correlation ids.
- [ ] Stale-channel detector and alerts.
- [ ] DLQ size metric and alert.

## Gate G1 before Phase 2

- [ ] p95 post-to-DB latency under 5 seconds.
- [ ] Zero missed messages across a deliberate reconnect.
- [ ] Duplicate posts produce one cluster and are attributed correctly.
- [ ] Malformed records land in the DLQ and do not stall workers.
- [ ] Session backup and restore procedure written and tested.
