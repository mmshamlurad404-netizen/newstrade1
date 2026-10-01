# 08 - Roadmap, Costs and Security

## 1. Phase timeline

| Phase | Name | Duration | Key deliverable |
| :--- | :--- | :--- | :--- |
| 0 | Setup | Week 1 | Telegram account, credentials, channel list |
| 1 | Ingestion | Weeks 2-3 | Real-time listener, gap recovery, dedup, media |
| 2 | Analysis | Weeks 4-6 | Relevance filter, LLM analysis, read-only news app |
| 3 | Signals and risk | Weeks 7-10 | Position extraction, confidence, risk, paper trading |
| 4 | App and deploy | Weeks 11-13 | Flutter app Windows and Android, notifications, Docker |
| 5 | Backtest and tune | Weeks 14-18 | Backtest report, calibrated confidence, staging |
| 6 | Live launch | Week 19+ | Small-capital live trading and monitoring |

The deliberate change from the first draft: a **read-only news app ships in
Phase 2** so the feed is validated before any trading work. Trading is later.

## 2. Go/no-go gates

Do not advance if a gate fails. These exist to stop a plausible-looking pipeline
from losing money.

| Gate | Between | Criteria |
| :--- | :--- | :--- |
| G1 Feed works | Phase 1 to 2 | p95 latency under 5 s, zero missed messages after reconnect, DLQ handled |
| G2 Analysis works | Phase 2 to 3 | coin F1 and event accuracy above agreed thresholds on the labeled set; injection test passes |
| G3 Backtest passes | Phase 3 to 4 | profit factor above 1.3 and drawdown below 20% on held-out data |
| G4 Paper trading | Phase 3 to live | 4-6 weeks stable, calibration monotonic, no risk-limit breaches |
| G5 Live readiness | before live | kill switch tested, reconciliation works, keys restricted, backups verified |
| G6 Compliance | before live | jurisdiction allows the instrument; disclaimers in place; private content not redistributed |

## 3. Milestones and KPIs

| Milestone | KPI |
| :--- | :--- |
| M1 Ingestion live | 99% uptime, p95 latency under 5 s, reconnect gap zero |
| M2 Analysis live | cost under 2 cents per analyzed message |
| M3 News app shipped | used daily; feed quality reviewed weekly |
| M4 Paper trading | at least 200 signals; calibration curve monotonic |
| M5 App shipped | Android and Windows builds installed and used daily |
| M6 Backtest complete | metrics reported per event type and channel on held-out data |
| M7 Live launch | no risk-limit breaches, daily loss stop respected |

## 4. Team and effort

| Role | Focus |
| :--- | :--- |
| Backend engineer | Ingestion, analysis, signals, API |
| Data/ML engineer | Prompts, evaluation, confidence calibration, backtesting |
| Mobile engineer | Flutter app for Windows and Android |
| DevOps (part-time) | Docker, monitoring, backups, security |

A single experienced developer can reach the MVP in roughly 4-5 months, but
should expect most effort to go into data quality, evaluation, and risk controls
rather than the app.

## 5. Cost estimate

| Item | Monthly estimate | Notes |
| :--- | :--- | :--- |
| VPS (8 vCPU, 16 GB) | 40-80 USD | Production; smaller for staging |
| LLM API | 20-150 USD | Scales with volume and model choice |
| Managed Postgres (optional) | 20-50 USD | Only if not self-hosting |
| Data APIs (CoinGecko and similar) | 0-100 USD | Free tiers often suffice to start |
| Exchange fees | Variable | Typically 0.02%-0.06% per side |
| Telegram | Free | User API is free |

Cost levers: cheap model for classification, strong model only for ambiguous or
high-urgency items, cache by content hash, gate media by relevance.

## 6. Security

### 6.1 Secrets and key custody

- Never commit `.env`, session files, `api_hash`, or exchange keys.
- Exchange keys live only on the server, encrypted at rest.
- Disable withdrawal permission; restrict keys to a whitelist IP; enable trading
  permission only if live trading is active.
- The app never stores exchange keys; it only holds a short-lived session token.
- Use a secrets manager or encrypted Docker secrets in production.

### 6.2 Application security

- Strong auth plus 2FA for the operator account; re-auth for sensitive actions.
- Rate-limit auth and trade endpoints.
- Validate and sanitize inputs; parameterize queries; reject unknown fields.
- Treat all message text as untrusted input to the LLM (prompt injection), and
  never let the LLM invoke trading functions.
- Keep dependencies patched; scan containers for vulnerabilities.

### 6.3 Telegram session safety

- Back up the session file securely; treat it as a password.
- One client per account; avoid frequent re-logins or IP changes.
- Throttle joins; respect rate limits and terms of service.
- Monitor for flood waits and account restrictions.

### 6.4 Auditability

- Immutable audit log for every order, cancellation, prompt change, and config
  change, with actor and timestamp.
- Keep audit logs indefinitely.

## 7. Legal, privacy and compliance

- This software is not financial advice. Display a clear disclaimer in the app.
- Read only channels you are a member of and allowed to access.
- Do not redistribute private-channel content unless the channel explicitly
  allows it; copyright and channel rules apply.
- Respect exchange terms and local regulations. Derivatives access varies by
  jurisdiction and may be restricted for the operator; gate by region.
- Consider tax reporting obligations for trading activity.
- If you later serve other users, do a separate privacy and data-protection
  review; that is a different product.

## 8. Operations runbook

| Incident | Response |
| :--- | :--- |
| Ingestor disconnected | Alert; restart container; verify session; gap-recover by min_id |
| No messages from a channel | Stale detector alerts; check membership and account status |
| Queue backlog growing | Scale workers; check LLM latency and cost |
| Exchange API errors | Backoff then alert; pause live trading if persistent |
| Daily loss limit hit | Trading auto-stops; review; manual reset required |
| Suspected key compromise | Kill switch; rotate keys; revoke Telegram session |
| Database failure | Fail over or restore the latest backup; verify integrity |

## 9. User risk disclosure

Show on first launch and in settings:

- Trading crypto derivatives involves substantial risk of loss.
- Confidence scores are probabilistic, not guarantees.
- Past performance does not predict future results.
- The operator is responsible for every trade enabled.
