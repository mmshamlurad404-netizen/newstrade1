from app.services.ingestion import health


class FakeRedis:
    def __init__(self, fail=False):
        self.calls = []
        self._fail = fail
        self._hash = {}

    async def hset(self, key, mapping=None):
        self.calls.append(("hset", key, dict(mapping or {})))
        self._hash.update(mapping or {})

    async def hincrby(self, key, field, amount):
        self.calls.append(("hincrby", key, field, amount))
        self._hash[field] = str(int(self._hash.get(field, 0)) + amount)

    async def hgetall(self, key):
        if self._fail:
            raise RuntimeError("no redis")
        return dict(self._hash)


async def test_record_lifecycle_fields():
    client = FakeRedis()

    await health.record_started(client)
    await health.record_heartbeat(client, False)
    await health.record_event(client)
    await health.record_reconnect(client)

    state = await health.read_state(client)
    assert state["connected"] == "0"
    assert state["reconnects"] == "1"
    assert "heartbeat" in state
    assert "last_event" in state
    assert "started_at" in state


async def test_read_state_degrades_on_error():
    assert await health.read_state(FakeRedis(fail=True)) == {}
