from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import app.services.ingestion.feed_worker as fw
from app.services.ingestion import feeds

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Bitcoin News</title>
<item>
  <title>Bitcoin hits new high</title>
  <link>https://example.com/a</link>
  <description>BTC pumps</description>
  <pubDate>Wed, 01 Jan 2025 12:00:00 GMT</pubDate>
  <guid>https://example.com/a</guid>
</item>
<item>
  <title>Ethereum upgrade</title>
  <link>https://example.com/b</link>
  <description>ETH news</description>
  <pubDate>Wed, 01 Jan 2025 13:00:00 GMT</pubDate>
  <guid>https://example.com/b</guid>
</item>
</channel></rss>"""


def _channel():
    return SimpleNamespace(
        id=1,
        telegram_id=-999,
        title="Example Feed",
        feed_url="https://example.com/feed",
        poll_interval_seconds=300,
        last_polled_at=None,
    )


def test_is_due_when_never_polled():
    now = datetime.now(timezone.utc)
    assert fw.is_due(_channel(), now) is True


def test_is_due_respects_interval():
    now = datetime.now(timezone.utc)
    fresh = _channel()
    fresh.last_polled_at = now - timedelta(seconds=10)
    stale = _channel()
    stale.last_polled_at = now - timedelta(seconds=600)
    assert fw.is_due(fresh, now) is False
    assert fw.is_due(stale, now) is True


async def test_poll_channel_publishes_new_entries(monkeypatch):
    fw._seen.clear()
    published = []

    async def fake_fetch(url, client):
        return RSS

    async def fake_publish(item):
        published.append(item)

    polls = []

    async def fake_update(channel_id, newest):
        polls.append((channel_id, newest))

    monkeypatch.setattr(fw.feeds, "fetch_feed", fake_fetch)
    monkeypatch.setattr(fw, "publish_raw", fake_publish)
    monkeypatch.setattr(fw, "update_feed_polled", fake_update)

    now = datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc)
    count = await fw.poll_channel(object(), _channel(), now)

    assert count == 2
    assert len(published) == 2
    assert polls and polls[0][0] == 1

    # second poll publishes nothing (already seen)
    count2 = await fw.poll_channel(object(), _channel(), now)
    assert count2 == 0
    assert len(published) == 2


async def test_poll_channel_skips_old_entries(monkeypatch):
    fw._seen.clear()
    published = []

    async def fake_fetch(url, client):
        return RSS

    async def fake_publish(item):
        published.append(item)

    async def fake_update(channel_id, newest):
        return None

    monkeypatch.setattr(fw.feeds, "fetch_feed", fake_fetch)
    monkeypatch.setattr(fw, "publish_raw", fake_publish)
    monkeypatch.setattr(fw, "update_feed_polled", fake_update)

    # 'now' far in the future so all entries are older than the cutoff
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    count = await fw.poll_channel(object(), _channel(), now)
    assert count == 0
    assert published == []


async def test_poll_channel_caps_seen_set(monkeypatch):
    fw._seen.clear()
    monkeypatch.setattr(fw, "MAX_SEEN_PER_CHANNEL", 1)

    async def fake_fetch(url, client):
        return RSS

    async def fake_publish(item):
        return None

    async def fake_update(channel_id, newest):
        return None

    monkeypatch.setattr(fw.feeds, "fetch_feed", fake_fetch)
    monkeypatch.setattr(fw, "publish_raw", fake_publish)
    monkeypatch.setattr(fw, "update_feed_polled", fake_update)

    now = datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc)
    await fw.poll_channel(object(), _channel(), now)
    seen = fw._seen[1]
    assert len(seen) <= 2
    assert feeds.stable_message_id("https://example.com/b") in seen
