# 07 - Confidence Engine, Risk and Backtesting

## 1. The core fix: two separate numbers

The first draft multiplied the confidence score by a volatility factor. That is
wrong: it caps the maximum confidence, so in volatile markets the 85+ bucket
becomes unreachable exactly when it matters. Keep two independent quantities:

1. **Confidence (0-100)**: how good the signal is, based on source credibility,
   model certainty, corroboration, and conviction strength. This drives
   thresholds and display.
2. **Market risk factor (0.0-1.0, default 1.0)**: how dangerous the current
   market is. This scales position size and can veto, but never rewrites the
   confidence score.

```text
confidence = 100 * (
    0.30 * source_credibility
  + 0.25 * llm_certainty
  + 0.25 * corroboration_score
  + 0.20 * conviction_strength
)
```

`confidence` is clamped to 0-100. Each term is normalized to 0.0-1.0.

## 2. Confidence terms

### 2.1 Source credibility

Average credibility of the independent origin channels, weighted by earliness.

```text
source_credibility = sum(weight_i * credibility_i) / sum(weight_i)
weight_i = 1.0 for the first report, decaying toward 0.5 for later reports
```

Start every channel at 0.5. Only originators count; forwarders are not credited.

### 2.2 LLM certainty

The `certainty` field from the analysis, clamped to 0.0-1.0. Downweight if the
anomaly detector flagged the output.

### 2.3 Corroboration

```text
corroboration_score = min(1.0, independent_origin_count / 4)
```

Count independent origin channels only.

### 2.4 Conviction strength

The strength of the directional call, combining sentiment magnitude and event
severity:

```text
conviction_strength = clamp(0.6 * abs(sentiment_score) + 0.4 * event_severity, 0, 1)
```

`event_severity` is a fixed lookup by event type (for example hack 0.9, listing
0.8, macro 0.7, partnership 0.5, other 0.3). Keep it in config so it is tunable
and auditable.

## 3. Weights are hypotheses, not truth

The 0.30/0.25/0.25/0.20 weights are starting guesses. Calibrate them from data:

- Fit weights so that confidence buckets match realized win rates.
- Re-fit only on training data and validate on a held-out period.
- Keep the weights in config and version them alongside prompts.

## 4. Market risk factor

```text
market_risk_factor = clamp(1.0
    - volatility_penalty
    - liquidity_penalty
    - macro_penalty
    - spread_penalty, 0.3, 1.0)
```

Suggested inputs:

| Input | Effect |
| :--- | :--- |
| BTC ATR% high | volatility penalty |
| Target asset ATR% high | volatility penalty |
| Thin order book depth | liquidity penalty |
| Imminent macro event (CPI/FOMC) | macro penalty |
| Wide spread | spread penalty, can force veto |

Hard vetoes (regardless of factor):

- Spread above the configured maximum.
- Depth below the intended position size.
- Funding extreme for the intended hold.
- Kill switch on, or daily loss limit hit.

Effective risk per trade:

```text
risk_pct = base_risk(confidence) * market_risk_factor
```

Base risk by confidence: below 60 = 0, 60-74 = 0.5%, 75-84 = 1.0%, 85+ = 2.0%.

## 5. Confidence calibration (the whole point)

A confidence score is only useful if it is calibrated: signals labeled 80%
should win about 80% of the time (or, for trading, show a stable positive
expectancy).

Measure and report:

- Reliability curve: realized win rate per confidence decile.
- Expectancy and average PnL per confidence bucket.
- Brier score or log loss on the directional prediction.
- Sample size per bucket with confidence intervals.

If bucket 85+ does not out-perform bucket 65-74, the weights are wrong or the
score is noise. Calibration, not raw accuracy, is the acceptance criterion for
the confidence engine.

## 6. Weekly credibility update

Over the last 7 days, for originator signals only:

```text
raw_accuracy = winning_signals / max(1, total_signals)
new_credibility = clamp(0.8 * old + 0.2 * raw_accuracy, 0.1, 0.95)
```

Guardrails:

- Require at least 5 signals before adjusting; otherwise keep the score.
- Move slowly (0.2 learning rate) to avoid chasing luck.
- Decay toward 0.5 after 30 days of silence.
- Cap any single channel below 0.95 to avoid over-trusting one source.

## 7. Risk engine limits

| Limit | Value |
| :--- | :--- |
| Risk per trade | 0.5-2.0% by confidence, scaled by market risk factor |
| Max concurrent positions | 3 |
| Max aggregate open risk | 5% of equity |
| Max net correlated (BTC-beta) exposure | 1.5x single-trade risk budget |
| Max leverage | 5x |
| Daily loss stop | -3% of equity, auto stop for the day |
| Weekly loss stop | -8%, manual reset |
| Cooldown per asset | 15 minutes |
| Max spread to enter | 0.5% |
| Max slippage | 0.3% or 0.5 ATR, whichever is smaller |
| Max position vs volume | below 1% of recent average volume |
| Min liquidation distance | liquidation at least 2x stop distance |

### 7.1 Correlation risk

Crypto positions are highly correlated; three longs can be one leveraged bet.

- Compute rolling correlation to BTC per asset.
- Beta-adjust and sum open directional exposure.
- If the correlated cap binds, reduce size or reject.

### 7.2 Kill switch

One flag at the top of the execution path: reject new entries, optionally cancel
orders, optionally flatten. Triggered by the API, config, or a loss limit.

### 7.3 Failure modes

- Exchange outage: retry with backoff, then alert; do not flood.
- Partial fill: reconcile and repair protective orders.
- Stop gap-through: record slippage; count toward loss limits.
- Funding spike: include in expected cost; avoid unintended holds.

## 8. Backtesting methodology

### 8.1 Data

- 3-6 months of scraped Telegram history per channel.
- Candles matching each signal's timeframe.
- Fee schedule and a slippage model per venue.

### 8.2 Simulation rules

1. Signal becomes tradable at the message timestamp (use posted time, not scrape
   time; if only scrape time is known, add a conservatism buffer).
2. Entry per the signal's `order_type`: limit at the entry zone with timeout, or
   IOC market with modeled slippage.
3. Fees per side; funding for perp holds.
4. Stop and partial TPs evaluated on candle high/low. When a candle touches both
   stop and TP, assume the stop fills first (conservative).
5. Apply the same risk, correlation, and loss-limit rules as live.
6. Enforce expiry.

```python
def simulate(signal, candles, fee_bps=5, slip_bps=8):
    # returns a trade result with pnl, close_reason, and holding time
    ...
```

### 8.3 Metrics and gates

| Metric | Gate before live |
| :--- | :--- |
| Win rate | above 50% |
| Profit factor | above 1.3 on held-out data |
| Max drawdown | below 20% |
| Expectancy per trade | positive after fees and funding |
| Calibration | monotonic reliability curve |

### 8.4 Segmentation

Report metrics by event type, confidence bucket, timeframe, channel, and market
regime. Retire event types or channels that consistently lose. This is the main
feedback loop.

### 8.5 Statistical discipline

- Walk-forward validation; hold out a final period.
- Report how many parameter combinations were tried (multiple-testing risk).
- Require a minimum sample size per segment; do not act on tiny samples.
- Beware survivorship and selection bias: your channel list is curated today.

## 9. Paper trading

Run paper trading for at least 4-6 weeks after backtesting:

- Same pipeline and risk rules; no real orders.
- Log every candidate signal, including rejections.
- Compare paper results with the backtest. Large gaps mean the backtest is
  optimistic (latency, slippage, or survivorship).

Only after paper results are stable and calibrated should live trading begin,
with small capital and the kill switch armed.
