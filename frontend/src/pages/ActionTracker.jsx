import { useState } from "react";
import { Link } from "react-router-dom";
import {
  EmptyState, ErrorState, Loading, RiskBadge, StatusBadge, Toast, useApi,
  useToast,
} from "../components/ui";
import { api, fmtDate, pct } from "../services/api";

const TASK_TYPES = [
  "", "Call Patient", "Send Reminder", "Confirm Transportation",
  "Escalate Access Issue", "Review Provider Schedule",
];

export default function ActionTracker() {
  const [filters, setFilters] = useState({
    status: "", priority: "", assigned_to: "", task_type: "",
  });
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [busy, setBusy] = useState(null);
  const toast = useToast();

  const { data, loading, error, reload } = useApi(
    () => api.tasks({ ...filters, overdue_only: overdueOnly, limit: 120 }),
    [JSON.stringify(filters), overdueOnly]
  );

  const set = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));

  const act = async (taskId, fn, msg) => {
    setBusy(taskId);
    try {
      await fn();
      toast.show(msg);
      reload();
    } catch (err) {
      toast.show(`Failed: ${err.message}`);
    } finally {
      setBusy(null);
    }
  };

  const summary = data?.summary;
  const staffOptions = summary?.by_staff?.map((s) => s.assigned_to) || [];

  return (
    <div className="stack">
      {summary && (
        <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))" }}>
          <div className="kpi-card">
            <span className="kpi-label">Pending</span>
            <div className="kpi-value">{summary.pending}</div>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">In Progress</span>
            <div className="kpi-value">{summary.in_progress}</div>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Overdue</span>
            <div className="kpi-value" style={{ color: summary.overdue ? "var(--red-600)" : undefined }}>
              {summary.overdue}
            </div>
            {summary.overdue > 0 && <div className="kpi-note warn">Needs manager attention</div>}
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Completed</span>
            <div className="kpi-value" style={{ color: "var(--green-600)" }}>{summary.completed}</div>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Action Completion Rate</span>
            <div className="kpi-value">{pct(summary.completion_rate)}</div>
            <div className="kpi-note">Of all tasks created</div>
          </div>
        </div>
      )}

      <div className="section-grid grid-2-1">
        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">Task Board</h3>
              <div className="card-hint">Overdue and high-priority tasks float to the top</div>
            </div>
            <label className="row small" style={{ gap: 6, cursor: "pointer", fontWeight: 600 }}>
              <input type="checkbox" checked={overdueOnly}
                onChange={(e) => setOverdueOnly(e.target.checked)} />
              Overdue only
            </label>
          </div>

          <div className="card-pad" style={{ borderBottom: "1px solid var(--line)" }}>
            <div className="filter-bar">
              <div className="field">
                <label>Status</label>
                <select value={filters.status} onChange={set("status")}>
                  <option value="">All</option>
                  <option>Pending</option><option>In Progress</option><option>Completed</option>
                </select>
              </div>
              <div className="field">
                <label>Priority</label>
                <select value={filters.priority} onChange={set("priority")}>
                  <option value="">All</option>
                  <option>High</option><option>Medium</option><option>Low</option>
                </select>
              </div>
              <div className="field">
                <label>Task Type</label>
                <select value={filters.task_type} onChange={set("task_type")}>
                  {TASK_TYPES.map((t) => (
                    <option key={t} value={t}>{t || "All types"}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Assigned Staff</label>
                <select value={filters.assigned_to} onChange={set("assigned_to")}>
                  <option value="">Everyone</option>
                  {staffOptions.map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
            </div>
          </div>

          {loading && <Loading label="Loading task board…" />}
          {error && <ErrorState error={error} onRetry={reload} />}
          {data && data.tasks.length === 0 && (
            <EmptyState title="No tasks match"
              message="Adjust the filters or clear the overdue toggle." />
          )}

          {data && data.tasks.length > 0 && (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Priority</th>
                    <th>Assigned</th>
                    <th>Due</th>
                    <th>Appointment Risk</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.tasks.map((t) => (
                    <tr key={t.task_id} style={t.is_overdue ? { background: "#fdf6f5" } : undefined}>
                      <td>
                        <div className="cell-main">{t.task_type}</div>
                        <div className="cell-sub">
                          {t.patient_name
                            ? <>{t.patient_name} · {t.clinic_name}</>
                            : (t.context || "Operational review")}
                        </div>
                      </td>
                      <td>
                        <span className={`badge plain ${
                          t.priority === "High" ? "high"
                            : t.priority === "Medium" ? "medium" : "neutral"}`}>
                          {t.priority}
                        </span>
                      </td>
                      <td className="small">{t.assigned_to}</td>
                      <td className="nowrap">
                        <span className="small" style={t.is_overdue
                          ? { color: "var(--red-600)", fontWeight: 650 } : undefined}>
                          {fmtDate(t.due_date)}{t.is_overdue ? " · overdue" : ""}
                        </span>
                      </td>
                      <td>{t.risk_category ? <RiskBadge category={t.risk_category} /> : <span className="muted small">—</span>}</td>
                      <td><StatusBadge status={t.is_overdue && t.task_status !== "Completed" ? "Overdue" : t.task_status} /></td>
                      <td className="nowrap">
                        <div className="row" style={{ gap: 6 }}>
                          {t.task_status === "Pending" && (
                            <button className="btn btn-sm btn-outline" disabled={busy === t.task_id}
                              onClick={() => act(t.task_id,
                                () => api.updateTaskStatus(t.task_id, "In Progress"),
                                "Task started")}>
                              Start
                            </button>
                          )}
                          {t.task_status !== "Completed" && (
                            <button className="btn btn-sm btn-success" disabled={busy === t.task_id}
                              onClick={() => act(t.task_id,
                                () => api.completeTask(t.task_id),
                                "Task completed")}>
                              Complete
                            </button>
                          )}
                          {t.appointment_id && (
                            <Link className="btn btn-sm btn-ghost"
                              to={`/appointments/${t.appointment_id}`}>
                              Open
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card" style={{ alignSelf: "start" }}>
          <div className="card-head">
            <h3 className="card-title">Completion by Staff</h3>
          </div>
          <div className="card-pad stack" style={{ gap: 12 }}>
            {(summary?.by_staff || []).map((s) => {
              const rate = s.total ? s.completed / s.total : 0;
              return (
                <div key={s.assigned_to}>
                  <div className="row between small" style={{ marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{s.assigned_to}</span>
                    <span className="muted">{s.completed}/{s.total}</span>
                  </div>
                  <div className={`util-bar ${rate >= 0.3 ? "progress-good" : rate >= 0.15 ? "progress-mid" : "progress-low"}`}>
                    <span style={{ width: `${rate * 100}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <Toast message={toast.message} />
    </div>
  );
}
