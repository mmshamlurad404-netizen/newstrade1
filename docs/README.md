# Newstrade1 - Crypto News Trading Platform

A planning package for a Windows + Android application that listens to public and
private Telegram crypto channels, turns the raw messages into structured news,
analyzes them with AI, extracts tradable positions (direction, entry, stop loss,
take profits), scores confidence, and can place orders on crypto exchanges.

## Direct answer: how do I feed news to my app?

You cannot use a Telegram Bot to read private channels reliably. Bots only see
messages in channels where they are explicitly added as admin/member, and they
cannot join a private channel without an invite unless they are already a member.

The correct mechanism is the **MTProto User API** where the program logs in as a
normal Telegram user account (your own account, or a dedicated account that is a
member of every channel you want to follow). The recommended library is
**Telethon** (Python) or **Pyrogram**.

The pipeline is:

```text
Telegram channels (public + private)
        |
        v
MTProto user client (Telethon)  -- real-time NewMessage events + history backfill
        |
        v
Normalize + deduplicate + media OCR/vision
        |
        v
Message queue (Redis Streams)
        |
        v
AI analysis worker (LLM -> structured JSON)
        |
        v
Signal + confidence engine
        |
        v
PostgreSQL (news, signals) -> FastAPI -> Flutter app (Windows/Android)
        |
        v
Risk manager -> CCXT -> Exchange (Binance/Bybit/...)
```

Key rules to keep the feed working:

1. Use a **dedicated Telegram account** with a saved session file, not your
   personal account.
2. Be a **member of every channel you read**. Read only channels you are allowed
   to access.
3. Listen with `events.NewMessage` for real time, and run a periodic history
   backfill for missed messages.
4. Handle `FloodWait` automatically and never run more than one client session
   per account.
5. Deduplicate aggressively: most crypto channels forward the same news.

## Documents

| File | Contents |
| :--- | :--- |
| `01-overview-and-architecture.md` | Vision, scope, end-to-end architecture, tech stack, repo layout |
| `02-phase-1-telegram-ingestion.md` | Phase 1: account setup, Telethon client, history, media, dedup, queue |
| `03-phase-2-analysis-and-signals.md` | Phase 2: filtering, LLM analysis, entity and event extraction |
| `04-phase-3-trading-engine.md` | Phase 3: position extraction, exchange integration, order execution |
| `05-phase-4-app-and-deployment.md` | Phase 4: FastAPI, Flutter app, notifications, Docker deployment |
| `06-data-model-and-api.md` | PostgreSQL schema, Redis streams, REST and WebSocket API |
| `07-confidence-risk-and-backtesting.md` | Confidence formula, source credibility, risk rules, backtesting |
| `08-roadmap-costs-and-security.md` | Phase timeline, KPIs, cost estimate, security and legal notes |
| `09-implementation-guide.md` | Concrete step-by-step build order and starter code layout |

## Reading order

Start with `01`, then implement in phase order `02` -> `03` -> `04` -> `05`.
Use `06`, `07`, `08`, `09` as references while implementing.

## Scope of first release (MVP)

- Ingest 3-10 channels first, then scale to 100+.
- News feed with sentiment and coin filters.
- Position extraction and confidence scoring.
- Paper trading only, with a full audit log.
- Live trading is a later, explicitly enabled phase.
