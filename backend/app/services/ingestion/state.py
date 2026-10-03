from sqlalchemy import func, select, update

from app.db.session import async_session_factory
from app.models.ingestion import Channel


async def load_tracked_channels() -> list[Channel]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Channel).where(Channel.is_active.is_(True))
        )
        return list(result.scalars().all())


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
