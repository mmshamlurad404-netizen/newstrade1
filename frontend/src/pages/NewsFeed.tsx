import { useState } from "react";

import { api } from "../api/client";
import type { News } from "../api/types";
import { EmptyState, Panel, Pill } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { useWebSocket } from "../hooks/useWebSocket";

function sentimentTone(sentiment: string | null): string {
  if (sentiment === "bullish") return "positive";
  if (sentiment === "bearish") return "negative";
  return "";
}

export function NewsFeed() {
  const [coin, setCoin] = useState("");
  const [eventType, setEventType] = useState("");
  const [urgency, setUrgency] = useState("");

  const params = new URLSearchParams();
  if (coin) params.set("coin", coin);
  if (eventType) params.set("event_type", eventType);
  if (urgency) params.set("urgency", urgency);
  const query = params.toString() ? `?${params.toString()}` : "";

  const { data, error, loading } = useApi(() => api.news(query), [query]);
  const { items: live, connected } = useWebSocket<News>("/ws/news");

  const known = new Set((data ?? []).map((item) => item.id));
  const merged = [
    ...live.filter((item) => !known.has(item.id)),
    ...(data ?? []),
  ];

  return (
    <Panel
      title="News feed"
      action={<span className={`dot ${connected ? "dot-on" : ""}`}>live</span>}
    >
      <div className="filters">
        <input
          placeholder="Coin (e.g. SOL)"
          value={coin}
          onChange={(event) => setCoin(event.target.value.toUpperCase())}
        />
        <select value={eventType} onChange={(event) => setEventType(event.target.value)}>
          <option value="">All events</option>
          {["listing", "delisting", "hack", "partnership", "unlock", "regulation", "adoption", "macro"].map(
            (value) => (
              <option key={value} value={value}>
                {value}
              </option>
            )
          )}
        </select>
        <select value={urgency} onChange={(event) => setUrgency(event.target.value)}>
          <option value="">Any urgency</option>
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
        </select>
      </div>

      {error && <p className="error">Failed to load news: {error}</p>}
      {loading && !data && <p className="muted">Loading...</p>}
      {!loading && merged.length === 0 && <EmptyState message="No news yet." />}

      <ul className="news-list">
        {merged.map((item) => (
          <li key={item.id} className="news-item">
            <div className="news-top">
              <span className="coins">{item.coins.join(", ") || "unmapped"}</span>
              <Pill tone={sentimentTone(item.sentiment)}>
                {item.sentiment ?? "unknown"}
              </Pill>
              {item.urgency === "high" && <Pill tone="negative">high urgency</Pill>}
              <span className="muted">{item.source_count} source(s)</span>
            </div>
            <h3>{item.headline}</h3>
            <div className="news-meta">
              <span>{item.event_type ?? "other"}</span>
              <span>{item.origin_channel ?? "unknown channel"}</span>
              <span>{item.first_seen_at?.replace("T", " ").slice(0, 19)}</span>
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
