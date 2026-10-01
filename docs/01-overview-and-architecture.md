# 01 - Overview & System Architecture

## 1. Vision
A Windows + Android trading app that listens to 50-500+ Telegram channels (public + private), normalizes crypto news in real-time, analyzes it with AI, extracts tradable positions (Long/Short, Entry/SL/TP), scores confidence, and executes via exchange APIs.

## 2. End-to-End Data Flow


## 3. Tech Stack Decision

| Layer | Tech Recommendation | Why |
| :--- | :--- | :--- |
| **Ingestion** | Python + Telethon / Pyrogram (MTProto User Client) | Only MTProto User API can read private channels. Bot API WILL NOT WORK for private channels. |
| **Backend API** | Python FastAPI + WebSockets | Real-time news push to apps |
| **Database** | PostgreSQL + TimescaleDB + Redis + Qdrant/PGVector | Timescale for OHLCV, Redis for queue/cache, Vector DB for semantic search |
| **Queue** | Redis Streams / RabbitMQ / Kafka | Decoupling ingestion from analysis |
| **AI / NLP** | LLM API (Claude/GPT-4/Gemini) + FinBERT + spaCy | LLM for reasoning, FinBERT for fast sentiment |
| **Trading** | CCXT Pro | Unified API for Binance, Bybit, OKX, Bitget |
| **Windows App** | Electron + React + TypeScript OR Flutter Desktop | Single codebase for Windows + Android if using Flutter |
| **Android App** | Flutter | One codebase for Android + Windows |
| **Infra** | Docker, Docker Compose, VPS | Easy to deploy |

## 4. Core Concepts
1.  **Source Credibility Score:** Each Telegram channel gets a weight (0-1) based on historical accuracy.
2.  **Signal Confidence:** 0-100% based on source weight + corroboration + LLM certainty + market context.
3.  **Paper Trading First:** Never go live before 4-6 weeks of paper trading and backtesting.

## 5. Legal & Risk Warning
- You MUST use your own Telegram Account (user session) to read private channels you are a member of. Scraping channels you don\'t have access to violates Telegram ToS.
- This is not financial advice. Add disclaimers. Use strict risk management (max 1-2% per trade).