import asyncio

from telethon import TelegramClient

from app.core.config import settings


async def main() -> None:
    client = TelegramClient(
        settings.tg_session_name, settings.tg_api_id, settings.tg_api_hash
    )
    await client.start()
    me = await client.get_me()
    print("Logged in as:", me.username or me.id)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
