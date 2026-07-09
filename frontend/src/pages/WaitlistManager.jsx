import { useState } from "react";
import {
  EmptyState, ErrorState, Loading, StatusBadge, Toast, useApi, useToast,
} from "../components/ui";
import { api, fmtDateTime } from "../services/api";

export default function WaitlistManager() {
  const [clinicId, setClinicId] = useState("");
  const [specialty, setSpecialty] = useState("");
  const toast = useToast();
  const [busy, setBusy] = useState(null);

  const clinics = useApi(() => api.clinics());
  const slots = useApi(
    () => api.waitlistSlots({ clinic_id: clinicId, specialty, limit: 30 }),
    [clinicId, specialty]
  );
  const queue = useApi(() => api.waitlist({ specialty }), [specialty]);

  const specialties = [...new Set(
    (queue.data?.waitlist || []).map((w) => w.requested_specialty)
  )].sort();

  const setStatus = async (waitlistId, status, message) => {
    setBusy(waitlistId);
    try {
      await api.updateWaitlistStatus(waitlistId, status);
      toast.show(message);
      slots.reload();
      queue.reload();
    } catch (err) {
      toast.show(`Failed: ${err.message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="stack">
      <div className="card card-pad">
        <div className="filter-bar">
          <div className="field">
            <label>Clinic</label>
            <select value={clinicId} onChange={(e) => setClinicId(e.target.value)}>
              <option value="">All clinics</option>
              {(clinics.data?.clinics || []).map((c) => (
                <option key={c.clinic_id} value={c.clinic_id}>{c.clinic_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Specialty</label>
            <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
              <option value="">All specialties</option>
              {specialties.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          {queue.data && (
            <div className="row" style={{ gap: 16, marginLeft: "auto" }}>
              <div>
                <div className="kpi-value" style={{ fontSize: 19 }}>{queue.data.count}</div>
                <div className="kpi-note">Active waitlist patients</div>
              </div>
              <div>
                <div className="kpi-value" style={{ fontSize: 19 }}>
                  {queue.data.average_days_waiting}
                </div>
                <div className="kpi-note">Avg days waiting</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">Open Slots & Recommended Patients</h3>
            <div className="card-hint">
              Each slot shows its top-ranked waitlist candidates. Scores weight urgency
              (35%), days waiting (25%), availability fit (20%), attendance likelihood
              (15%), and provider preference (5%).
            </div>
          </div>
        </div>

        {slots.loading && <Loading label="Matching open slots to the waitlist…" />}
        {slots.error && <ErrorState error={slots.error} onRetry={slots.reload} />}
        {slots.data && slots.data.slots.length === 0 && (
          <EmptyState title="No open slots in this view"
            message="Try another clinic or specialty, or widen the date window." />
        )}

        {slots.data && slots.data.slots.length > 0 && (
          <div className="card-pad stack" style={{ gap: 14 }}>
            {slots.data.slots.filter((s) => s.match_count > 0).map((s) => (
              <div key={s.slot_id} className="card card-pad" style={{ boxShadow: "none" }}>
                <div className="row between wrap" style={{ marginBottom: 10 }}>
                  <div>
                    <div className="cell-main">
                      {fmtDateTime(s.slot_datetime)} · {s.provider_name}
                    </div>
                    <div className="cell-sub">
                      {s.clinic_name} · {s.specialty}
                    </div>
                  </div>
                  <StatusBadge status={
                    s.slot_status === "Open" ? "Active" : "Reschedule Requested"} />
                </div>
                <div className="section-grid" style={{
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                }}>
                  {s.top_matches.map((m, i) => (
                    <div key={m.waitlist_id} className={`match-card ${i === 0 ? "best" : ""}`}>
                      <div className="row between">
                        <div>
                          <div className="cell-main">
                            {m.patient_name || `Waitlist #${m.waitlist_id}`}
                            {i === 0 && (
                              <span className="badge teal plain" style={{ marginLeft: 8 }}>
                                Recommended
                              </span>
                            )}
                          </div>
                          <div className="cell-sub">
                            {m.urgency_level} · waiting {m.days_waiting} days ·{" "}
                            {m.availability_window}
                          </div>
                        </div>
                        <span className="score-ring">
                          {(m.match_score * 100).toFixed(0)}
                        </span>
                      </div>
                      <div className="small muted">{m.match_reason}</div>
                      <div className="row wrap" style={{ gap: 6 }}>
                        <button className="btn btn-sm btn-primary" disabled={busy === m.waitlist_id}
                          onClick={() => setStatus(m.waitlist_id, "Offered",
                            `Slot offered to ${m.patient_name || "patient"}`)}>
                          Offer Slot
                        </button>
                        <button className="btn btn-sm btn-success" disabled={busy === m.waitlist_id}
                          onClick={() => setStatus(m.waitlist_id, "Accepted",
                            "Marked accepted — slot recovered")}>
                          Mark Accepted
                        </button>
                        <button className="btn btn-sm btn-outline" disabled={busy === m.waitlist_id}
                          onClick={() => setStatus(m.waitlist_id, "Declined",
                            "Marked declined")}>
                          Mark Declined
                        </button>
                        <button className="btn btn-sm btn-ghost" disabled={busy === m.waitlist_id}
                          onClick={() => setStatus(m.waitlist_id, "Contacted",
                            "Skipped — patient noted as contacted")}>
                          Skip
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h3 className="card-title">Waitlist Queue</h3>
          <span className="card-hint">Sorted by urgency, then wait time</span>
        </div>
        {queue.loading && <Loading />}
        {queue.error && <ErrorState error={queue.error} onRetry={queue.reload} />}
        {queue.data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Specialty</th>
                  <th>Preferred Clinic</th>
                  <th>Urgency</th>
                  <th>Days Waiting</th>
                  <th>Availability</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {queue.data.waitlist.slice(0, 40).map((w) => (
                  <tr key={w.waitlist_id}>
                    <td>
                      <div className="cell-main">{w.patient_name}</div>
                      <div className="cell-sub">Request #{w.waitlist_id}</div>
                    </td>
                    <td>{w.requested_specialty}</td>
                    <td className="small">{w.preferred_clinic || "Any"}</td>
                    <td>
                      <span className={`badge plain ${
                        w.urgency_level === "Urgent" ? "high"
                          : w.urgency_level === "Soon" ? "medium" : "neutral"}`}>
                        {w.urgency_level}
                      </span>
                    </td>
                    <td><strong>{w.days_waiting}</strong></td>
                    <td className="small">{w.availability_window}</td>
                    <td><StatusBadge status={w.waitlist_status} /></td>
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
