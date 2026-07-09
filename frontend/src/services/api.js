const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  dashboard: () => request("/dashboard/summary"),

  appointments: (params = {}) =>
    request(`/appointments?${new URLSearchParams(clean(params))}`),
  appointmentDetail: (id) => request(`/appointments/${id}`),
  searchAppointments: (params = {}) =>
    request(`/appointments/search?${new URLSearchParams(clean(params))}`),
  sendReminder: (id) =>
    request(`/appointments/${id}/send-reminder`, { method: "POST" }),
  markContacted: (id) =>
    request(`/appointments/${id}/mark-contacted`, { method: "POST" }),

  highRisk: (hours = 72) => request(`/risk/high?hours_ahead=${hours}`),
  riskSummary: () => request("/risk/summary"),

  waitlist: (params = {}) =>
    request(`/waitlist?${new URLSearchParams(clean(params))}`),
  waitlistSlots: (params = {}) =>
    request(`/waitlist/slots?${new URLSearchParams(clean(params))}`),
  waitlistMatches: (appointmentId) => request(`/waitlist/matches/${appointmentId}`),
  updateWaitlistStatus: (waitlistId, status) =>
    request(`/waitlist/${waitlistId}/status?status=${encodeURIComponent(status)}`, {
      method: "POST",
    }),

  providers: (params = {}) =>
    request(`/providers?${new URLSearchParams(clean(params))}`),
  providerSchedule: (id, params = {}) =>
    request(`/providers/${id}/schedule?${new URLSearchParams(clean(params))}`),

  clinics: () => request("/clinics"),
  clinicUtilization: () => request("/clinics/utilization"),

  tasks: (params = {}) => request(`/tasks?${new URLSearchParams(clean(params))}`),
  createTask: (body) =>
    request("/tasks", { method: "POST", body: JSON.stringify(body) }),
  completeTask: (id) => request(`/tasks/${id}/complete`, { method: "POST" }),
  updateTaskStatus: (id, status) =>
    request(`/tasks/${id}/status?status=${encodeURIComponent(status)}`, {
      method: "POST",
    }),
};

function clean(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  );
}

export function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

export function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short", month: "short", day: "numeric",
  });
}

export function fmtTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "numeric", minute: "2-digit",
  });
}

export function pct(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}
