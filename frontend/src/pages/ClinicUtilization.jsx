import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { ErrorState, Loading, useApi } from "../components/ui";
import { api, pct } from "../services/api";

export default function ClinicUtilization() {
  const { data, loading, error, reload } = useApi(() => api.clinicUtilization());

  if (loading) return <Loading label="Calculating clinic utilization…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const clinics = data.clinics;
  const chart = clinics.map((c) => ({
    name: c.clinic_name.replace(/ (Center|Medicine|Care|& \w+)$/g, ""),
    Utilization: +(c.utilization_rate * 100).toFixed(1),
    Potential: +(c.potential_utilization * 100).toFixed(1),
    target: c.target_utilization * 100,
  }));

  const totals = clinics.reduce((acc, c) => ({
    slots: acc.slots + c.available_slots,
    booked: acc.booked + c.booked_appointments,
    open: acc.open + c.open_slots,
    recoverable: acc.recoverable + c.recoverable_slots,
    cancelled: acc.cancelled + c.cancelled_appointments,
  }), { slots: 0, booked: 0, open: 0, recoverable: 0, cancelled: 0 });

  return (
    <div className="stack">
      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Scheduled Capacity</span>
          <div className="kpi-value">{totals.slots.toLocaleString()}</div>
          <div className="kpi-note">Appointment slots, next 14 days</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Booked Appointments</span>
          <div className="kpi-value">{totals.booked.toLocaleString()}</div>
          <div className="kpi-note">{pct(totals.booked / totals.slots)} of capacity</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Open Slots</span>
          <div className="kpi-value">{totals.open.toLocaleString()}</div>
          <div className="kpi-note">Unbooked and offerable</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Cancelled Visits</span>
          <div className="kpi-value">{totals.cancelled.toLocaleString()}</div>
          <div className="kpi-note">Upcoming window</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Recoverable Slots</span>
          <div className="kpi-value" style={{ color: "var(--green-600)" }}>
            {totals.recoverable.toLocaleString()}
          </div>
          <div className="kpi-note good">Cancellations with waitlist match ready</div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">Utilization vs. Potential by Clinic</h3>
            <div className="card-hint">
              Utilization = booked ÷ available slots. Potential adds recoverable
              cancelled slots that have a waitlist match.
            </div>
          </div>
        </div>
        <div className="card-pad">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chart} barGap={3}>
              <CartesianGrid vertical={false} stroke="#eef2f6" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false}
                tickLine={false} interval={0} />
              <YAxis unit="%" tick={{ fontSize: 11 }} axisLine={false}
                tickLine={false} width={40} domain={[0, 100]} />
              <Tooltip formatter={(v) => `${v}%`}
                contentStyle={{ borderRadius: 10, border: "1px solid var(--line)", fontSize: 12 }} />
              <ReferenceLine y={80} stroke="#9aa8b7" strokeDasharray="5 4"
                label={{ value: "Target 80%", fontSize: 11, fill: "#64748b", position: "insideTopRight" }} />
              <Bar dataKey="Utilization" radius={[4, 4, 0, 0]}>
                {chart.map((c, i) => (
                  <Cell key={i} fill={c.Utilization >= c.target ? "#1e7d46" : "#2a7fc9"} />
                ))}
              </Bar>
              <Bar dataKey="Potential" fill="#8fc1e8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3 className="card-title">Clinic Scorecard</h3>
          <span className="card-hint">Next 14 days · historical leakage for context</span>
        </div>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Clinic</th>
                <th>Capacity</th>
                <th>Booked</th>
                <th>Open Slots</th>
                <th>Cancelled</th>
                <th>Recoverable</th>
                <th>High Risk</th>
                <th>Historical No-Show</th>
                <th style={{ minWidth: 170 }}>Utilization vs Target</th>
              </tr>
            </thead>
            <tbody>
              {clinics.map((c) => (
                <tr key={c.clinic_id}>
                  <td>
                    <div className="cell-main">{c.clinic_name}</div>
                    <div className="cell-sub">{c.service_line} · target {pct(c.target_utilization)}</div>
                  </td>
                  <td>{c.available_slots.toLocaleString()}</td>
                  <td>{c.booked_appointments.toLocaleString()}</td>
                  <td>{c.open_slots}</td>
                  <td>{c.cancelled_appointments}</td>
                  <td style={{ color: "var(--green-600)", fontWeight: 650 }}>
                    {c.recoverable_slots}
                  </td>
                  <td>
                    <span className={`badge plain ${c.high_risk_appointments > 150 ? "high" : "neutral"}`}>
                      {c.high_risk_appointments}
                    </span>
                  </td>
                  <td>
                    <span className={`badge plain ${
                      c.historical_no_show_rate > 0.21 ? "high"
                        : c.historical_no_show_rate > 0.19 ? "medium" : "low"}`}>
                      {pct(c.historical_no_show_rate, 1)}
                    </span>
                  </td>
                  <td>
                    <div className="row" style={{ flexDirection: "column", alignItems: "stretch", gap: 4 }}>
                      <UtilizationRow value={c.utilization_rate} target={c.target_utilization} />
                      <span className="cell-sub">
                        potential {pct(c.potential_utilization)} with slot recovery
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function UtilizationRow({ value, target }) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  const tone = v >= target ? "progress-good" : v >= target - 0.08 ? "progress-mid" : "progress-low";
  return (
    <div className="row" style={{ gap: 8 }}>
      <div className={`util-bar grow ${tone}`}>
        <span style={{ width: `${v * 100}%` }} />
      </div>
      <span className="small" style={{ fontWeight: 650 }}>{(v * 100).toFixed(0)}%</span>
    </div>
  );
}
