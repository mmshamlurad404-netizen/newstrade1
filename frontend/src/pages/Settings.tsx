import { useState } from "react";

import { api, getToken, setToken } from "../api/client";
import { Panel, Pill, StatCard } from "../components/ui";
import { useApi } from "../hooks/useApi";

export function Settings() {
  const [token, setTokenValue] = useState(getToken());
  const { data: health, error, reload } = useApi(() => api.health(), []);

  const applyToken = () => {
    setToken(token.trim());
    reload();
  };

  const toggleKillSwitch = async () => {
    if (!health) return;
    await api.setKillSwitch(!health.kill_switch);
    reload();
  };

  return (
    <div className="stack">
      <Panel title="Connection">
        <div className="field">
          <label htmlFor="token">API token</label>
          <input
            id="token"
            type="password"
            value={token}
            onChange={(event) => setTokenValue(event.target.value)}
            placeholder="Bearer token from the backend"
          />
          <button className="btn" onClick={applyToken}>
            Save token
          </button>
        </div>
        <p className="muted">
          The token is the backend <code>API_TOKEN</code>. Requests use it as a
          bearer credential and WebSockets pass it as a query parameter.
        </p>
      </Panel>

      <Panel title="Trading safety">
        {error && <p className="error">Backend unreachable: {error}</p>}
        {health && (
          <>
            <div className="stats">
              <StatCard label="Trading mode" value={health.trading_mode} />
              <StatCard
                label="Kill switch"
                value={health.kill_switch ? "ENGAGED" : "off"}
                tone={health.kill_switch ? "negative" : "positive"}
              />
            </div>
            <button
              className={`btn ${health.kill_switch ? "" : "btn-danger"}`}
              onClick={toggleKillSwitch}
            >
              {health.kill_switch ? "Release kill switch" : "Engage kill switch"}
            </button>
            <p className="muted">
              Paper trading is the default. Live execution requires an explicit
              confirmation and is blocked while the kill switch is engaged.
            </p>
          </>
        )}
        <p className="muted">
          <Pill>exchange keys never leave the backend</Pill>
        </p>
      </Panel>
    </div>
  );
}
