import { useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import { EmptyState, Panel, Pill } from "../components/ui";
import { useApi } from "../hooks/useApi";

function lastSeen(value: string | null): string {
  return value?.slice(0, 19).replace("T", " ") ?? "-";
}

export function Channels() {
  const { data, error, loading, reload } = useApi(() => api.channels(), []);
  const { data: feeds, reload: reloadFeeds } = useApi(() => api.feeds(), []);

  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [credibility, setCredibility] = useState(0.6);
  const [formError, setFormError] = useState<string | null>(null);

  async function addFeed(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      await api.createFeed({ title, url, credibility });
      setTitle("");
      setUrl("");
      reloadFeeds();
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  async function toggle(feedId: number, active: boolean) {
    await api.setFeedActive(feedId, active);
    reloadFeeds();
  }

  return (
    <div className="stack">
      <Panel title="Channels & sources">
        {error && <p className="error">Failed to load channels: {error}</p>}
        {loading && !data && <p className="muted">Loading...</p>}
        {data && data.length === 0 && (
          <EmptyState message="No channels tracked yet." />
        )}
        {data && data.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Source</th>
                <th>Username / URL</th>
                <th>Credibility</th>
                <th>Active</th>
                <th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {data.map((channel) => (
                <tr key={channel.id}>
                  <td>{channel.title}</td>
                  <td>
                    <Pill tone={channel.kind === "feed" ? "positive" : ""}>
                      {channel.kind}
                    </Pill>
                  </td>
                  <td>{channel.feed_url ?? channel.username ?? "-"}</td>
                  <td>{channel.credibility?.toFixed(3)}</td>
                  <td>{channel.is_active ? "yes" : "no"}</td>
                  <td>{lastSeen(channel.last_seen_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel title="Crypto news website feeds">
        <form className="device-form" onSubmit={addFeed}>
          <input
            placeholder="Feed name (e.g. CoinDesk)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
          />
          <input
            placeholder="RSS / Atom / JSON feed URL"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            required
          />
          <input
            type="number"
            step="0.05"
            min="0"
            max="1"
            value={credibility}
            onChange={(event) => setCredibility(Number(event.target.value))}
            title="credibility"
          />
          <button type="submit">Add feed</button>
        </form>
        {formError && <p className="error">{formError}</p>}

        {(feeds ?? []).length === 0 && (
          <EmptyState message="No website feeds yet. Add one above." />
        )}
        {(feeds ?? []).length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Credibility</th>
                <th>Last polled</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {(feeds ?? []).map((feed) => (
                <tr key={feed.id}>
                  <td>{feed.title}</td>
                  <td className="mono">{feed.feed_url}</td>
                  <td>{feed.credibility?.toFixed(3)}</td>
                  <td>{lastSeen(feed.last_polled_at)}</td>
                  <td>
                    <button
                      className="link"
                      onClick={() => toggle(feed.id, !feed.is_active)}
                    >
                      {feed.is_active ? "pause" : "resume"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
