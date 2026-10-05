import { useState } from "react";

import { api } from "../api/client";
import type { Signal } from "../api/types";
import {
  ConfidenceBar,
  DirectionBadge,
  EmptyState,
  Panel,
  Pill,
} from "../components/ui";
import { useApi } from "../hooks/useApi";
import { useWebSocket } from "../hooks/useWebSocket";

function countdown(expiresAt: string | null | undefined): string {
  if (!expiresAt) return "-";
  const remaining = new Date(expiresAt).getTime() - Date.now();
  if (remaining <= 0) return "expired";
  const minutes = Math.floor(remaining / 60000);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function Signals() {
  const [confidenceMin, setConfidenceMin] = useState(0);
  const [direction, setDirection] = useState("");
  const [status, setStatus] = useState("");

  const params = new URLSearchParams();
  if (confidenceMin) params.set("confidence_min", String(confidenceMin));
  if (direction) params.set("direction", direction);
  if (status) params.set("status", status);
  const query = params.toString() ? `?${params.toString()}` : "";

  const { data, error, loading } = useApi(() => api.signals(query), [query]);
  const { items: live, connected } = useWebSocket<Signal>("/ws/signals");

  const known = new Set((data ?? []).map((item) => item.signal_id));
  const merged = [
    ...live.filter((item) => !known.has(item.signal_id)),
    ...(data ?? []),
  ];

  return (
    <Panel
      title="Signals"
      action={<span className={`dot ${connected ? "dot-on" : ""}`}>live</span>}
    >
      <div className="filters">
        <label className="range">
          min confidence: {confidenceMin}
          <input
            type="range"
            min={0}
            max={100}
            value={confidenceMin}
            onChange={(event) => setConfidenceMin(Number(event.target.value))}
          />
        </label>
        <select value={direction} onChange={(event) => setDirection(event.target.value)}>
          <option value="">Any direction</option>
          <option value="LONG">LONG</option>
          <option value="SHORT">SHORT</option>
        </select>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">Any status</option>
          <option value="active">active</option>
          <option value="rejected">rejected</option>
          <option value="closed">closed</option>
          <option value="expired">expired</option>
        </select>
      </div>

      {error && <p className="error">Failed to load signals: {error}</p>}
      {loading && !data && <p className="muted">Loading...</p>}
      {!loading && merged.length === 0 && <EmptyState message="No signals yet." />}

      <div className="signal-grid">
        {merged.map((signal) => (
          <article key={signal.signal_id} className="signal-card">
            <header>
              <span className="asset">{signal.asset}</span>
              <DirectionBadge direction={signal.direction} />
              <Pill tone={signal.status === "rejected" ? "negative" : "positive"}>
                {signal.status}
              </Pill>
            </header>
            <ConfidenceBar value={signal.confidence} />
            <dl className="levels">
              <div>
                <dt>Entry</dt>
                <dd>
                  {signal.entry_low?.toFixed(4)} - {signal.entry_high?.toFixed(4)}
                </dd>
              </div>
              <div>
                <dt>Stop</dt>
                <dd>{signal.stop_loss?.toFixed(4)}</dd>
              </div>
              <div>
                <dt>Targets</dt>
                <dd>{(signal.take_profits ?? []).map((tp) => tp.toFixed(4)).join(" / ")}</dd>
              </div>
              <div>
                <dt>Reward/Risk</dt>
                <dd>{signal.risk_reward?.toFixed(2) ?? "-"}</dd>
              </div>
              <div>
                <dt>Risk factor</dt>
                <dd>{signal.market_risk_factor?.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Expires in</dt>
                <dd>{countdown(signal.expires_at)}</dd>
              </div>
            </dl>
            {signal.rationale && <p className="rationale">{signal.rationale}</p>}
          </article>
        ))}
      </div>
    </Panel>
  );
}
