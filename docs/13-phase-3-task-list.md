# 13 - Phase 3 Implementation Task List

Bite-sized tasks for Phase 3 (signals, confidence, risk, paper trading). Each
task ends with something testable. Respect gates G3-G5 in
`08-roadmap-costs-and-security.md` before enabling any live trading.

## Task 0: Pipeline wiring

- [x] Add `signals` and `orders` streams to `queue.py`.
- [x] Add `publish_signal` and `publish_order` helpers.
- [x] Signaler consumes `analyzed_news`; publishes `signals`.

## Task 1: Signal schema

- [x] Implement `backend/app/schemas/signal.py`: `Signal`, `Direction`,
      `SignalStatus`, `Mode`.

## Task 2: Confidence engine

- [x] Implement `backend/app/services/signals/confidence.py`:
      `compute_confidence`, `corroboration_score`, `conviction_strength`,
      `market_risk_factor`, `veto_reasons`.
- [x] Confidence = 100 x (0.30 source + 0.25 certainty + 0.25 corroboration +
      0.20 conviction); volatility never edits confidence.
- [x] Unit test corroboration monotonicity, bucket reachability, bounds, and
      market risk factor clamping.

## Task 3: Deterministic levels

- [x] Implement `backend/app/services/signals/levels.py`: `atr`, `build_levels`,
      `entry_zone`, `risk_reward`.
- [x] Unit test long/short ordering and risk-reward math.

## Task 4: Signal builder

- [x] Implement `backend/app/services/signals/engine.py`: `direction_for`,
      `deterministic_signal_id` (uuid5), `build_signal`.
- [x] Reject with a reason when direction is unclear, candles are insufficient,
      ATR is zero, or reward/risk < 1.5.

## Task 5: Risk manager

- [x] Implement `backend/app/services/trading/risk.py`: `RiskConfig`,
      `RiskState`, `RiskDecision`, `base_risk_pct`, `position_size`, `evaluate`.
- [x] Enforce kill switch, daily/weekly loss caps, max positions, max leverage,
      spread, depth, position-vs-volume, min confidence, min reward/risk,
      aggregate open risk, and correlation cap.
- [x] Unit test approval path and each veto reason.

## Task 6: Paper trading

- [x] Implement `backend/app/services/trading/paper.py`: `simulate_entry`,
      `check_exit`, `compute_pnl` with fees.

## Task 7: Exchange adapter

- [x] Implement `backend/app/services/trading/exchanges.py`: `build_exchange`,
      `fetch_candles`, `snapshot` via `ccxt.pro`.
- [ ] Add live `fetch_markets` allowlist (shared with Phase 2 coin resolution).
- [ ] Add retry/backoff on transient exchange errors.

## Task 8: Signal and trade worker

- [x] Implement `backend/app/services/signals/worker.py` consuming
      `analyzed_news`.
- [x] Idempotent `signals` upsert on deterministic `signal_id`.
- [x] Risk-evaluate; persist rejected signals with reasons.
- [x] On approval, persist active signal and open a `paper_trades` row.
- [x] Publish to `signals`, route failures to `dlq`.
- [ ] Add an executor that manages open paper trades (exit on SL/TP/expiry).
- [ ] Add daily/weekly PnL rollups into `RiskState`.

## Task 9: Database changes

- [x] Add `signals`, `orders`, `trades`, `paper_trades`, `candles`,
      `channel_stats` (migration 0003).

## Task 10: Deployment

- [x] Add the `signaler` service to `deploy/docker-compose.yml`.
- [x] Add `ccxt` dependency and `DEFAULT_EXCHANGE` / `PAPER_EQUITY` settings.

## Gate G3-G5 before live trading

- [ ] Backtest the confidence and level rules on historical news/candles.
- [ ] Run paper trading for 4-6 weeks; record hit rate, expectancy, max drawdown.
- [ ] Confirm the executor closes trades correctly on SL/TP/expiry.
- [ ] Confirm risk caps hold under concurrent signals and correlated assets.
- [ ] Only then enable `manual_live`, followed later by `auto_live`.
