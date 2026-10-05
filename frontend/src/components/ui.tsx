import type { ReactNode } from "react";

export function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>{title}</h2>
        {action}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function DirectionBadge({ direction }: { direction: string }) {
  return (
    <span className={`badge badge-${direction.toLowerCase()}`}>{direction}</span>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const tone = value >= 85 ? "high" : value >= 75 ? "medium" : "low";
  return (
    <div className="confidence">
      <div className="confidence-track">
        <div
          className={`confidence-fill confidence-${tone}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <span className="confidence-value">{value}</span>
    </div>
  );
}

export function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
}) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className={`stat-value ${tone ?? ""}`}>{value}</span>
    </div>
  );
}

export function Pill({ tone, children }: { tone?: string; children: ReactNode }) {
  return <span className={`pill ${tone ?? ""}`}>{children}</span>;
}

export function EmptyState({ message }: { message: string }) {
  return <p className="empty">{message}</p>;
}

export function ErrorState({ error }: { error: string }) {
  return <p className="error">Failed to load: {error}</p>;
}
