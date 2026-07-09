import { useState } from "react";
import { Link } from "react-router-dom";
import {
  EmptyState, ErrorState, Loading, RiskBadge, StatusBadge, UtilBar, useApi,
} from "../components/ui";
import { api, fmtTime, pct } from "../services/api";

export default function ProviderSchedule() {
  const providers = useApi(() => api.providers());
  const [providerId, setProviderId] = useState(null);
  const [dayIndex, setDayIndex] = useState(0);

  const activeId = providerId
    || providers.data?.providers?.[0]?.provider_id
    || null;

  const schedule = useApi(
    () => (activeId ? api.providerSchedule(activeId, { days: 5 })
                    : Promise.resolve(null)),
    [activeId]
  );

  if (providers.loading) return <Loading label="Loading providers…" />;
  if (providers.error) {
    return <ErrorState error={providers.error} onRetry={providers.reload} />;
  }

  const list = providers.data.providers;
  const sched = schedule.data;
  const day = sched?.days?.[dayIndex];

  return (
    <div className="section-grid" style={{ gridTemplateColumns: "300px 1fr", alignItems: "start" }}>
      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">Providers</h3>
            <div className="card-hint">Sorted by utilization — lowest first</div>
          </div>
        </div>
        <div style={{ maxHeight: "72vh", overflowY: "auto" }}>
          {list.map((p) => (
            <button key={p.provider_id}
              onClick={() => { setProviderId(p.provider_id); setDayIndex(0); }}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "12px 16px", background:
                  p.provider_id === activeId ? "var(--blue-050)" : "transparent",
                border: "none", borderBottom: "1px solid var(--line)",
                cursor: "pointer", fontFamily: "inherit",
                borderLeft: p.provider_id === activeId
                  ? "3px solid var(--blue-600)" : "3px solid transparent",
              }}>
              <div className="row between">
                <div>
                  <div className="cell-main">{p.provider_name}</div>
                  <div className="cell-sub">{p.specialty} · {p.clinic_name}</div>
                </div>
                {p.high_risk > 0 && (
                  <span className="badge high plain">{p.high_risk} HR</span>
                )}
              </div>
              <div style={{ marginTop: 8 }}>
                <UtilBar value={p.utilization_rate} />
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="stack">
        {schedule.loading && <Loading label="Loading schedule…" />}
        {schedule.error && <ErrorState error={schedule.error} onRetry={schedule.reload} />}

        {sched && (
          <>
            <div className="card card-pad">
              <div className="row between wrap">
                <div>
                  <h2 style={{ margin: 0, fontSize: 17 }}>
                    {sched.provider.provider_name}
                  </h2>
                  <div className="muted small" style={{ marginTop: 3 }}>
                    {sched.provider.specialty} · {sched.provider.clinic_name} ·{" "}
                    {sched.provider.daily_capacity} slots/day
                  </div>
                </div>
                <div className="day-tabs">
                  {sched.days.map((d, i) => (
                    <button key={d.date} className={`day-tab ${i === dayIndex ? "active" : ""}`}
                      onClick={() => setDayIndex(i)}>
                      <span className="d">{d.day_of_week.slice(0, 3)}</span>
                      {new Date(d.date + "T00:00:00").toLocaleDateString(undefined, {
                        month: "short", day: "numeric" })}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {day && (
              <>
                <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))" }}>
                  <div className="kpi-card">
                    <span className="kpi-label">Booked</span>
                    <div className="kpi-value">{day.booked}<span className="muted" style={{ fontSize: 14 }}> / {day.capacity}</span></div>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-label">Utilization</span>
                    <div className="kpi-value">{day.utilization_rate != null ? pct(day.utilization_rate) : "—"}</div>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-label">High-Risk Visits</span>
                    <div className="kpi-value" style={{ color: day.high_risk_appointments ? "var(--red-600)" : undefined }}>
                      {day.high_risk_appointments}
                    </div>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-label">Open Slots</span>
                    <div className="kpi-value">{day.open_slots}</div>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-label">Released (Cancelled)</span>
                    <div className="kpi-value">{day.released_slots + day.cancelled}</div>
                  </div>
                </div>

                <div className="card card-pad" style={{
                  background: "var(--blue-050)", border: "1px solid #cfe3f5",
                }}>
                  <span className="small" style={{ fontWeight: 600, color: "var(--navy-800)" }}>
                    Manager insight: {day.insight}
                    {day.open_slots + day.released_slots > 0 &&
                      " Open capacity can be offered to waitlist patients."}
                    {day.utilization_rate >= 0.95 &&
                      ` High fill with ${day.high_risk_appointments} high-risk bookings — review overbook exposure if all patients attend.`}
                  </span>
                </div>

                <div className="card">
                  <div className="card-head">
                    <h3 className="card-title">
                      Day Schedule — {new Date(day.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
                    </h3>
                    <div className="legend">
                      <span><i style={{ background: "#2a7fc9" }} /> Booked</span>
                      <span><i style={{ background: "#c0504d" }} /> High risk</span>
                      <span><i style={{ background: "#b7c4d0" }} /> Cancelled</span>
                    </div>
                  </div>
                  {day.appointments.length === 0 ? (
                    <EmptyState title="No appointments this day"
                      message="The full day is open capacity." />
                  ) : (
                    <div className="table-wrap">
                      <table className="data">
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>Patient</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>No-Show Probability</th>
                            <th>Reminder</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {day.appointments.map((a) => (
                            <tr key={a.appointment_id}>
                              <td className="nowrap cell-main">{fmtTime(a.appointment_datetime)}</td>
                              <td>{a.patient_name}</td>
                              <td className="small">{a.appointment_type}</td>
                              <td><StatusBadge status={a.appointment_status} /></td>
                              <td>
                                <div className="row" style={{ gap: 7 }}>
                                  {a.no_show_probability != null && (
                                    <strong>{pct(a.no_show_probability)}</strong>
                                  )}
                                  <RiskBadge category={a.risk_category} />
                                </div>
                              </td>
                              <td><StatusBadge status={a.reminder_status} /></td>
                              <td>
                                <Link className="btn btn-sm btn-outline"
                                  to={`/appointments/${a.appointment_id}`}>
                                  View
                                </Link>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
