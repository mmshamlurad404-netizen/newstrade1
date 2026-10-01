# 03 - Phase 2 & 3: Analysis, Position Extraction & Confidence

### Phase 2: AI Analysis Pipeline (The Brain)

Every new message from Redis -> Analysis Worker.

**Step 1: Fast Filter (10ms)**
- Regex + FinBERT-Crypto model to filter noise. Is it crypto relevant? Score 0-1.
- If score < 0.3 -> discard (memes, off-topic)

**Step 2: LLM Deep Analysis (1-3 sec)**
Use a single structured LLM call with JSON output. This is cheaper and faster.

**PROMPT TEMPLATE:**
You are a crypto trading analyst. Analyze this Telegram news.

Message: "{cleaned_text}"
Channel: {channel_name} | Time: {timestamp}

Return ONLY valid JSON:
{
"is_tradable": boolean,
"coins": ["BTC", "ETH"],
"event_type": "listing | hack | partnership | regulation | unlock | whale_movement | macro | other",
"sentiment": "bullish | bearish | neutral",
"sentiment_score": -1.0 to 1.0,
"urgency": "low | medium | high | critical",
"summary": "1 sentence summary",
"impact_timeframe": "scalp (minutes) | intraday (hours) | swing (days)"
}

**Step 3: Context Enrichment**
- Check CoinGecko/CoinMarketCap API: Is coin low-cap? (high impact)
- Check if similar news in last 1 hour from other channels? -> Corroboration boost.

### Phase 3: Position Extractor & Confidence Engine

This converts analysis -> tradable signal.

**Position JSON Schema (Saved to `signals` table):**
json
{
"signal_id": "uuid",
"asset": "SOL/USDT",
"direction": "LONG | SHORT | NO_TRADE",
"entry_zone": [145.2, 146.0],
"stop_loss": 143.5,
"take_profits": [148.0, 150.5, 155.0],
"leverage_suggested": 3,
"timeframe": "15m | 1h | 4h",
"confidence": 78,
"rationale": "Binance listing news + high urgency...",
"expires_at": "2025-09-10T14:00:00Z",
"risk_reward": 2.8
}


**How to Generate Entry/SL/TP?**
You have 2 options:
1.  **LLM + Technicals (Recommended):** LLM suggests direction/bias, then your TA engine calculates levels. Fetch live price via CCXT, calculate ATR, support/resistance, set SL = entry +/- 1.5*ATR.
2.  **Pure LLM:** Ask LLM to suggest levels (less accurate).

**Confidence Score Formula (0-100):**
Confidence = ( W1SourceCredibility + W2LLM_Certainty + W3Corroboration + W4SentimentStrength ) * MarketVolatilityFactor

W1=0.30, W2=0.25, W3=0.25, W4=0.20
SourceCredibility: Avg score of channels reporting it (e.g., Whale Alert 0.9, Random signal group 0.3)

Corroboration: +20 points if 3+ independent channels report within 10 mins

SentimentStrength: abs(sentiment_score)

MarketVolatilityFactor: 0.8 if BTC volatility > 5% (news less reliable)


**Rules:**
- Confidence < 60 -> NO_TRADE, only show as news in app
- 60-75 -> Low size signal (0.5% risk)
- 75-85 -> Medium signal (1% risk)
- >85 -> High signal (2% risk max)

Update channel credibility weekly: if channel\'s high-confidence signals were profitable -> increase score.
