# 04 - Phase 4: Trading Engine & Exchange Integration

### Architecture
`Signal DB -> Risk Manager -> Order Executor -> Exchange (via CCXT)`

**1. Connecting to Providers (Exchanges)**
Use CCXT Pro (supports 100+ exchanges).

python
import ccxt.pro as ccxt

exchange = ccxt.bybit({
'apiKey': 'YOUR_KEY',
'secret': 'YOUR_SECRET',
'enableRateLimit': True,
'options': {'defaultType': 'future'} # for perpetual futures
})

Fetch price

ticker = await exchange.fetch_ticker('BTC/USDT')

Create order with risk management

async def execute_signal(signal):
balance = await exchange.fetch_balance()
risk_pct = 0.01 if signal['confidence'] > 75 else 0.005
position_size = (balance['USDT']['free'] * risk_pct) / abs(signal['entry'] - signal['stop_loss'])

params = {'stopLoss': signal['stop_loss'], 'takeProfit': signal['take_profits'][0]}
order = await exchange.create_market_order(signal['asset'], 'buy' if signal['direction']=='LONG' else 'sell', position_size, params=params)


**2. Risk Manager (MUST HAVE)**
- Max daily loss: -3% -> stop trading for day
- Max open positions: 3
- Max leverage: 5x (even if signal says 20x)
- No trading during high-impact news if spread > 0.5%
- Always set SL/TP on exchange side, not just in app

**3. Modes:**
- **Paper Trading:** Default for 1 month. Log everything to `paper_trades` table.
- **Live Trading:** Requires user to enable manually + 2FA confirmation per trade or auto-trade toggle.

**4. Backtesting:**
Before live, backtest your confidence engine.
- Replay 6 months of scraped Telegram history
- Simulate trades at historical prices
- Metrics: Win Rate, Profit Factor, Max Drawdown

**Supported Exchanges:**
Start with 2: Binance & Bybit (largest liquidity for futures). Add OKX later.
