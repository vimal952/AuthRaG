import { useState, useEffect } from "react";
import { adminApi } from "../services/api";

const TABS = ["Overview", "Users", "Audit Logs"];

function StatCard({ label, value, className }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${className || ""}`}>{value ?? "—"}</div>
    </div>
  );
}

function Overview({ data }) {
  if (!data) {
    return (
      <div className="analytics-loading">
        <div className="analytics-spinner"></div>
        <p>Analyzing system telemetry...</p>
      </div>
    );
  }

  const maxCount = Math.max(...(data.daily_queries?.map((d) => d.count) || [1]), 1);

  return (
    <>
      <div className="analytics-grid">
        <StatCard label="Total Queries (7d)" value={data.total_queries} />
        <StatCard label="Queries (24h)" value={data.queries_24h} />
        <StatCard label="Avg LLM Latency" value={`${data.avg_llm_latency_ms}ms`} />
        <StatCard label="Total Documents" value={data.total_documents} />
        <StatCard label="Vector Chunks" value={data.total_vectors} />
        <StatCard label="Total Users" value={data.total_users} />
        <StatCard label="Employees" value={data.total_employees} />
        <StatCard label="Uploads (7d)" value={data.uploads_7d} />
        <div className="stat-card">
          <div className="stat-label">LLM Status</div>
          <div className={`stat-value ${data.llm_healthy ? "green" : "red"}`}>
            <span className={`health-dot ${data.llm_healthy ? "ok" : "err"}`} />
            {data.llm_healthy ? "Online" : "Offline"}
          </div>
        </div>
      </div>

      <div className="admin-grid">
        <div className="card">
          <div className="section-title">Daily Query Volume</div>
          {data.daily_queries?.length > 0 ? (
            <>
              <div className="bar-chart">
                {data.daily_queries.map((d) => (
                  <div
                    key={d.date}
                    className="bar"
                    style={{ height: `${Math.round((d.count / maxCount) * 76) + 4}px` }}
                    title={`${d.date}: ${d.count}`}
                  />
                ))}
              </div>
              <div style={{ display: "flex", gap: "4px" }}>
                {data.daily_queries.map((d) => (
                  <div key={d.date} className="bar-label" style={{ flex: 1 }}>
                    {d.date.slice(5)}
                  </div>
                ))}
              </div>
            </>
          ) : <p style={{ color: "#888", fontSize: "0.85rem" }}>No query data yet</p>}
        </div>

        <div className="card">
          <div className="section-title">Top Accessed Documents</div>
          {data.top_accessed_docs?.length > 0 ? (
            <table>
              <thead><tr><th>Document</th><th>Access Count</th></tr></thead>
              <tbody>
                {data.top_accessed_docs.map((d) => (
                  <tr key={d.document_id}>
                    <td>{d.title}</td>
                    <td>{d.access_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p style={{ color: "#888", fontSize: "0.85rem" }}>No accesses yet</p>}
        </div>

        <div className="card">
          <div className="section-title">Most Active Users</div>
          {data.active_users?.length > 0 ? (
            <table>
              <thead><tr><th>User</th><th>Queries</th></tr></thead>
              <tbody>
                {data.active_users.map((u) => (
                  <tr key={u.email}>
                    <td>{u.email}</td>
                    <td>{u.query_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p style={{ color: "#888", fontSize: "0.85rem" }}>No activity yet</p>}
        </div>
      </div>
    </>
  );
}

function Users() {
  const [users, setUsers] = useState([]);
  const [updating, setUpdating] = useState(null);

  useEffect(() => {
    adminApi.listUsers().then((r) => setUsers(r.data)).catch(() => {});
  }, []);

  const changeRole = async (userId, role) => {
    setUpdating(userId);
    try {
      await adminApi.updateRole(userId, role);
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role } : u));
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to update role");
    } finally {
      setUpdating(null);
    }
  };

  const RoleBadge = ({ role }) => {
    const cls = { admin: "badge-admin", employee: "badge-employee", user: "badge-user" };
    return <span className={`badge ${cls[role] || ""}`}>{role}</span>;
  };

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr><th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th>Change Role</th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.name}</td>
              <td>{u.email}</td>
              <td><RoleBadge role={u.role} /></td>
              <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
              <td>
                {u.role !== "admin" && (
                  <select
                    value={u.role}
                    onChange={(e) => changeRole(u.id, e.target.value)}
                    disabled={updating === u.id}
                    style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #ddd", fontSize: "0.82rem" }}
                  >
                    <option value="user">User</option>
                    <option value="employee">Employee</option>
                  </select>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");

  useEffect(() => {
    adminApi.getAuditLogs({ page, limit: 25, ...(actionFilter ? { action: actionFilter } : {}) })
      .then((r) => { setLogs(r.data.logs); setTotal(r.data.total); })
      .catch(() => {});
  }, [page, actionFilter]);

  const ACTIONS = ["", "login", "register", "chat_query", "document_upload", "document_delete", "role_change"];

  return (
    <>
      <div style={{ display: "flex", gap: "10px", marginBottom: "14px", alignItems: "center" }}>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "0.85rem" }}
        >
          {ACTIONS.map((a) => <option key={a} value={a}>{a || "All actions"}</option>)}
        </select>
        <span style={{ color: "#888", fontSize: "0.82rem" }}>{total} total events</span>
      </div>

      <div className="card" style={{ marginBottom: 0 }}>
        {logs.map((log, i) => (
          <div key={i} className="log-item">
            <div>
              <span className="log-action">{log.action}</span>
              &nbsp;·&nbsp;<strong>{log.user_email}</strong>
              &nbsp;·&nbsp;<span className={`badge badge-${log.role}`}>{log.role}</span>
            </div>
            <div className="log-meta">
              {log.timestamp}
              {log.title && ` · "${log.title}"`}
              {log.query && ` · Q: ${log.query.substring(0, 60)}...`}
              {log.latency_ms && ` · ${log.latency_ms}ms`}
              {log.new_role && ` · → ${log.new_role}`}
            </div>
          </div>
        ))}
        {logs.length === 0 && <p style={{ color: "#888", fontSize: "0.85rem" }}>No logs yet</p>}
      </div>

      <div style={{ display: "flex", gap: "8px", marginTop: "12px", alignItems: "center" }}>
        <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Previous</button>
        <span style={{ fontSize: "0.83rem", color: "#666" }}>Page {page} of {Math.ceil(total / 25) || 1}</span>
        <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(total / 25)}>Next</button>
      </div>
    </>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState("Overview");
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    if (tab === "Overview") {
      adminApi.getAnalytics().then((r) => setAnalytics(r.data)).catch(() => {});
    }
  }, [tab]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Admin Dashboard</h1>
      </div>
      <div className="tab-bar">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      {tab === "Overview" && <Overview data={analytics} />}
      {tab === "Users" && <Users />}
      {tab === "Audit Logs" && <AuditLogs />}
    </div>
  );
}
