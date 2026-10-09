from sqlalchemy import func, select, update

from app.db.session import async_session_factory
from app.models.ingestion import Channel


async def load_tracked_channels() -> list[Channel]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.is_active.is_(True),
                Channel.kind == "telegram",
            )
        )
        return list(result.scalars().all())


async def load_feed_channels() -> list[Channel]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.is_active.is_(True),
                Channel.kind == "feed",
            )
        )
        return list(result.scalars().all())


async def update_feed_polled(channel_id: int, posted_at=None) -> None:
    values = {"last_polled_at": func.now(), "last_seen_at": func.now()}
    if posted_at is not None:
        values["last_seen_at"] = posted_at
    async with async_session_factory() as session:
        await session.execute(
            update(Channel).where(Channel.id == channel_id).values(**values)
        )
        await session.commit()


async def update_last_message_id(telegram_id: int, message_id: int) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(Channel)
            .where(Channel.telegram_id == telegram_id)
            .values(last_message_id=message_id, last_seen_at=func.now())
        )
        await session.commit()


async def record_flood_wait(account_label: str) -> None:
    from app.models.ingestion import IngestionAccount

    async with async_session_factory() as session:
        await session.execute(
            update(IngestionAccount)
            .where(IngestionAccount.label == account_label)
            .values(last_flood_wait_at=func.now())
        )
        await session.commit()
