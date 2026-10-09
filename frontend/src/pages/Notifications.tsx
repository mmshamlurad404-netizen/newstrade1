import { useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import { EmptyState, Panel, Pill } from "../components/ui";
import { useApi } from "../hooks/useApi";

function timeAgo(iso: string | null): string {
  if (!iso) return "-";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function Notifications() {
  const { data, error, loading, reload } = useApi(() => api.notifications(), []);
  const { data: devices, reload: reloadDevices } = useApi(() => api.devices(), []);

  const [token, setToken] = useState("");
  const [platform, setPlatform] = useState("android");
  const [label, setLabel] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const notes = data ?? [];
  const unread = notes.filter((item) => !item.read_at).length;

  async function markRead(id: number) {
    await api.markNotificationRead(id);
    reload();
  }

  async function markAll() {
    await api.markAllNotificationsRead();
    reload();
  }

  async function register(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      await api.registerDevice({ token, platform, label: label || undefined });
      setToken("");
      setLabel("");
      reloadDevices();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  return (
    <div className="stack">
      <Panel
        title={`Notifications${unread ? ` (${unread} unread)` : ""}`}
        action={
          unread > 0 ? (
            <button className="link" onClick={markAll}>
              mark all read
            </button>
          ) : null
        }
      >
        {error && <p className="error">Failed to load notifications: {error}</p>}
        {loading && !data && <p className="muted">Loading...</p>}
        {!loading && notes.length === 0 && (
          <EmptyState message="No notifications yet." />
        )}

        <ul className="notify-list">
          {notes.map((note) => (
            <li
              key={note.id}
              className={`notify-item ${note.read_at ? "" : "notify-unread"}`}
            >
              <div className="notify-main">
                <div className="notify-title">
                  <Pill tone={note.event_type.includes("rejected") ? "negative" : "positive"}>
                    {note.event_type}
                  </Pill>
                  <span>{note.title}</span>
                </div>
                {note.body && <p className="muted">{note.body}</p>}
                <span className="notify-time">{timeAgo(note.created_at)}</span>
              </div>
              {!note.read_at && (
                <button className="link" onClick={() => markRead(note.id)}>
                  mark read
                </button>
              )}
            </li>
          ))}
        </ul>
      </Panel>

      <Panel title="Devices">
        <form className="device-form" onSubmit={register}>
          <input
            placeholder="FCM registration token"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            required
          />
          <select value={platform} onChange={(event) => setPlatform(event.target.value)}>
            <option value="android">android</option>
            <option value="windows">windows</option>
            <option value="web">web</option>
          </select>
          <input
            placeholder="label (optional)"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
          />
          <button type="submit">Register</button>
        </form>
        {formError && <p className="error">{formError}</p>}

        <ul className="device-list">
          {(devices ?? []).map((device) => (
            <li key={device.id}>
              <span className="mono">{device.token.slice(0, 16)}...</span>
              <Pill tone={device.is_active ? "positive" : "negative"}>
                {device.platform}
              </Pill>
              {device.label && <span className="muted">{device.label}</span>}
            </li>
          ))}
          {(devices ?? []).length === 0 && (
            <EmptyState message="No devices registered." />
          )}
        </ul>
      </Panel>
    </div>
  );
}
