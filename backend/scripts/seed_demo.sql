-- Demo data for local UI preview. Safe to run repeatedly.
-- Usage: psql "$DATABASE_URL_PSQL" -f scripts/seed_demo.sql

INSERT INTO channels (telegram_id, username, title, is_private, credibility, is_active)
VALUES
    (1001, 'example_news', 'Example News', false, 0.720, true),
    (1002, NULL, 'Private Alpha', true, 0.550, true)
ON CONFLICT (telegram_id) DO NOTHING;

INSERT INTO news (
    canonical_hash, headline, body_text, coins, event_type, sentiment,
    sentiment_score, urgency, certainty, impact_timeframe, market_scope,
    analysis_status, asset_resolved, source_count, origin_channel_id,
    first_seen_at, last_seen_at, prompt_version
)
VALUES
    ('demo-1', 'Binance will list SOL on spot', 'Exchange announcement.',
     ARRAY['SOL'], 'listing', 'bullish', 0.820, 'high', 0.780, 'intraday',
     'asset', 'analyzed', true, 4,
     (SELECT id FROM channels WHERE telegram_id = 1001),
     now() - interval '20 minutes', now() - interval '18 minutes', 'analysis-v1'),
    ('demo-2', 'Major exchange exploited, withdrawals frozen', 'Security incident.',
     ARRAY['ETH'], 'hack', 'bearish', -0.900, 'high', 0.600, 'intraday',
     'asset', 'analyzed', true, 2,
     (SELECT id FROM channels WHERE telegram_id = 1002),
     now() - interval '2 hours', now() - interval '2 hours', 'analysis-v1'),
    ('demo-3', 'Partnership announced with payments giant', 'Adoption news.',
     ARRAY['XRP'], 'partnership', 'bullish', 0.600, 'medium', 0.500, 'swing',
     'asset', 'analyzed', true, 1,
     (SELECT id FROM channels WHERE telegram_id = 1001),
     now() - interval '5 hours', now() - interval '5 hours', 'analysis-v1')
ON CONFLICT (canonical_hash) DO NOTHING;

INSERT INTO signals (
    id, news_id, asset, direction, entry_low, entry_high, stop_loss,
    take_profits, leverage_suggested, timeframe, confidence,
    market_risk_factor, risk_pct, rationale, risk_reward, status,
    prompt_version, expires_at
)
VALUES
    ('demo-signal-1', (SELECT id FROM news WHERE canonical_hash = 'demo-1'),
     'SOL/USDT', 'LONG', 145.2, 146.0, 143.5, ARRAY[148.0, 150.5, 155.0],
     3, '15m', 78, 0.800, 0.0100, 'listing bullish', 2.80, 'active',
     'analysis-v1', now() + interval '3 hours'),
    ('demo-signal-2', (SELECT id FROM news WHERE canonical_hash = 'demo-2'),
     'ETH/USDT', 'SHORT', 3200, 3210, 3260, ARRAY[3120.0, 3050.0, 2950.0],
     2, '15m', 69, 0.700, 0.0050, 'hack bearish', 1.90, 'active',
     'analysis-v1', now() + interval '2 hours')
ON CONFLICT (id) DO NOTHING;

INSERT INTO paper_trades (
    signal_id, asset, direction, entry_price, exit_price, quantity,
    pnl, pnl_pct, fees, opened_at, closed_at, close_reason
)
VALUES
    ('demo-signal-1', 'SOL/USDT', 'LONG', 145.2, NULL, 50,
     NULL, NULL, 3.63, now() - interval '15 minutes', NULL, NULL),
    ('demo-signal-2', 'ETH/USDT', 'SHORT', 3200, 3120, 0.5,
     40.0, 2.5, 0.80, now() - interval '5 hours', now() - interval '1 hour',
     'take_profit')
ON CONFLICT DO NOTHING;
