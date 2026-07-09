import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ErrorState, Loading, RiskBadge, StatusBadge, Toast, useApi, useToast,
} from "../components/ui";
import { api, fmtDate, fmtDateTime, pct } from "../services/api";

export default function AppointmentDetail() {
  const { id } = useParams();
  const { data, loading, error, reload } = useApi(
    () => api.appointmentDetail(id), [id]);
  const toast = useToast();
  const [notes, setNotes] = useState("");
  const [savedNotes, setSavedNotes] = useState([]);
  const [busy, setBusy] = useState(false);

  if (loading) return <Loading label="Loading appointment…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const { appointment: a, patient, risk_explanation, previous_behavior,
          reminder_history, waitlist_replacement, tasks } = data;

  const act = async (fn, msg) => {
    setBusy(true);
    try {
      await fn();
      toast.show(msg);
      reload();
    } catch (err) {
      toast.show(`Failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  const addNote = (e) => {
    e.preventDefault();
    if (!notes.trim()) return;
    setSavedNotes((n) => [
      { text: notes.trim(), at: new Date(), author: "Sandra Kim" }, ...n,
    ]);
    setNotes("");
    toast.show("Note added to the appointment record");
  };

  return (
    <div className="stack">
      <div className="card card-pad row between wrap">
        <div className="row" style={{ gap: 14 }}>
          <div>
            <div className="row" style={{ gap: 10 }}>
              <h2 style={{ margin: 0, fontSize: 17 }}>
                Appointment #{a.appointment_id}
              </h2>
              <RiskBadge category={a.risk_category} />
              <StatusBadge status={a.appointment_status} />
            </div>
            <div className="muted small" style={{ marginTop: 4 }}>
              {fmtDateTime(a.appointment_datetime)} · {a.clinic_name} ·{" "}
              {a.provider_name} · {a.appointment_type}
            </div>
          </div>
        </div>
        <div className="row wrap" style={{ gap: 8 }}>
          <button className="btn btn-outline" disabled={busy}
            onClick={() => act(() => api.sendReminder(a.appointment_id),
              "SMS reminder queued")}>
            Send Reminder
          </button>
          <button className="btn btn-success" disabled={busy}
            onClick={() => act(() => api.markContacted(a.appointment_id),
              "Patient marked as contacted")}>
            Mark Contacted
          </button>
          <Link className="btn btn-ghost" to="/queue">← Back to queue</Link>
        </div>
      </div>

      <div className="detail-grid">
        <div className="stack">
          <div className="card">
            <div className="card-head"><h3 className="card-title">Patient Summary</h3></div>
            <div className="card-pad">
              <dl className="kv">
                <dt>Name</dt><dd>{patient.patient_name}</dd>
                <dt>Patient ID</dt><dd>#{patient.patient_id}</dd>
                <dt>Age / Gender</dt><dd>{patient.age} · {patient.gender === "F" ? "Female" : "Male"}</dd>
                <dt>Neighborhood</dt><dd style={{ textTransform: "capitalize" }}>{patient.neighborhood.toLowerCase()}</dd>
                <dt>Conditions</dt>
                <dd>
                  {patient.conditions.length ? (
                    <div className="chip-list">
                      {patient.conditions.map((c) => (
                        <span key={c} className="badge neutral plain">{c}</span>
                      ))}
                    </div>
                  ) : "None on record"}
                </dd>
                {patient.mobility_support_level >= 2 && (
                  <>
                    <dt>Mobility</dt>
                    <dd><span className="badge medium plain">Transportation support may be needed</span></dd>
                  </>
                )}
              </dl>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h3 className="card-title">Previous Appointment Behavior</h3>
            </div>
            <div className="card-pad">
              <div className="row" style={{ gap: 20, marginBottom: 12 }}>
                <div>
                  <div className="kpi-value" style={{ fontSize: 20 }}>
                    {previous_behavior.total_visits}
                  </div>
                  <div className="kpi-note">Prior visits</div>
                </div>
                <div>
                  <div className="kpi-value" style={{ fontSize: 20, color: previous_behavior.no_shows ? "var(--red-600)" : "var(--green-600)" }}>
                    {previous_behavior.no_shows}
                  </div>
                  <div className="kpi-note">No-shows</div>
                </div>
                <div>
                  <div className="kpi-value" style={{ fontSize: 20 }}>
                    {previous_behavior.no_show_rate != null
                      ? pct(previous_behavior.no_show_rate) : "—"}
                  </div>
                  <div className="kpi-note">Personal no-show rate</div>
                </div>
              </div>
              {previous_behavior.recent_visits.length > 0 && (
                <table className="data">
                  <thead>
                    <tr><th>Date</th><th>Clinic</th><th>Outcome</th></tr>
                  </thead>
                  <tbody>
                    {previous_behavior.recent_visits.map((v) => (
                      <tr key={v.appointment_id}>
                        <td className="nowrap small">{fmtDate(v.appointment_datetime)}</td>
                        <td className="small">{v.clinic_name}</td>
                        <td><StatusBadge status={v.appointment_status === "No-Show" ? "Declined" : v.appointment_status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        <div className="stack">
          <div className="section-grid grid-1-1">
            <div className="card">
              <div className="card-head">
                <h3 className="card-title">Risk Explanation</h3>
              </div>
              <div className="card-pad">
                <p style={{ marginTop: 0, fontWeight: 600 }}>
                  {risk_explanation.summary}
                </p>
                <ul className="factor-list">
                  {risk_explanation.factors.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <h3 className="card-title">Recommended Action</h3>
              </div>
              <div className="card-pad">
                <div className="badge info plain" style={{ fontSize: 13, padding: "6px 12px" }}>
                  {a.recommended_action || "Monitor appointment"}
                </div>
                {tasks.length > 0 && (
                  <div style={{ marginTop: 14 }}>
                    <div className="small muted" style={{ marginBottom: 6 }}>Linked staff tasks</div>
                    {tasks.map((t) => (
                      <div key={t.task_id} className="row between" style={{ padding: "7px 0", borderTop: "1px solid var(--line)" }}>
                        <div>
                          <div className="cell-main small">{t.task_type}</div>
                          <div className="cell-sub">{t.assigned_to} · due {fmtDate(t.due_date)}</div>
                        </div>
                        <StatusBadge status={t.task_status} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="section-grid grid-1-1">
            <div className="card">
              <div className="card-head">
                <h3 className="card-title">Reminder History</h3>
              </div>
              <div className="card-pad">
                {reminder_history.length === 0 ? (
                  <div className="muted small">No reminders sent for this visit yet.</div>
                ) : (
                  <ul className="timeline">
                    {reminder_history.map((r) => (
                      <li key={r.reminder_id}>
                        <div className="cell-main small">
                          {r.reminder_type} · {fmtDateTime(r.sent_datetime)}
                        </div>
                        <div className="row" style={{ gap: 6, marginTop: 4 }}>
                          <StatusBadge status={r.delivery_status === "Failed" ? "Delivery Failed" : r.patient_response} />
                          <span className="cell-sub">{r.delivery_status}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">Waitlist Replacement Option</h3>
                  <div className="card-hint">If this slot releases, offer it to:</div>
                </div>
              </div>
              <div className="card-pad stack" style={{ gap: 10 }}>
                {!waitlist_replacement.available && (
                  <div className="muted small">
                    No eligible waitlist patients for this specialty and clinic.
                  </div>
                )}
                {waitlist_replacement.candidates.map((c, i) => (
                  <div key={c.waitlist_id} className={`match-card ${i === 0 ? "best" : ""}`}>
                    <div className="row between">
                      <div className="cell-main">{c.patient_name || `Waitlist #${c.waitlist_id}`}</div>
                      <span className="score-ring">{(c.match_score * 100).toFixed(0)}</span>
                    </div>
                    <div className="row wrap" style={{ gap: 6 }}>
                      <StatusBadge status={c.urgency_level === "Urgent" ? "Declined" : "Active"} />
                      <span className="badge neutral plain">{c.urgency_level}</span>
                      <span className="badge neutral plain">{c.days_waiting} days waiting</span>
                    </div>
                    <div className="small muted">{c.match_reason}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h3 className="card-title">Staff Notes</h3></div>
            <div className="card-pad">
              <form onSubmit={addNote} className="row" style={{ gap: 10 }}>
                <input className="grow" style={{
                  fontFamily: "inherit", fontSize: 13, padding: "9px 12px",
                  border: "1px solid var(--line)", borderRadius: 8,
                }}
                  placeholder="Add an outreach note (e.g., left voicemail, confirmed transport)…"
                  value={notes} onChange={(e) => setNotes(e.target.value)} />
                <button className="btn btn-primary" type="submit">Add Note</button>
              </form>
              {savedNotes.length > 0 && (
                <ul className="timeline" style={{ marginTop: 16 }}>
                  {savedNotes.map((n, i) => (
                    <li key={i}>
                      <div className="cell-main small">{n.author} · {n.at.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}</div>
                      <div className="small" style={{ marginTop: 3 }}>{n.text}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
      <Toast message={toast.message} />
    </div>
  );
}
