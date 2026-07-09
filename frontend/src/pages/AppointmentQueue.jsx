import { useState } from "react";
import { Link } from "react-router-dom";
import {
  EmptyState, ErrorState, Loading, RiskBadge, StatusBadge, Toast, useApi,
  useToast,
} from "../components/ui";
import { api, fmtDateTime, pct } from "../services/api";

const RISK_OPTIONS = ["", "High", "Medium", "Low"];
const TASK_OPTIONS = ["", "Pending", "In Progress", "Completed", "No Task"];
const REMINDER_OPTIONS = [
  "", "Confirmed", "Sent — No Response", "Not Sent", "Delivery Failed",
  "Reschedule Requested",
];

export default function AppointmentQueue() {
  const [filters, setFilters] = useState({
    risk_category: "High", clinic_id: "", provider_id: "", date_from: "",
    date_to: "", task_status: "", reminder_status: "",
  });
  const [busyId, setBusyId] = useState(null);
  const toast = useToast();

  const clinics = useApi(() => api.clinics());
  const providers = useApi(() => api.providers());
  const { data, loading, error, reload } = useApi(
    () => api.appointments({ ...filters, sort: "risk", limit: 100 }),
    [JSON.stringify(filters)]
  );

  const set = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));

  const doAction = async (id, fn, message) => {
    setBusyId(id);
    try {
      await fn();
      toast.show(message);
      reload();
    } catch (err) {
      toast.show(`Failed: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="stack">
      <div className="card card-pad">
        <div className="filter-bar">
          <div className="field">
            <label>Risk Category</label>
            <select value={filters.risk_category} onChange={set("risk_category")}>
              {RISK_OPTIONS.map((o) => (
                <option key={o} value={o}>{o || "All risk levels"}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Clinic</label>
            <select value={filters.clinic_id} onChange={set("clinic_id")}>
              <option value="">All clinics</option>
              {(clinics.data?.clinics || []).map((c) => (
                <option key={c.clinic_id} value={c.clinic_id}>{c.clinic_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Provider</label>
            <select value={filters.provider_id} onChange={set("provider_id")}>
              <option value="">All providers</option>
              {(providers.data?.providers || []).map((p) => (
                <option key={p.provider_id} value={p.provider_id}>{p.provider_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>From</label>
            <input type="date" value={filters.date_from} onChange={set("date_from")} />
          </div>
          <div className="field">
            <label>To</label>
            <input type="date" value={filters.date_to} onChange={set("date_to")} />
          </div>
          <div className="field">
            <label>Task Status</label>
            <select value={filters.task_status} onChange={set("task_status")}>
              {TASK_OPTIONS.map((o) => (
                <option key={o} value={o}>{o || "All task statuses"}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Reminder Status</label>
            <select value={filters.reminder_status} onChange={set("reminder_status")}>
              {REMINDER_OPTIONS.map((o) => (
                <option key={o} value={o}>{o || "All reminder statuses"}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">
              Work Queue{data ? ` — ${data.total.toLocaleString()} appointments` : ""}
            </h3>
            <div className="card-hint">
              Sorted by access risk, then appointment time. Showing up to 100 rows.
            </div>
          </div>
        </div>

        {loading && <Loading label="Loading work queue…" />}
        {error && <ErrorState error={error} onRetry={reload} />}
        {data && data.appointments.length === 0 && (
          <EmptyState title="No appointments match these filters"
            message="Try widening the risk category or clearing the date range." />
        )}

        {data && data.appointments.length > 0 && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Appointment Time</th>
                  <th>Patient</th>
                  <th>Clinic / Provider</th>
                  <th>Risk Score</th>
                  <th>Risk Category</th>
                  <th>Recommended Action</th>
                  <th>Reminder</th>
                  <th>Task</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.appointments.map((a) => (
                  <tr key={a.appointment_id}>
                    <td className="nowrap">
                      <div className="cell-main">{fmtDateTime(a.appointment_datetime)}</div>
                      <div className="cell-sub">{a.appointment_type}</div>
                    </td>
                    <td>
                      <div className="cell-main">{a.patient_name}</div>
                      <div className="cell-sub">#{a.patient_id}</div>
                    </td>
                    <td>
                      <div className="cell-main">{a.clinic_name}</div>
                      <div className="cell-sub">{a.provider_name}</div>
                    </td>
                    <td><strong>{pct(a.no_show_probability)}</strong></td>
                    <td><RiskBadge category={a.risk_category} /></td>
                    <td style={{ maxWidth: 210 }}>
                      <span className="small">{a.recommended_action}</span>
                    </td>
                    <td><StatusBadge status={a.reminder_status} /></td>
                    <td><StatusBadge status={a.task_status} /></td>
                    <td className="nowrap">
                      <div className="row" style={{ gap: 6 }}>
                        <button className="btn btn-sm btn-outline"
                          disabled={busyId === a.appointment_id}
                          onClick={() => doAction(a.appointment_id,
                            () => api.sendReminder(a.appointment_id),
                            `Reminder sent for appointment ${a.appointment_id}`)}>
                          Send Reminder
                        </button>
                        {a.task_status ? (
                          <button className="btn btn-sm btn-outline"
                            disabled={busyId === a.appointment_id}
                            onClick={() => doAction(a.appointment_id,
                              () => api.markContacted(a.appointment_id),
                              "Patient marked as contacted")}>
                            Mark Contacted
                          </button>
                        ) : (
                          <button className="btn btn-sm btn-outline"
                            disabled={busyId === a.appointment_id}
                            onClick={() => doAction(a.appointment_id,
                              () => api.createTask({ appointment_id: a.appointment_id }),
                              "Follow-up task created")}>
                            Create Task
                          </button>
                        )}
                        <Link className="btn btn-sm btn-primary"
                          to={`/appointments/${a.appointment_id}`}>
                          View
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Toast message={toast.message} />
    </div>
  );
}
