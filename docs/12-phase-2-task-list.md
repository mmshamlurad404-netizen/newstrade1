# 12 - Phase 2 Implementation Task List

Bite-sized tasks for Phase 2 (analysis). Each task ends with something testable.
Respect gate G2 in `08-roadmap-costs-and-security.md` before moving to Phase 3.

## Task 0: Pipeline rewiring

- [x] Add `clustered_news` stream; cluster worker publishes there.
- [x] Analyzer consumes `clustered_news`; publishes `analyzed_news`.
- [x] Add `fast_alerts` and unified `dlq` streams.

## Task 1: Analysis schemas

- [x] Implement `backend/app/schemas/analysis.py`: `Analysis`, enums, and
      `AnalysisStatus`.
- [x] Validate ranges (sentiment -1..1, certainty 0..1) and uppercase coins.

## Task 2: Fast relevance filter and fast path

- [x] Implement `backend/app/services/analysis/filter.py`: `relevance_score`,
      `detect_fast_alert`.
- [x] Threshold is configurable (`ANALYSIS_RELEVANCE_MIN`).
- [x] Unit test high relevance for listings and low relevance for off-topic.

## Task 3: Coin resolution

- [x] Implement `backend/app/services/analysis/coins.py`: `extract_symbols`,
      `canonicalize`, `resolve_coins` against a symbol allowlist.
- [ ] Replace the static allowlist with live exchange `fetch_markets` at runtime.

## Task 4: Hardened prompt and versioning

- [x] Implement `backend/app/services/analysis/prompt.py`: system text,
      data/instruction separation, delimiter neutralization, `PROMPT_VERSION`.
- [x] Unit test that delimiters are stripped and the version is embedded.

## Task 5: LLM client

- [x] Implement `backend/app/services/analysis/llm.py`: JSON call, validation,
      one repair retry, `AnalysisError`.
- [ ] Add token/cost logging per call.
- [ ] Add provider fallback (secondary model on repeated failure).

## Task 6: Injection and anomaly validation

- [x] Implement `backend/app/services/analysis/validator.py`:
      `detect_injection`, `is_anomalous`, `apply_caps`.
- [x] Unit test detection, anomaly flagging, and caps.

## Task 7: Enrichment and market data

- [x] Implement `backend/app/services/analysis/market.py` (price, cap tier) and
      `enrich.py` (`build_enrichment`).
- [ ] Add liquidity/spread checks via CCXT order book.
- [ ] Add macro calendar window check.

## Task 8: Analysis worker

- [x] Implement `backend/app/services/analysis/worker.py` consuming
      `clustered_news`.
- [x] Idempotent: skip already-analyzed news.
- [x] Persist analysis, set `analysis_status`, publish `analyzed_news`.
- [x] Publish `fast_alerts` for high-precision templates.
- [ ] Add cost and latency metrics per stage.

## Task 9: Database changes

- [x] Add `news.analysis_status` and `news.discarded_reason`.
- [x] Add `prompt_versions`, `eval_labels`, `eval_runs` (migration 0002).

## Task 10: Evaluation set

- [ ] Label 500-1,000 real messages (coins, event_type, sentiment, tradable).
- [ ] Add at least 10 adversarial injection messages.
- [ ] Compute coin F1, event accuracy, tradable F1, injection pass per release.

## Gate G2 before Phase 3

- [ ] Coin extraction F1 and event accuracy above the agreed thresholds.
- [ ] Injection test passes (no compliance from adversarial inputs).
- [ ] Discarded noise rate is reasonable and reviewed.
- [ ] Failure paths land in the DLQ and do not stall the worker.
