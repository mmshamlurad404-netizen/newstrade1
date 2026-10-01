# 02 - Phase 1: Telegram News Extraction

This is the most critical phase. How to feed news to your app.

### Phase 0: Setup (1 Week)
- [ ] Get `api_id` and `api_hash` from https://my.telegram.org -> API Development Tools
- [ ] Create a dedicated Telegram account for scraping (don\'t use personal main)
- [ ] Whitelist IP, enable 2FA

### Phase 1: Ingestion Engine - Implementation

**DO NOT USE BOT API.** Bot can only read private channels if it\'s an admin/member and limited. Use MTProto User Client.

**Stack: Python + Telethon**

**Key Features to Implement:**
1.  **Real-time Listener:** `events.NewMessage` instead of polling every N seconds.
2.  **History Scraper:** On first run, scrape last 2000 messages per channel for backtesting.
    `await client.get_messages(channel, limit=2000)`
3.  **Media Handling:** Download images/PDFs, run OCR (Tesseract) + Vision LLM (GPT-4o) to extract text from images.
4.  **Deduplication:** Many channels forward same news. Hash text `hash(normalized_text)` and drop duplicates within 30 min window.
5.  **Normalization:** Clean emojis, links, language detection, translate to English if needed (using LLM).
6.  **Rate Limiting & Session:** Telethon handles FloodWait automatically. Never run >1 client per account.


**Alternative if you can\'t code MTProto:** Use `Telegram RSS` tools but not recommended for private channels.

**Database Schema (PostgreSQL)**