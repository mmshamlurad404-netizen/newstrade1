import redis.asyncio as redis

from app.core.config import settings

KILL_SWITCH_KEY = "runtime:kill_switch"

_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_kill_switch() -> bool:
    try:
        value = await _client.get(KILL_SWITCH_KEY)
    except Exception:
        return False
    return value == "1"


async def set_kill_switch(enabled: bool) -> bool:
    try:
        await _client.set(KILL_SWITCH_KEY, "1" if enabled else "0")
    except Exception:
        pass
    return enabled
