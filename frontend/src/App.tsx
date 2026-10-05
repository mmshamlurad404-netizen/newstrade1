import { useState } from "react";

import { api } from "./api/client";
import { useApi } from "./hooks/useApi";
import { Channels } from "./pages/Channels";
import { NewsFeed } from "./pages/NewsFeed";
import { Portfolio } from "./pages/Portfolio";
import { Settings } from "./pages/Settings";
import { Signals } from "./pages/Signals";

const TABS = ["News", "Signals", "Portfolio", "Channels", "Settings"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>("News");
  const { data: health } = useApi(() => api.health(), []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Newstrade</div>
        <nav>
          {TABS.map((item) => (
            <button
              key={item}
              className={`tab ${tab === item ? "tab-on" : ""}`}
              onClick={() => setTab(item)}
            >
              {item}
            </button>
          ))}
        </nav>
        <div className="status">
          {health?.kill_switch && <span className="badge badge-short">KILL</span>}
          <span className={`badge badge-${health?.trading_mode === "paper" ? "no_trade" : "long"}`}>
            {health?.trading_mode ?? "offline"}
          </span>
        </div>
      </header>

      <main>
        {tab === "News" && <NewsFeed />}
        {tab === "Signals" && <Signals />}
        {tab === "Portfolio" && <Portfolio />}
        {tab === "Channels" && <Channels />}
        {tab === "Settings" && <Settings />}
      </main>
    </div>
  );
}
