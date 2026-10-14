import time

from app.services.ingestion import health
from app.services.ingestion import queue as queue_module


class FakeRedis:
    def __init__(self, fail=False, data=None):
        self.calls = []
        self._fail = fail
        self._hash = dict(data or {})

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


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(queue_module, "get_client", lambda: client)


async def test_snapshot_ok_when_connected_and_fresh(monkeypatch):
    now = time.time()
    _patch_client(
        monkeypatch,
        FakeRedis(data={"connected": "1", "heartbeat": str(now - 5)}),
    )
    snap = await health.snapshot(stale_seconds=120, timeout=2.0)
    assert snap["status"] == "ok"
    assert snap["reported"] is True
    assert snap["connected"] is True
    assert snap["stale"] is False
    assert 0 <= snap["seconds_since_heartbeat"] < 10


async def test_snapshot_degraded_when_stale(monkeypatch):
    now = time.time()
    _patch_client(
        monkeypatch,
        FakeRedis(data={"connected": "1", "heartbeat": str(now - 500)}),
    )
    snap = await health.snapshot(stale_seconds=120, timeout=2.0)
    assert snap["status"] == "degraded"
    assert snap["stale"] is True


async def test_snapshot_degraded_when_disconnected(monkeypatch):
    now = time.time()
    _patch_client(
        monkeypatch,
        FakeRedis(data={"connected": "0", "heartbeat": str(now - 5)}),
    )
    snap = await health.snapshot(stale_seconds=120, timeout=2.0)
    assert snap["status"] == "degraded"
    assert snap["connected"] is False


async def test_snapshot_unknown_when_unreported(monkeypatch):
    _patch_client(monkeypatch, FakeRedis())
    snap = await health.snapshot(stale_seconds=120, timeout=2.0)
    assert snap["status"] == "unknown"
    assert snap["reported"] is False


async def test_snapshot_unknown_on_redis_error(monkeypatch):
    _patch_client(monkeypatch, FakeRedis(fail=True))
    snap = await health.snapshot(stale_seconds=120, timeout=2.0)
    assert snap["status"] == "unknown"
