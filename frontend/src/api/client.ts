import type {
  Channel,
  Device,
  Health,
  News,
  Notification,
  Portfolio,
  Signal,
  Trade,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "newstrade_token";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? import.meta.env.VITE_API_TOKEN ?? "";
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  news: (params = "") => request<News[]>(`/api/news${params}`),
  newsDetail: (id: number) =>
    request<{ news: News; sources: Array<Record<string, unknown>> }>(
      `/api/news/${id}`
    ),
  signals: (params = "") => request<Signal[]>(`/api/signals${params}`),
  signal: (id: string) =>
    request<{ signal: Signal; news: News | null }>(`/api/signal/${id}`),
  portfolio: () => request<Portfolio>("/api/portfolio"),
  trades: (params = "") => request<Trade[]>(`/api/trades${params}`),
  channels: () => request<Channel[]>("/api/channels"),
  killSwitch: () => request<{ kill_switch: boolean }>("/api/kill-switch"),
  setKillSwitch: (enabled: boolean) =>
    request<{ kill_switch: boolean }>("/api/kill-switch", {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  notifications: (params = "") =>
    request<Notification[]>(`/api/notifications${params}`),
  markNotificationRead: (id: number) =>
    request<Notification>(`/api/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () =>
    request<{ status: string; marked: number }>("/api/notifications/read-all", {
      method: "POST",
    }),
  devices: () => request<Device[]>("/api/devices"),
  registerDevice: (body: { token: string; platform: string; label?: string }) =>
    request<Device>("/api/devices", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export function wsUrl(path: string): string {
  const base = BASE || window.location.origin;
  const url = new URL(base);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const token = getToken();
  return `${protocol}//${url.host}${path}${
    token ? `?token=${encodeURIComponent(token)}` : ""
  }`;
}
