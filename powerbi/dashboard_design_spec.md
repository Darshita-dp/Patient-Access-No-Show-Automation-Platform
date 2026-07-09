# Power BI Dashboard — Page-by-Page Design Specification

Design language: white canvas, navy `#0B2540` headers, blue `#2A7FC9` primary
series, red `#C0504D` for risk/leakage, green `#1E7D46` for recovery/positive,
amber `#D9A441` for warnings. Cards use rounded corners and a light shadow to
match the React application.

Global slicers (synced across pages 1–6): **Date range**, **Clinic**,
**Specialty**.

---

## Page 1 — Executive Summary

**Audience:** clinic operations leaders, weekly review.

| Zone | Visual | Fields / Measure |
|---|---|---|
| KPI band (8 cards) | Card | Total Appointments · No Show Rate · Cancellation Rate · High Risk Appointments · Open Slot Count · Recovered Slot Count · Clinic Utilization · Pending Outreach Tasks |
| Left half | Line chart — *No-show trend by week* | DateDim[week_of_year] × No Show Rate |
| Right half | Bar chart — *No-show rate by clinic* | Clinics[clinic_name] × No Show Rate, network-average constant line |
| Bottom left | Bar chart — *Utilization by provider* (top/bottom 10) | Providers[provider_name] × Clinic Utilization |
| Bottom right | Column chart — *High-risk appointments by date* | DateDim[full_date] × High Risk Appointments |

---

## Page 2 — No-Show Risk Analysis

**Audience:** patient access manager; drives outreach targeting.

| Zone | Visual | Fields / Measure |
|---|---|---|
| Top left | Donut — *Risk category distribution* | RiskScores[risk_category] × count |
| Top middle | Column — *No-show rate by age group* | Patients[age] binned (0-12, 13-18, 19-30, 31-45, 46-60, 61-75, 76+) × No Show Rate |
| Top right | Column — *No-show rate by lead-time bucket* | Appointments[lead_time_days] binned (0, 1-3, 4-7, 8-14, 15-30, 30+) × No Show Rate |
| Middle left | Clustered bar — *No-show rate by SMS received* | Appointments[sms_received] × No Show Rate |
| Middle right | Bar — *Top risk drivers* | Static visual from `models/model_metrics.json` top_features (imported as a small table) |
| Bottom | Table — *High-risk appointment list* | appointment_datetime, patient, clinic, provider, no_show_probability, recommended_action; filtered risk_category = "High", sorted by probability desc |

---

## Page 3 — Clinic Utilization

| Zone | Visual | Fields / Measure |
|---|---|---|
| KPI band | Cards | Available Appointment Slots · Booked · Clinic Utilization · Open Slot Count · Recovered Slot Count |
| Main | Clustered column + line — *Utilization vs target by clinic* | Clinics[clinic_name] × Clinic Utilization, line = target_utilization |
| Left | Bar — *Open slots by clinic* | Clinics[clinic_name] × Open Slot Count |
| Right | Bar — *No-show leakage by clinic* | Clinics[clinic_name] × No Show Rate (historical) |
| Bottom | Matrix — *Recovered slot opportunity* | clinic × week: Recovered Slot Count vs slots with waitlist matches |

---

## Page 4 — Provider Schedule Performance

| Zone | Visual | Fields / Measure |
|---|---|---|
| Main | Bar — *Provider utilization ranking* | Providers[provider_name] × utilization, conditional color below 75% |
| Top right | Scatter — *Provider no-show rate vs volume* | x = appointment count, y = provider no-show rate, size = high-risk count |
| Middle | Column — *Appointments by provider* | provider × Total Appointments |
| Bottom left | Bar — *High-risk appointments by provider* | provider × High Risk Appointments |
| Bottom right | Matrix — *Schedule gaps* | provider × day: open slots per day, heat-scaled |

---

## Page 5 — Waitlist & Access Gaps

| Zone | Visual | Fields / Measure |
|---|---|---|
| KPI band | Cards | Active waitlist count · Average Waitlist Days · Urgent requests · Matched slots |
| Left | Bar — *Waitlist patients by specialty* | requested_specialty × count |
| Middle | Column — *Average days waiting by specialty* | requested_specialty × Average Waitlist Days |
| Right | Donut — *Urgency mix* | urgency_level × count |
| Bottom left | Table — *Open slots with available matches* | slot_datetime, clinic, specialty, match_count, best match score |
| Bottom right | Stacked column — *Matched vs unmatched slots by clinic* | clinic × slots (matched / unmatched) |

---

## Page 6 — Staff Action Tracker

| Zone | Visual | Fields / Measure |
|---|---|---|
| KPI band | Cards | Pending Outreach Tasks · Overdue Tasks · Completed Tasks · Action Completion Rate |
| Left | Column — *Tasks by priority* | priority × count, stacked by task_status |
| Middle | Bar — *Tasks completed by staff* | assigned_to × Completed Tasks |
| Right | Donut — *Task type mix* | task_type × count |
| Bottom | Table — *Overdue task list* | task_type, assigned_to, due_date, patient, risk_category; filtered Overdue |

---

## Page 7 — Before / After Automation Impact

> **Clearly labeled on-canvas:** *"Simulated operational impact based on
> synthetic workflow assumptions — not measured hospital results."*

| Metric | Before | After |
|---|---|---|
| No-show rate | 18.5% | 14.2% |
| Manual outreach hours/week | 22 | 9 |
| Recovered open slots/week | 4 | 17 |
| High-risk appointments contacted | 35% | 82% |
| Average waitlist days | 21 | 14 |

Visuals: KPI comparison cards (before grey, after blue), slope chart for the
five metrics, and a text panel explaining the assumed workflow changes
(automated risk scoring → targeted outreach → waitlist backfill).

Source table: `before_after_simulation.csv` in this folder.
