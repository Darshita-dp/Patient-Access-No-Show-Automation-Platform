import { Link } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from "recharts";
import {
  IconAlert, IconBell, IconCalendar, IconCheck, IconPhone, IconSlot,
  IconTasks, IconTrend, IconUser, IconWaitlist,
} from "../components/Icons";
import {
  ErrorState, KpiCard, Loading, RiskBadge, useApi,
} from "../components/ui";
import { api, fmtDateTime, pct } from "../services/api";

export default function CommandCenter() {
  const { data, loading, error, reload } = useApi(() => api.dashboard());

  if (loading) return <Loading label="Loading command center…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const { cards, high_risk_needing_action, open_slots_with_matches,
          utilization_trend, manager_alerts } = data;

  const trendData = utilization_trend.map((d) => ({
    day: new Date(d.day).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    Booked: d.booked,
    "High Risk": d.high_risk,
  }));

  return (
    <div className="stack">
      <div className="kpi-grid">
        <KpiCard label="Appointments Today" value={cards.appointments_today}
          icon={<IconCalendar />} iconBg="var(--blue-050)" iconColor="var(--blue-600)"
          note="Scheduled visits on today's calendar" />
        <KpiCard label="High-Risk Appointments" value={cards.high_risk_appointments}
          icon={<IconAlert />} iconBg="var(--red-050)" iconColor="var(--red-600)"
          note="Across the next 14 days" noteTone="warn" />
        <KpiCard label="No-Show Rate" value={pct(cards.no_show_rate, 1)}
          icon={<IconTrend />} iconBg="var(--amber-050)" iconColor="var(--amber-700)"
          note="Trailing historical baseline" />
        <KpiCard label="Open Slots" value={cards.open_slots}
          icon={<IconSlot />} iconBg="var(--teal-050)" iconColor="var(--teal-600)"
          note="Unbooked capacity, next 14 days" />
        <KpiCard label="Waitlist Patients" value={cards.waitlist_patients}
          icon={<IconWaitlist />} iconBg="var(--blue-050)" iconColor="var(--blue-600)"
          note="Active requests awaiting placement" />
        <KpiCard label="Provider Utilization" value={pct(cards.provider_utilization)}
          icon={<IconUser />} iconBg="var(--teal-050)" iconColor="var(--teal-600)"
          note="Network average, next two weeks" />
        <KpiCard label="Pending Staff Actions" value={cards.pending_staff_actions}
          icon={<IconTasks />} iconBg="var(--amber-050)" iconColor="var(--amber-700)"
          note="Outreach tasks awaiting completion" />
        <KpiCard label="Recovered Slots" value={cards.recovered_slots}
          icon={<IconCheck />} iconBg="var(--green-050)" iconColor="var(--green-600)"
          note="Cancellations with a waitlist match ready" noteTone="good" />
      </div>

      <div className="section-grid grid-2-1">
        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">High-Risk Appointments Needing Action</h3>
              <div className="card-hint">Next 48 hours · sorted by no-show probability</div>
            </div>
            <Link className="btn btn-ghost" to="/queue">Open work queue →</Link>
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Appointment</th>
                  <th>Patient</th>
                  <th>No-Show Probability</th>
                  <th>Recommended Action</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {high_risk_needing_action.map((a) => (
                  <tr key={a.appointment_id}>
                    <td className="nowrap">
                      <div className="cell-main">{fmtDateTime(a.appointment_datetime)}</div>
                      <div className="cell-sub">{a.clinic_name}</div>
                    </td>
                    <td>
                      <div className="cell-main">{a.patient_name}</div>
                      <div className="cell-sub">{a.provider_name}</div>
                    </td>
                    <td>
                      <div className="row" style={{ gap: 8 }}>
                        <strong>{pct(a.no_show_probability)}</strong>
                        <RiskBadge category={a.risk_category} />
                      </div>
                    </td>
                    <td style={{ maxWidth: 220 }}>
                      <span className="small">{a.recommended_action}</span>
                    </td>
                    <td>
                      <Link className="btn btn-sm btn-outline"
                        to={`/appointments/${a.appointment_id}`}>
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-head">
              <h3 className="card-title">Manager Alerts</h3>
            </div>
            <div className="card-pad stack" style={{ gap: 10 }}>
              {manager_alerts.length === 0 && (
                <div className="muted small">No active alerts — operations are on track.</div>
              )}
              {manager_alerts.map((a, i) => (
                <div className="alert-item" key={i}>
                  <span className={`alert-dot ${a.severity}`} />
                  <div>
                    <div className="alert-title">{a.title}</div>
                    <div className="alert-detail">{a.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="section-grid grid-1-1">
        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">Open Slots With Waitlist Matches</h3>
              <div className="card-hint">Released by cancellation · best candidate ready to offer</div>
            </div>
            <Link className="btn btn-ghost" to="/waitlist">Waitlist manager →</Link>
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Provider</th>
                  <th>Match Score</th>
                </tr>
              </thead>
              <tbody>
                {open_slots_with_matches.map((s) => (
                  <tr key={s.slot_id}>
                    <td className="nowrap">
                      <div className="cell-main">{fmtDateTime(s.slot_datetime)}</div>
                      <div className="cell-sub">{s.clinic_name}</div>
                    </td>
                    <td>
                      <div className="cell-main">{s.provider_name}</div>
                      <div className="cell-sub">{s.specialty}</div>
                    </td>
                    <td>
                      {s.match_score != null ? (
                        <span className="badge teal plain">
                          {(s.match_score * 100).toFixed(0)} match
                        </span>
                      ) : (
                        <span className="muted small">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">Schedule & Risk — Next 14 Days</h3>
              <div className="card-hint">Booked appointments and the high-risk share per day</div>
            </div>
          </div>
          <div className="card-pad">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={trendData} barGap={2}>
                <CartesianGrid vertical={false} stroke="#eef2f6" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={34} />
                <Tooltip cursor={{ fill: "rgba(42,127,201,0.06)" }}
                  contentStyle={{ borderRadius: 10, border: "1px solid var(--line)", fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Booked" fill="#2a7fc9" radius={[4, 4, 0, 0]} />
                <Bar dataKey="High Risk" fill="#c0504d" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
