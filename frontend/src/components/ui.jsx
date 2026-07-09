import { useEffect, useState } from "react";
import { IconAlert, IconSearch } from "./Icons";

export function RiskBadge({ category }) {
  if (!category) return <span className="badge neutral plain">Unscored</span>;
  const cls = category.toLowerCase();
  return <span className={`badge ${cls}`}>{category} Risk</span>;
}

export function StatusBadge({ status }) {
  if (!status) return <span className="badge neutral plain">No Task</span>;
  const map = {
    Completed: "low", "In Progress": "info", Pending: "neutral",
    Overdue: "high", Scheduled: "info", Cancelled: "high",
    Confirmed: "low", "Sent — No Response": "neutral",
    "Reschedule Requested": "medium", "Delivery Failed": "high",
    "Not Sent": "medium", Active: "info", Contacted: "teal",
    Offered: "medium", Accepted: "low", Declined: "high",
  };
  return <span className={`badge plain ${map[status] || "neutral"}`}>{status}</span>;
}

export function KpiCard({ label, value, note, noteTone, icon, iconBg, iconColor }) {
  return (
    <div className="kpi-card">
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        {icon && (
          <span className="kpi-icon" style={{ background: iconBg, color: iconColor }}>
            {icon}
          </span>
        )}
      </div>
      <div className="kpi-value">{value}</div>
      {note && <div className={`kpi-note ${noteTone || ""}`}>{note}</div>}
    </div>
  );
}

export function Loading({ label = "Loading data…" }) {
  return (
    <div className="state-block">
      <div className="spinner" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state-block">
      <div className="icon" style={{ background: "var(--red-050)", color: "var(--red-600)" }}>
        <IconAlert />
      </div>
      <h4>Could not load data</h4>
      <p>{String(error?.message || error)}</p>
      <p className="small" style={{ marginTop: 8 }}>
        Make sure the API is running: <code>uvicorn api.main:app --port 8000</code>
      </p>
      {onRetry && (
        <button className="btn btn-outline" style={{ marginTop: 14 }} onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title = "Nothing here", message }) {
  return (
    <div className="state-block">
      <div className="icon"><IconSearch /></div>
      <h4>{title}</h4>
      {message && <p>{message}</p>}
    </div>
  );
}

export function UtilBar({ value, target = 0.75 }) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  const tone = v >= target ? "progress-good" : v >= target - 0.1 ? "progress-mid" : "progress-low";
  return (
    <div className="row" style={{ gap: 8 }}>
      <div className={`util-bar grow ${tone}`}>
        <span style={{ width: `${v * 100}%` }} />
      </div>
      <span className="small" style={{ fontWeight: 650, minWidth: 36, textAlign: "right" }}>
        {(v * 100).toFixed(0)}%
      </span>
    </div>
  );
}

/** Small data-loading hook shared by every page. */
export function useApi(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    loader()
      .then((data) => alive && setState({ data, loading: false, error: null }))
      .catch((error) => alive && setState({ data: null, loading: false, error }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { ...state, reload: () => setTick((t) => t + 1) };
}

export function Toast({ message }) {
  if (!message) return null;
  return (
    <div style={{
      position: "fixed", bottom: 24, right: 24, zIndex: 100,
      background: "var(--navy-800)", color: "#fff",
      padding: "11px 18px", borderRadius: 10, fontSize: 13, fontWeight: 550,
      boxShadow: "0 8px 24px rgba(11,37,64,0.35)",
    }}>
      {message}
    </div>
  );
}

export function useToast() {
  const [message, setMessage] = useState(null);
  const show = (msg) => {
    setMessage(msg);
    window.clearTimeout(show._t);
    show._t = window.setTimeout(() => setMessage(null), 2600);
  };
  return { message, show };
}
