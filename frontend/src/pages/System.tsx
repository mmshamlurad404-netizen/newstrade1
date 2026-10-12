import { api } from "../api/client";
import { Panel, StatCard } from "../components/ui";
import { useApi } from "../hooks/useApi";

type Metrics = Record<string, number>;

const STREAMS: Array<{ key: string; label: string }> = [
  { key: "raw_news", label: "raw_news" },
  { key: "clustered_news", label: "clustered_news" },
  { key: "analyzed_news", label: "analyzed_news" },
  { key: "signals", label: "signals" },
  { key: "dlq", label: "dlq" },
];

const LAG_WARN = 500;

function val(m: Metrics, key: string): number {
  return m[key] ?? 0;
}

function statusCount(m: Metrics, base: string, status: string): number {
  return m[`${base}{status="${status}"}`] ?? 0;
}

function sumPrefix(m: Metrics, prefix: string): number {
  return Object.entries(m)
    .filter(([key]) => key.startsWith(prefix))
    .reduce((total, [, value]) => total + value, 0);
}

function streamLength(m: Metrics, stream: string): number {
  return val(m, `newstrade_stream_length{stream="${stream}"}`);
}

function streamLag(m: Metrics, stream: string): number {
  return sumPrefix(m, `newstrade_stream_lag{stream="${stream}"`);
}

function streamPending(m: Metrics, stream: string): number {
  return sumPrefix(m, `newstrade_stream_pending{stream="${stream}"`);
}

function money(value: number): string {
  return value.toFixed(2);
}

export function System() {
  const { data, error, loading, reload } = useApi(() => api.metrics(), []);

  if (error)
    return (
      <Panel title="System">
        <p className="error">{error}</p>
      </Panel>
    );
  if (loading || !data)
    return (
      <Panel title="System">
        <p className="muted">Loading...</p>
      </Panel>
    );

  const m = data.metrics;
  const backlog = STREAMS.filter(
    (s) => s.key !== "dlq" && streamLag(m, s.key) > LAG_WARN
  );

  return (
    <div className="stack">
      <Panel
        title="System health"
        action={
          <button className="tab" onClick={reload}>
            Refresh
          </button>
        }
      >
        <div className="stats">
          <StatCard
            label="News pending"
            value={String(statusCount(m, "newstrade_news_total", "pending"))}
          />
          <StatCard
            label="News analyzed"
            value={String(statusCount(m, "newstrade_news_total", "analyzed"))}
          />
          <StatCard
            label="DLQ size"
            value={String(streamLength(m, "dlq"))}
            tone={streamLength(m, "dlq") > 0 ? "negative" : undefined}
          />
          <StatCard
            label="Backlog"
            value={backlog.length === 0 ? "ok" : backlog.map((b) => b.key).join(", ")}
            tone={backlog.length === 0 ? "positive" : "negative"}
          />
        </div>
      </Panel>

      <Panel title="Pipeline streams">
        <table className="table">
          <thead>
            <tr>
              <th>Stream</th>
              <th>Length</th>
              <th>Pending</th>
              <th>Lag</th>
            </tr>
          </thead>
          <tbody>
            {STREAMS.map((s) => {
              const lag = streamLag(m, s.key);
              return (
                <tr key={s.key}>
                  <td>{s.label}</td>
                  <td>{streamLength(m, s.key)}</td>
                  <td>{streamPending(m, s.key)}</td>
                  <td className={lag > LAG_WARN ? "negative" : undefined}>
                    {lag}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      <Panel title="Trading">
        <div className="stats">
          <StatCard
            label="Paper open"
            value={String(val(m, "newstrade_paper_trades_open"))}
          />
          <StatCard
            label="Paper closed"
            value={String(val(m, "newstrade_paper_trades_closed_total"))}
          />
          <StatCard
            label="Wins / Losses"
            value={`${val(m, "newstrade_paper_trades_wins_total")} / ${val(
              m,
              "newstrade_paper_trades_losses_total"
            )}`}
          />
          <StatCard
            label="Realized PnL"
            value={money(val(m, "newstrade_paper_realized_pnl"))}
            tone={
              val(m, "newstrade_paper_realized_pnl") >= 0
                ? "positive"
                : "negative"
            }
          />
          <StatCard
            label="Realized today"
            value={money(val(m, "newstrade_paper_realized_pnl_day"))}
            tone={
              val(m, "newstrade_paper_realized_pnl_day") >= 0
                ? "positive"
                : "negative"
            }
          />
          <StatCard
            label="Open risk"
            value={`${val(m, "newstrade_paper_open_risk_pct").toFixed(2)}%`}
          />
          <StatCard
            label="Signals active"
            value={String(statusCount(m, "newstrade_signals_total", "active"))}
          />
          <StatCard
            label="Signals rejected"
            value={String(statusCount(m, "newstrade_signals_total", "rejected"))}
          />
        </div>
      </Panel>

      <Panel title="Sources">
        <div className="stats">
          <StatCard
            label="Channels total"
            value={String(val(m, "newstrade_channels_total"))}
          />
          <StatCard
            label="Feeds active"
            value={String(val(m, 'newstrade_channels_active{kind="feed"}'))}
          />
          <StatCard
            label="Telegram active"
            value={String(val(m, 'newstrade_channels_active{kind="telegram"}'))}
          />
        </div>
      </Panel>
    </div>
  );
}
