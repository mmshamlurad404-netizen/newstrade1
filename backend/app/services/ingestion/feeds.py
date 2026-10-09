"""Crypto news website feeds (RSS / Atom / JSON Feed) as an ingestion source.

Website feeds are treated like any other raw source: each entry is mapped to a
``RawItem``-compatible dict and published onto the ``raw_news`` stream, after
which the existing cluster -> analyze -> signal pipeline handles it unchanged.
"""

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.core.config import settings
from app.services.ingestion.dedup import content_hash
from app.services.ingestion.normalize import normalize

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass
class FeedEntry:
    guid: str
    title: str
    link: str | None
    summary: str | None
    published: datetime | None


def synthetic_telegram_id(feed_url: str) -> int:
    """Deterministic negative id so feeds share the channels table safely.

    Real Telegram ids are positive, so feeds never collide with them and the
    Telegram listener can ignore them by ``kind``.
    """
    digest = hashlib.sha1(feed_url.encode("utf-8")).hexdigest()[:12]
    return -(int(digest, 16))


def stable_message_id(guid: str) -> int:
    return int(hashlib.sha1(guid.encode("utf-8")).hexdigest()[:15], 16)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip()


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element, *names: str) -> str | None:
    for child in element:
        if _localname(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return None


def _atom_link(entry) -> str | None:
    fallback = None
    for child in entry:
        if _localname(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if not href:
            continue
        rel = child.attrib.get("rel", "alternate")
        if rel == "alternate":
            return href
        fallback = fallback or href
    return fallback


def parse_rss(root) -> list[FeedEntry]:
    channel = next(
        (child for child in root if _localname(child.tag) == "channel"), None
    )
    if channel is None:
        return []
    entries: list[FeedEntry] = []
    for item in channel:
        if _localname(item.tag) != "item":
            continue
        title = _child_text(item, "title") or ""
        link = _child_text(item, "link")
        guid = _child_text(item, "guid") or link or title
        summary = _child_text(item, "description", "encoded", "summary")
        published = parse_date(
            _child_text(item, "pubdate", "published", "date")
        )
        entries.append(
            FeedEntry(guid, strip_html(title), link, summary, published)
        )
    return entries


def parse_atom(root) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    for entry in root:
        if _localname(entry.tag) != "entry":
            continue
        title = _child_text(entry, "title") or ""
        link = _atom_link(entry)
        guid = _child_text(entry, "id") or link or title
        summary = _child_text(entry, "summary", "content")
        published = parse_date(
            _child_text(entry, "published", "updated", "date")
        )
        entries.append(
            FeedEntry(guid, strip_html(title), link, summary, published)
        )
    return entries


def parse_json_feed(payload: dict) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    for item in payload.get("items", []):
        title = item.get("title") or ""
        link = item.get("url") or item.get("external_url")
        guid = item.get("id") or link or title
        summary = item.get("summary") or item.get("content_text") or item.get(
            "content_html"
        )
        published = parse_date(item.get("date_published") or item.get("date_modified"))
        entries.append(
            FeedEntry(guid, strip_html(title), link, summary, published)
        )
    return entries


def parse_feed(content: bytes) -> list[FeedEntry]:
    """Parse RSS, Atom or JSON Feed bytes into entries. Returns [] on failure."""
    text = content.lstrip()
    if text.startswith(b"{") or text.startswith(b"["):
        try:
            payload = json.loads(content)
        except (ValueError, UnicodeDecodeError):
            return []
        if isinstance(payload, dict):
            return parse_json_feed(payload)
        return []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    local = _localname(root.tag)
    if local == "rss":
        return parse_rss(root)
    if local == "feed":
        return parse_atom(root)
    return []


async def fetch_feed(url: str, client: httpx.AsyncClient | None = None) -> bytes:
    headers = {"User-Agent": settings.feed_user_agent, "Accept": "*/*"}
    if client is not None:
        response = await client.get(url, headers=headers)
    else:
        async with httpx.AsyncClient(
            timeout=settings.feed_request_timeout, follow_redirects=True
        ) as own:
            response = await own.get(url, headers=headers)
    response.raise_for_status()
    return response.content


def build_raw_item(channel, entry: FeedEntry) -> dict | None:
    body = " ".join(part for part in [entry.title, strip_html(entry.summary)] if part)
    normalized, links = normalize(body)
    if not normalized:
        return None
    if entry.link and entry.link not in links:
        links.append(entry.link)
    posted = entry.published or datetime.now(timezone.utc)
    return {
        "channel_telegram_id": channel.telegram_id,
        "channel_title": channel.title,
        "is_private": False,
        "message_id": stable_message_id(entry.guid),
        "posted_at": posted.isoformat(),
        "original_text": body,
        "normalized_text": normalized,
        "links": links,
        "media_type": None,
        "views": None,
        "forwards": None,
        "content_hash": content_hash(normalized),
    }
