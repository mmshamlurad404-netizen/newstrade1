"""Register a set of default crypto news website feeds.

Usage (from the backend directory):
    python scripts/seed_feeds.py

Idempotent: feeds already present (matched by URL) are left untouched.
"""

import asyncio
import os
import sys
from decimal import Decimal

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_factory  # noqa: E402
from app.models.ingestion import Channel  # noqa: E402
from app.services.ingestion.feeds import synthetic_telegram_id  # noqa: E402

DEFAULT_FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", 0.750),
    ("Cointelegraph", "https://cointelegraph.com/rss", 0.680),
    ("Decrypt", "https://decrypt.co/feed", 0.700),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/feed", 0.650),
]


async def main() -> None:
    async with async_session_factory() as session:
        added = 0
        for title, url, credibility in DEFAULT_FEEDS:
            existing = await session.scalar(
                select(Channel).where(Channel.feed_url == url)
            )
            if existing is not None:
                continue
            session.add(
                Channel(
                    telegram_id=synthetic_telegram_id(url),
                    title=title,
                    kind="feed",
                    feed_url=url,
                    credibility=Decimal(str(credibility)),
                    poll_interval_seconds=300,
                    is_active=True,
                )
            )
            added += 1
        await session.commit()
        print(f"seeded {added} new feed(s); {len(DEFAULT_FEEDS) - added} already present")


if __name__ == "__main__":
    asyncio.run(main())
