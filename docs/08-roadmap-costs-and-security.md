# 08 - Roadmap, Costs and Security

## 1. Phase timeline

| Phase | Name | Duration | Key deliverable | Exit criteria |
| :--- | :--- | :--- | :--- | :--- |
| 0 | Setup | Week 1 | Telegram account, API credentials, channel list | Ingestor can log in and read a test channel |
| 1 | Ingestion | Weeks 2-3 | Real-time listener, history backfill, dedup, media | Post-to-DB latency under 5 s |
| 2 | Analysis | Weeks 4-6 | Relevance filter, LLM analysis, enrichment | Structured JSON stored for all relevant news |
| 3 | Signals and trading | Weeks 7-10 | Position extractor, confidence, risk, paper trading | Complete paper trading with audit logs |
| 4 | App and deploy | Weeks 11-14 | Flutter app on Windows and Android, Docker deploy | Real-time signal in app under 5 s |
| 5 | Backtest and tune | Weeks 15-18 | Backtest report, tuned weights, staging at scale | Profit factor above 1.3, drawdown below 20% |
| 6 | Live launch | Week 19+ | Small-capital live trading and monitoring | Stable results over 4 weeks |

## 2. Milestones and KPIs

| Milestone | KPI |
| :--- | :--- |
| M1 Ingestion live | 99% uptime, latency p95 under 5 s |
| M2 Analysis live | Analysis cost under 2 cents per message |
| M3 Paper trading | At least 200 signals evaluated |
| M4 App shipped | Android and Windows builds installed and used daily |
| M5 Backtest complete | Documented metrics by event type and channel |
| M6 Live launch | No risk-limit breaches, daily loss stop respected |

## 3. Team and effort

A realistic small-team split:

| Role | Focus |
| :--- | :--- |
| Backend engineer | Ingestion, analysis, signals, API |
| Data or ML engineer | Prompts, confidence tuning, backtesting |
| Mobile engineer | Flutter app for Windows and Android |
| DevOps (part-time) | Docker, monitoring, backups, security |

A single experienced developer can build the MVP in roughly 4-5 months, but
should expect to spend significant time on data quality and risk controls.

## 4. Cost estimate

| Item | Monthly estimate | Notes |
| :--- | :--- | :--- |
| VPS (8 vCPU, 16 GB) | 40-80 USD | Production; smaller for staging |
| LLM API | 20-150 USD | Depends on message volume and model choice |
| Managed Postgres (optional) | 20-50 USD | Only if not self-hosting |
| FCM | Free | Standard tier |
| Exchange fees | Variable | Maker/taker, typically 0.02%-0.06% |
| Data APIs (CoinGecko and similar) | 0-100 USD | Free tiers often suffice to start |
| Telegram | Free | User API is free |

Cost control levers: cheap model for classification, strong model only for
ambiguous or high-urgency items; cache by content hash; batch calls.

## 5. Security

### 5.1 Secrets

- Never commit `.env`, session files, `api_hash`, or exchange keys.
- Use a secrets manager or encrypted Docker secrets in production.
- Exchange API keys: enable trading only if needed, never enable withdrawals,
  and restrict to a whitelisted IP.

### 5.2 Application security

- Hash and salt user passwords; prefer OAuth or one-time codes.
- Rate limit authentication and trade endpoints.
- Encrypt sensitive settings at rest.
- Validate and sanitize all inputs; parameterize database queries.
- Keep dependencies updated and scan for known vulnerabilities.
- Run services with least privilege in containers.

### 5.3 Telegram session safety

- Back up the session file securely; treat it like a password.
- One session per account; avoid frequent re-logins or IP changes.
- Respect Telegram rate limits and terms of service.

### 5.4 Auditability

- Immutable audit log for every order, cancellation, and config change.
- Record the responsible user or system component for each action.
- Retention: keep audit logs indefinitely.

## 6. Legal and compliance

- This software is not financial advice. Display a clear disclaimer in the app.
- Only read Telegram channels you are a member of and allowed to access.
- Respect each exchange's terms of service and local regulations, including
  derivatives rules that vary by jurisdiction.
- Consider tax reporting requirements for trading activity.
- If you later serve other users, review data-protection obligations for the
  personal data you store.

## 7. Operations runbook

| Incident | Response |
| :--- | :--- |
| Ingestor disconnected | Alert fires; restart container; verify session and reconnect |
| Queue backlog growing | Scale analyzer workers; check LLM latency and cost |
| Exchange API errors | Retry with backoff; if persistent, pause live trading |
| Daily loss limit hit | Trading auto-stops; review signals; manual reset required |
| Suspected key compromise | Rotate API keys, revoke session, enable kill switch |
| Database failure | Fail over or restore from the latest backup; verify integrity |

## 8. Risk disclosure for users

Show once on first launch and in settings:

- Trading crypto derivatives involves substantial risk of loss.
- Confidence scores are probabilistic, not guarantees.
- Past performance does not predict future results.
- The user is responsible for every trade they enable.
