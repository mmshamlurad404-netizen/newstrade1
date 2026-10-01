# 05 - Phase 5 & 6: App (Windows + Android) & Deployment

### Phase 5: App Development

**Backend API (FastAPI) - The bridge between DB and Apps**

python
Endpoints

GET /api/news?coin=BTC&limit=50 # Feed for app
GET /api/signals?confidence_min=70 # Tradable signals
GET /api/signal/{id} # Signal detail
POST /api/trade/execute # Execute manual trade
WS /ws/news # WebSocket for real-time push


**Frontend - Recommended: Flutter (One codebase for Windows + Android)**
- Alternative: React + Electron for Windows + React Native for Android (more work)

**App Screens:**
1.  **News Feed:** Real-time list, filter by coin, urgency, channel. Like Twitter feed.
2.  **Signal Card:** Asset, Direction badge (LONG green/SHORT red), Confidence bar, Entry/SL/TP, Rationale, "Execute" button.
3.  **Portfolio:** Open positions, PnL, History (from exchange via CCXT fetch_positions)
4.  **Settings:** API keys (encrypted locally), Risk settings, Channel selector

**Push Notifications:** Use Firebase Cloud Messaging (FCM) for Android + Windows. Backend triggers FCM when confidence > 75.

### Phase 6: Deployment & Roadmap

**Infrastructure (Docker Compose on VPS - e.g., Hetzner/Contabo 8GB RAM)**

yaml
services:
postgres: ...
redis: ...
ingestor: # telethon listener (always on)
analyzer: # python worker
api: # FastAPI
frontend: # Flutter web build



**Development Roadmap (4-5 Months):**

| Phase | Duration | Deliverable |
| :--- | :--- | :--- |
| **MVP - Phase 0-1** | Weeks 1-3 | Telegram ingestor running, saving to DB, simple API |
| **MVP - Phase 2** | Weeks 4-6 | AI analysis working, news app shows news + sentiment |
| **Beta - Phase 3** | Weeks 7-10 | Position extraction + confidence + paper trading |
| **Beta - Phase 4** | Weeks 11-14 | Flutter App (Windows/Android) + Backtesting results |
| **Launch** | Week 15+ | Live trading with small capital, monitoring |

**Next Steps for You:**
1. `git init` and create `docs/` folder with these files.
2. Create Telegram API credentials and test `listener.py` with 2-3 public channels.
3. Set up FastAPI + Postgres and confirm real-time flow before adding AI.

**Cost Estimate:**
- VPS: $15/mo
- LLM API: $20-100/mo (depends on volume, use GPT-4o-mini or Claude Haiku to save)
- No cost for Telegram/ CCXT