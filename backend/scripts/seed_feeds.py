"""Register the default crypto news and signal web feeds.

Usage (from the backend directory):
    python scripts/seed_feeds.py
    python scripts/seed_feeds.py --prune

The catalog lives in ``app.services.ingestion.feed_catalog`` and contains a
curated set of crypto media, on-chain/analytics research, exchange/company
blogs, mainstream finance desks, and news aggregators.

Idempotent: feeds already present (matched by URL) are updated in place. Feeds
not in the catalog are left untouched unless ``--prune`` is passed, in which
case feed channels whose URL is no longer in the catalog are deactivated (not
deleted) so they stop being polled.
"""

import argparse
import asyncio
import os
import sys
from decimal import Decimal

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_factory  # noqa: E402
from app.models.ingestion import Channel  # noqa: E402
from app.services.ingestion.feed_catalog import (  # noqa: E402
    DEFAULT_FEEDS,
    POLL_INTERVAL_SECONDS,
)
from app.services.ingestion.feeds import synthetic_telegram_id  # noqa: E402


async def main(prune: bool = False) -> None:
    catalog_urls = {url for _, url, _ in DEFAULT_FEEDS}
    async with async_session_factory() as session:
        added = 0
        updated = 0
        for title, url, credibility in DEFAULT_FEEDS:
            feed_url = url
            existing = await session.scalar(
                select(Channel).where(Channel.feed_url == feed_url)
            )
            if existing is None:
                session.add(
                    Channel(
                        telegram_id=synthetic_telegram_id(url),
                        title=title,
                        kind="feed",
                        feed_url=url,
                        credibility=Decimal(str(credibility)),
                        poll_interval_seconds=POLL_INTERVAL_SECONDS,
                        is_active=True,
                    )
                )
                added += 1
                continue
            changed = False
            if existing.title != title:
                existing.title = title
                changed = True
            if existing.credibility != Decimal(str(credibility)):
                existing.credibility = Decimal(str(credibility))
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if existing.poll_interval_seconds != POLL_INTERVAL_SECONDS:
                existing.poll_interval_seconds = POLL_INTERVAL_SECONDS
                changed = True
            if changed:
                updated += 1

        pruned = 0
        if prune:
            stale = await session.scalars(
                select(Channel).where(
                    Channel.kind == "feed",
                    Channel.is_active.is_(True),
                )
            )
            for channel in stale:
                if channel.feed_url not in catalog_urls:
                    channel.is_active = False
                    pruned += 1

        await session.commit()
        print(
            f"seeded {added} new, updated {updated}, "
            f"catalog size {len(DEFAULT_FEEDS)}"
            + (f", pruned {pruned} stale feed(s)" if prune else "")
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed crypto news feeds.")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="deactivate feed channels whose URL is not in the catalog",
    )
    args = parser.parse_args()
    asyncio.run(main(prune=args.prune))
