import { api } from "../api/client";
import { EmptyState, Panel, Pill } from "../components/ui";
import { useApi } from "../hooks/useApi";

export function Channels() {
  const { data, error, loading } = useApi(() => api.channels(), []);

  return (
    <Panel title="Channels">
      {error && <p className="error">Failed to load channels: {error}</p>}
      {loading && !data && <p className="muted">Loading...</p>}
      {data && data.length === 0 && <EmptyState message="No channels tracked yet." />}
      {data && data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Username</th>
              <th>Credibility</th>
              <th>Privacy</th>
              <th>Active</th>
              <th>Last seen</th>
            </tr>
          </thead>
          <tbody>
            {data.map((channel) => (
              <tr key={channel.id}>
                <td>{channel.title}</td>
                <td>{channel.username ?? "-"}</td>
                <td>{channel.credibility?.toFixed(3)}</td>
                <td>
                  <Pill tone={channel.is_private ? "negative" : ""}>
                    {channel.is_private ? "private" : "public"}
                  </Pill>
                </td>
                <td>{channel.is_active ? "yes" : "no"}</td>
                <td>{channel.last_seen_at?.slice(0, 19).replace("T", " ") ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
