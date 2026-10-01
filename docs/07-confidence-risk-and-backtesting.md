# 07 - Confidence Engine, Risk and Backtesting

## 1. Confidence formula

```text
confidence = 100 * (
    0.30 * source_credibility
  + 0.25 * llm_certainty
  + 0.25 * corroboration_score
  + 0.20 * sentiment_strength
) * market_volatility_factor
```

Each term is normalized to 0.0-1.0 before weighting.

### 1.1 Source credibility

Average credibility of the channels that reported the news, weighted by how
early each channel posted it.

```text
source_credibility = sum(weight_i * credibility_i) / sum(weight_i)
weight_i = 1.0 for the first report, decaying to 0.5 for later reports
```

Start every channel at 0.5. Update weekly from `channel_stats`.

### 1.2 LLM certainty

The `certainty` field returned by the analysis model, clamped to 0.0-1.0.

### 1.3 Corroboration score

```text
corroboration_score = min(1.0, independent_source_count / 4)
```

Count independent channels only (ignore forwards of the same original channel).

### 1.4 Sentiment strength

```text
sentiment_strength = abs(sentiment_score)
```

### 1.5 Market volatility factor

```text
market_volatility_factor = 0.8 if btc_atr_pct > 5 else 1.0
```

Optionally make it continuous:

```text
factor = clamp(1.0 - (btc_atr_pct - 2.0) / 12.0, 0.7, 1.0)
```

## 2. Thresholds and actions

| Confidence | Action | Risk per trade |
| :--- | :--- | :--- |
| below 60 | NO_TRADE, news only | 0% |
| 60-74 | low size | 0.5% |
| 75-84 | medium size | 1.0% |
| 85 and above | high size | 2.0% max |

These are starting values. Tune them with backtest and paper-trading results.

## 3. Weekly credibility update

For each channel, over the last 7 days:

```text
raw_accuracy = winning_signals / max(1, total_signals)
new_credibility = clamp(0.8 * old + 0.2 * raw_accuracy, 0.1, 0.95)
```

Use only signals where that channel was the first reporter, so a channel that
merely forwards others does not get credit.

Guardrails:

- Require at least 5 signals before adjusting; otherwise keep the current score.
- Move slowly (the 0.2 learning rate) to avoid chasing luck.
- Decay credibility toward 0.5 if a channel has been silent for 30 days.

## 4. Risk engine

### 4.1 Limits

| Limit | Value |
| :--- | :--- |
| Risk per trade | 0.5% to 2.0% by confidence |
| Max concurrent positions | 3 |
| Max aggregate open risk | 5% of equity |
| Max leverage | 5x |
| Daily loss stop | -3% of equity |
| Weekly loss stop | -8% of equity, manual reset |
| Cooldown per asset | 15 minutes |
| Max spread to enter | 0.5% |
| Max single position notional | 25% of equity |

### 4.2 Kill switch

A single flag checked at the top of the execution path. Setting it to true:

1. Rejects all new entries.
2. Optionally cancels open orders.
3. Optionally flattens positions in a controlled way.

It can be triggered through the API, a config flag, or automatically when a loss
limit is hit.

### 4.3 Failure modes to handle

- Exchange API outage: retry with backoff, then alert; never flood with retries.
- Partial fills: reconcile with `fetch_positions` and adjust the protective
  orders.
- Price gaps through the stop: record slippage and count toward the loss limits.
- Clock skew: use exchange time for all order timestamps.

## 5. Backtesting methodology

### 5.1 Data

- 3-6 months of scraped Telegram history per channel.
- Candles at the timeframe matching each signal.

### 5.2 Simulation rules

1. Signal becomes tradable at the timestamp the message was posted.
2. Entry at the next candle open plus a slippage assumption (for example 5-10
   basis points).
3. Fees per side from the exchange fee schedule.
4. Stop loss and take profit evaluated on candle high/low, conservatively
   assuming the stop is hit first when a candle touches both.
5. Apply the same risk sizing and limits as live.
6. Enforce signal expiry.

```python
def simulate(signal, candles, fee_bps=5, slip_bps=8):
    # returns a trade result dict with pnl and close reason
    ...
```

### 5.3 Metrics

| Metric | Target before live |
| :--- | :--- |
| Win rate | above 50% |
| Profit factor | above 1.3 |
| Max drawdown | below 20% |
| Expectancy per trade | positive after fees |
| Average holding time | consistent with the timeframe |

### 5.4 Segmentation

Report metrics by:

- event type
- confidence bucket
- impact timeframe
- channel
- market regime (trending vs ranging)

Drop event types or channels that consistently lose. This is the main feedback
loop for the confidence weights.

### 5.5 Avoid look-ahead and overfitting

- Never use future candles when computing levels.
- Do not tune many parameters on the same data you evaluate on; hold out a
  period for validation.
- Report the number of parameter combinations tried so results can be judged.

## 6. Paper trading

Run paper trading for at least 4-6 weeks after backtesting:

- Same pipeline, same risk rules, no real orders.
- Log every candidate signal, including rejected ones.
- Compare paper results with the backtest; large gaps mean the backtest is
  optimistic (slippage, latency, or survivorship).

Only after paper results are stable should live trading be enabled, starting
with small capital.
