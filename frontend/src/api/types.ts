export interface News {
  id: number;
  headline: string;
  coins: string[];
  event_type: string | null;
  sentiment: string | null;
  sentiment_score: number | null;
  urgency: string | null;
  certainty: number | null;
  impact_timeframe: string | null;
  market_scope: string | null;
  source_count: number;
  origin_channel: string | null;
  asset_resolved: boolean;
  analysis_status: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
}

export interface Signal {
  signal_id: string;
  news_id: number | null;
  asset: string;
  direction: string;
  entry_low: number;
  entry_high: number;
  order_type: string;
  stop_loss: number;
  take_profits: number[];
  leverage_suggested: number;
  timeframe: string;
  confidence: number;
  market_risk_factor: number;
  risk_pct: number | null;
  risk_reward: number | null;
  rationale: string | null;
  status: string;
  prompt_version: string | null;
  created_at: string | null;
  expires_at: string | null;
}

export interface Trade {
  id: number;
  signal_id: string | null;
  mode: string;
  asset: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  pnl: number | null;
  pnl_pct: number | null;
  fees: number | null;
  opened_at: string;
  closed_at: string | null;
  close_reason: string | null;
}

export interface Portfolio {
  mode: string;
  equity: number;
  open_risk_amount: number;
  open_risk_pct: number;
  open_positions: Trade[];
  realized_pnl_total: number;
  realized_pnl_day: number;
  realized_pnl_week: number;
}

export interface Channel {
  id: number;
  telegram_id: number;
  username: string | null;
  title: string;
  is_private: boolean;
  credibility: number;
  is_active: boolean;
  last_seen_at: string | null;
}

export interface Health {
  status: string;
  trading_mode: string;
  kill_switch: boolean;
}
