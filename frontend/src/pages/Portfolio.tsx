import { api } from "../api/client";
import { EmptyState, Panel, Pill, StatCard } from "../components/ui";
import { useApi } from "../hooks/useApi";

function money(value: number | null | undefined): string {
  return value == null ? "-" : value.toFixed(2);
}

export function Portfolio() {
  const { data, error, loading } = useApi(() => api.portfolio(), []);
  const history = useApi(() => api.trades("?status=closed"), []);

  if (error) return <Panel title="Portfolio"><p className="error">{error}</p></Panel>;
  if (loading || !data) return <Panel title="Portfolio"><p className="muted">Loading...</p></Panel>;

  return (
    <div className="stack">
      <Panel title={`Portfolio (${data.mode})`}>
        <div className="stats">
          <StatCard label="Equity" value={money(data.equity)} />
          <StatCard
            label="Open risk"
            value={`${money(data.open_risk_amount)} (${data.open_risk_pct.toFixed(2)}%)`}
          />
          <StatCard
            label="Realized today"
            value={money(data.realized_pnl_day)}
            tone={data.realized_pnl_day >= 0 ? "positive" : "negative"}
          />
          <StatCard
            label="Realized week"
            value={money(data.realized_pnl_week)}
            tone={data.realized_pnl_week >= 0 ? "positive" : "negative"}
          />
          <StatCard
            label="Realized total"
            value={money(data.realized_pnl_total)}
            tone={data.realized_pnl_total >= 0 ? "positive" : "negative"}
          />
        </div>
      </Panel>

      <Panel title="Open positions">
        {data.open_positions.length === 0 ? (
          <EmptyState message="No open positions." />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Direction</th>
                <th>Entry</th>
                <th>Qty</th>
                <th>Fees</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {data.open_positions.map((trade) => (
                <tr key={trade.id}>
                  <td>{trade.asset}</td>
                  <td>
                    <Pill tone={trade.direction === "LONG" ? "positive" : "negative"}>
                      {trade.direction}
                    </Pill>
                  </td>
                  <td>{money(trade.entry_price)}</td>
                  <td>{trade.quantity?.toFixed(4)}</td>
                  <td>{money(trade.fees)}</td>
                  <td>{trade.opened_at?.slice(0, 19).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel title="Closed trades">
        {history.error && <p className="error">{history.error}</p>}
        {history.data && history.data.length === 0 && (
          <EmptyState message="No closed trades yet." />
        )}
        {history.data && history.data.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Mode</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>PnL</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {history.data.map((trade) => (
                <tr key={`${trade.mode}-${trade.id}`}>
                  <td>{trade.asset}</td>
                  <td>{trade.mode}</td>
                  <td>{money(trade.entry_price)}</td>
                  <td>{money(trade.exit_price)}</td>
                  <td className={(trade.pnl ?? 0) >= 0 ? "positive" : "negative"}>
                    {money(trade.pnl)} ({money(trade.pnl_pct)}%)
                  </td>
                  <td>{trade.close_reason ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
