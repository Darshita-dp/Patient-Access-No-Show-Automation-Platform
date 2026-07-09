import { useState } from "react";
import { Link } from "react-router-dom";
import { IconSearch } from "../components/Icons";
import {
  EmptyState, ErrorState, Loading, RiskBadge, StatusBadge, useApi,
} from "../components/ui";
import { api, fmtDateTime, pct } from "../services/api";

export default function SearchPage() {
  const [form, setForm] = useState({
    q: "", clinic_id: "", provider_id: "", date: "", risk_category: "",
  });
  const [query, setQuery] = useState(null);

  const clinics = useApi(() => api.clinics());
  const providers = useApi(() => api.providers());
  const results = useApi(
    () => (query ? api.searchAppointments(query) : Promise.resolve(null)),
    [JSON.stringify(query)]
  );

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const submit = (e) => {
    e.preventDefault();
    setQuery({ ...form });
  };

  return (
    <div className="stack">
      <div className="card card-pad">
        <form className="filter-bar" onSubmit={submit}>
          <div className="field grow">
            <label>Patient ID · Appointment ID · Patient Name</label>
            <div className="search-input">
              <IconSearch size={15} />
              <input placeholder="e.g. 5633033, 40190133335, or Synthetic Patient 03875"
                value={form.q} onChange={set("q")} style={{ width: "100%" }} />
            </div>
          </div>
          <div className="field">
            <label>Clinic</label>
            <select value={form.clinic_id} onChange={set("clinic_id")}>
              <option value="">Any clinic</option>
              {(clinics.data?.clinics || []).map((c) => (
                <option key={c.clinic_id} value={c.clinic_id}>{c.clinic_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Provider</label>
            <select value={form.provider_id} onChange={set("provider_id")}>
              <option value="">Any provider</option>
              {(providers.data?.providers || []).map((p) => (
                <option key={p.provider_id} value={p.provider_id}>{p.provider_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Date</label>
            <input type="date" value={form.date} onChange={set("date")} />
          </div>
          <div className="field">
            <label>Risk</label>
            <select value={form.risk_category} onChange={set("risk_category")}>
              <option value="">Any risk</option>
              <option>High</option><option>Medium</option><option>Low</option>
            </select>
          </div>
          <button className="btn btn-primary" type="submit">Search</button>
        </form>
      </div>

      <div className="card">
        <div className="card-head">
          <h3 className="card-title">
            {query
              ? `Results${results.data ? ` — ${results.data.count} found` : ""}`
              : "Search the schedule"}
          </h3>
        </div>

        {!query && (
          <EmptyState title="Find any patient or appointment"
            message="Search by patient ID, appointment ID, or name — or filter by clinic, provider, date, and risk category." />
        )}
        {query && results.loading && <Loading label="Searching…" />}
        {query && results.error && (
          <ErrorState error={results.error} onRetry={results.reload} />
        )}
        {query && results.data && results.data.count === 0 && (
          <EmptyState title="No matches"
            message="Check the ID or try a broader filter combination." />
        )}

        {query && results.data && results.data.count > 0 && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Appointment</th>
                  <th>Patient</th>
                  <th>Clinic / Provider</th>
                  <th>Status</th>
                  <th>Risk</th>
                  <th>Recommended Action</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {results.data.results.map((a) => (
                  <tr key={a.appointment_id}>
                    <td className="nowrap">
                      <div className="cell-main">{fmtDateTime(a.appointment_datetime)}</div>
                      <div className="cell-sub">#{a.appointment_id}</div>
                    </td>
                    <td>
                      <div className="cell-main">{a.patient_name}</div>
                      <div className="cell-sub">#{a.patient_id}</div>
                    </td>
                    <td>
                      <div className="cell-main">{a.clinic_name}</div>
                      <div className="cell-sub">{a.provider_name}</div>
                    </td>
                    <td><StatusBadge status={a.appointment_status} /></td>
                    <td>
                      <div className="row" style={{ gap: 7 }}>
                        <RiskBadge category={a.risk_category} />
                        {a.no_show_probability != null && (
                          <span className="small muted">{pct(a.no_show_probability)}</span>
                        )}
                      </div>
                    </td>
                    <td style={{ maxWidth: 220 }}>
                      <span className="small">{a.recommended_action || "—"}</span>
                    </td>
                    <td>
                      <Link className="btn btn-sm btn-primary"
                        to={`/appointments/${a.appointment_id}`}>
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
