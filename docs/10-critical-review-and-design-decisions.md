# 10 - Critical Review and Design Decisions

This document records the problems found when reviewing the first draft of the
plan and the decisions made to fix them. It is the reasoning behind the other
documents. Treat it as a decision log (ADR-style).

## 1. Problems found in the first draft

| # | Problem | Why it matters | Fixed in |
| :--- | :--- | :--- | :--- |
| 1 | Confidence was multiplied by a volatility factor | Capped max confidence at 80, so the 85+ bucket was unreachable in volatile markets | `04`, `07` |
| 2 | Telegram text was trusted | Prompt injection could fabricate signals | `03` |
| 3 | No honesty about latency | A 1-3 s LLM path cannot win fast listing moves | `01`, `03` |
| 4 | Exchange keys were stored in the app | Client compromise would expose funds | `05` |
| 5 | FCM assumed to work on Windows | Official Flutter FCM does not support Windows desktop | `05` |
| 6 | No analysis evaluation | Cannot tune or detect extraction regressions | `03`, `06` |
| 7 | No confidence calibration | The score could be meaningless but still trade | `07` |
| 8 | Correlation risk ignored | Three crypto longs are one leveraged bet | `04`, `07` |
| 9 | Reconnect gaps in `NewMessage` | Messages posted while offline were lost | `02` |
| 10 | At-least-once delivery not acknowledged | Duplicate news, signals, and orders | `02`, `06` |
| 11 | Entry zone vs market order mismatch | Unclear how entries actually fill | `04` |
| 12 | Multiple take profits never managed | Schema listed TPs the executor ignored | `04` |
| 13 | Single vs multi-user scope unclear | Drove unnecessary auth/multi-tenant work | `01` |
| 14 | Compliance and private-content redistribution not addressed | Legal and platform risk | `01`, `08` |

## 2. Key decisions

### ADR-001: Single-operator, self-hosted v1

Decision: build for one operator first. No multi-tenancy, no billing, no
per-user isolation.

Rationale: multi-tenancy multiplies auth, cost allocation, legal, and support
work without improving the core bet. Revisit only after the tool is proven.

### ADR-002: The LLM advises, deterministic code decides

Decision: the model only produces classification, sentiment, and a certainty
estimate. Levels, size, leverage, and orders are computed by deterministic code
and must pass the risk gate.

Rationale: removes prompt injection and hallucination from the execution path.
The model cannot place a trade, so a manipulated message cannot directly move
funds beyond the normal risk-limited signal.

### ADR-003: Two separate scores

Decision: `confidence` (signal quality) and `market_risk_factor` (environment)
are separate. Volatility scales size and can veto, but never edits confidence.

Rationale: preserves the meaning of confidence and keeps the high-confidence
bucket usable in all conditions. See `07`.

### ADR-004: Tiered, latency-honest pipeline

Decision: a fast path handles high-precision, speed-sensitive templates; the full
LLM path handles everything else. The UI labels fast alerts "unverified".

Rationale: avoids pretending we can win a race we usually cannot, while still
capturing the cases where we can.

### ADR-005: Treat message text as untrusted

Decision: delimiter-based data/instruction separation, schema validation, an
anomaly detector, and no tool access for the analysis call.

Rationale: channels are a hostile input surface; defense in depth is required.

### ADR-006: Server-side key custody only

Decision: exchange keys never leave the backend. The client holds only a
short-lived session token.

Rationale: a stolen phone or app must not expose trading funds.

### ADR-007: Clustering-based dedup and corroboration

Decision: near-duplicate clustering with origin attribution. Forwarders do not
increase independent corroboration or credibility.

Rationale: otherwise a single piece of news forwarded widely looks like strong
consensus and inflates confidence.

### ADR-008: Evaluation-first

Decision: build a labeled dataset and measure extraction quality and calibration
per release before tuning weights.

Rationale: without measurement, confidence weights and prompts cannot be
improved or protected against regressions.

### ADR-009: Paper and gates before live

Decision: explicit go/no-go gates between phases, including a 4-6 week paper
period and a passing backtest on held-out data.

Rationale: the cheapest way to avoid losing money on a plausible-looking system.

### ADR-010: Private content is not redistributed by default

Decision: `redistribute_content` defaults to false per channel.

Rationale: respects channel rules and copyright, and reduces legal exposure.

## 3. Trade-offs accepted

- **Flutter for desktop** sacrifices some native integration (notifications,
  secure storage) for one codebase. Accepted for v1; the Windows notification
  gap is handled with a WebSocket-driven toast.
- **LLM cost vs accuracy**: a cheap model may miss nuance. Accepted, mitigated by
  the fast filter, a stronger model only for ambiguous/high-urgency items, and
  caching.
- **Single Postgres with Timescale and pgvector** trades peak specialization for
  operational simplicity. Accepted at the expected scale.
- **Latency**: we accept being slow on the fastest events and target slower news.
  Accepted because it is the honest position.

## 4. Open questions

1. **Jurisdiction and instrument**: are perpetual futures legal and available to
   the operator? This gates the entire live-trading phase.
2. **Channel terms**: do the private channels permit automated reading and any
   display? Per-channel decision required.
3. **Model choice**: which LLM gives the best accuracy-per-dollar on the labeled
   set? Decide empirically, not by reputation.
4. **Exchange choice**: which venues offer the needed symbols and compliant
   access for the operator?
5. **Secondary account strategy**: at what channel count does one Telegram
   account hit limits, and is a second dedicated account justified?
6. **Edge decay**: does the measured edge survive fees, funding, and latency in
   paper trading? If not, the product should pivot to alerts-only.

## 5. What "done" means

The tool is done enough to trade live only when: the feed is reliable, extraction
is measured, confidence is calibrated, the backtest passes on held-out data,
paper trading is stable, the risk gate and kill switch are tested, and the legal
gate is cleared. Anything less is a research tool, and should be labeled as such.
