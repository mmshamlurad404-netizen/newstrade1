from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api import serializers
from app.schemas.api import FeedCreate
from app.services.ingestion import feeds
from app.services.ingestion.feed_catalog import DEFAULT_FEEDS, POLL_INTERVAL_SECONDS

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Bitcoin News</title>
<item>
  <title>Bitcoin hits new high</title>
  <link>https://example.com/a</link>
  <description>&lt;p&gt;BTC pumps past resistance&lt;/p&gt;</description>
  <pubDate>Wed, 01 Jan 2025 12:00:00 GMT</pubDate>
  <guid>https://example.com/a</guid>
</item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Ethereum upgrade scheduled</title>
    <link href="https://example.com/b" rel="alternate"/>
    <summary>ETH news summary</summary>
    <updated>2025-01-02T10:00:00Z</updated>
    <id>tag:example.com,2025:b</id>
  </entry>
</feed>"""

JSON_FEED = (
    b'{"version":"https://jsonfeed.org/version/1.1","items":['
    b'{"id":"1","url":"https://example.com/c","title":"Solana news",'
    b'"content_text":"SOL summary","date_published":"2025-01-03T09:00:00Z"}]}'
)


def _channel():
    return SimpleNamespace(telegram_id=-12345, title="Example Feed")


def test_parse_rss():
    entries = feeds.parse_feed(RSS)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "Bitcoin hits new high"
    assert entry.link == "https://example.com/a"
    assert "BTC pumps" in (entry.summary or "")
    assert entry.published is not None and entry.published.tzinfo is not None


def test_parse_atom():
    entries = feeds.parse_feed(ATOM)
    assert len(entries) == 1
    assert entries[0].title == "Ethereum upgrade scheduled"
    assert entries[0].link == "https://example.com/b"


def test_parse_json_feed():
    entries = feeds.parse_feed(JSON_FEED)
    assert len(entries) == 1
    assert entries[0].title == "Solana news"
    assert entries[0].link == "https://example.com/c"


def test_parse_feed_handles_garbage():
    assert feeds.parse_feed(b"not xml or json") == []
    assert feeds.parse_feed(b"<html><body>404</body></html>") == []


def test_stable_message_id_is_deterministic_and_positive():
    first = feeds.stable_message_id("https://example.com/a")
    second = feeds.stable_message_id("https://example.com/a")
    assert first == second
    assert first > 0
    assert first < 2**63


def test_synthetic_telegram_id_is_negative_and_deterministic():
    value = feeds.synthetic_telegram_id("https://example.com/feed")
    assert value == feeds.synthetic_telegram_id("https://example.com/feed")
    assert value < 0


def test_strip_html():
    assert feeds.strip_html("<p>Hello &amp; <b>world</b></p>") == "Hello & world"
    assert feeds.strip_html(None) == ""


def test_parse_date_formats():
    rfc = feeds.parse_date("Wed, 01 Jan 2025 12:00:00 GMT")
    iso = feeds.parse_date("2025-01-02T10:00:00Z")
    assert rfc is not None and rfc.tzinfo is not None
    assert iso is not None and iso.tzinfo is not None
    assert feeds.parse_date("not a date") is None


def test_build_raw_item_maps_entry():
    entry = feeds.FeedEntry(
        guid="https://example.com/a",
        title="Bitcoin hits new high",
        link="https://example.com/a",
        summary="<p>BTC pumps past resistance</p>",
        published=feeds.parse_date("Wed, 01 Jan 2025 12:00:00 GMT"),
    )
    item = feeds.build_raw_item(_channel(), entry)
    assert item is not None
    assert item["channel_telegram_id"] == -12345
    assert item["message_id"] == feeds.stable_message_id("https://example.com/a")
    assert "Bitcoin hits new high" in item["normalized_text"]
    assert "BTC pumps" in item["normalized_text"]
    assert "https://example.com/a" in item["links"]
    assert item["content_hash"]
    assert item["message_id"] > 0


def test_build_raw_item_skips_empty():
    entry = feeds.FeedEntry(guid="x", title="", link=None, summary=None, published=None)
    assert feeds.build_raw_item(_channel(), entry) is None


def test_feed_create_validation():
    body = FeedCreate(title="CoinDesk", url="https://example.com/feed")
    assert body.credibility == 0.6
    assert body.poll_interval_seconds == 300

    with pytest.raises(ValidationError):
        FeedCreate(title="", url="https://example.com/feed")
    with pytest.raises(ValidationError):
        FeedCreate(title="x", url="https://example.com/feed", credibility=2.0)
    with pytest.raises(ValidationError):
        FeedCreate(
            title="x", url="https://example.com/feed", poll_interval_seconds=1
        )


def test_serialize_channel_feed_fields():
    channel = SimpleNamespace(
        id=1,
        telegram_id=-200195541173621,
        username=None,
        title="CoinDesk",
        kind="feed",
        feed_url="https://www.coindesk.com/arc/outboundfeeds/rss/",
        poll_interval_seconds=300,
        last_polled_at=None,
        is_private=False,
        credibility=0.75,
        is_active=True,
        last_seen_at=None,
    )
    data = serializers.serialize_channel(channel)
    assert data["kind"] == "feed"
    assert data["feed_url"].endswith("rss/")
    assert data["poll_interval_seconds"] == 300


def test_feed_catalog_has_one_hundred_feeds():
    assert len(DEFAULT_FEEDS) == 100


def test_feed_catalog_entries_are_well_formed():
    urls = [url for _title, url, _cred in DEFAULT_FEEDS]
    titles = [title for title, _url, _cred in DEFAULT_FEEDS]
    assert len(set(urls)) == len(urls)
    assert len(set(titles)) == len(titles)
    for title, url, credibility in DEFAULT_FEEDS:
        assert title.strip()
        assert url.startswith("https://")
        assert 0.0 <= credibility <= 1.0


def test_feed_catalog_synthetic_ids_are_unique():
    ids = {feeds.synthetic_telegram_id(url) for _t, url, _c in DEFAULT_FEEDS}
    assert len(ids) == len(DEFAULT_FEEDS)
    assert POLL_INTERVAL_SECONDS >= 60
