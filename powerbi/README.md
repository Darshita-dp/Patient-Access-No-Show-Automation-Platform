# Power BI Executive Dashboard — Reporting-Layer Design

> **Scope:** Power BI implementation here is a **reporting-layer design and mock,
> not a completed `.pbix` file.** No `Patient_Access_Dashboard.pbix` exists in this
> repository. This folder delivers Power BI-ready KPI definitions, DAX measures,
> and dashboard layout documentation intended for future implementation.

To build the `.pbix`, open Power BI Desktop on a Windows machine and connect to the
PostgreSQL database (`etl/load_to_postgres.py` loads it; `sql/03_views.sql`
provides the reporting views). This folder contains the complete, buildable design
specification: data model, page layouts, visuals, and DAX measures — everything
needed to construct the dashboard. See `dashboard_design_spec.md`.

## Data model (import mode)

| Table | Source | Role |
|---|---|---|
| Appointments | `appointments` table / `vw_appointment_risk` | Fact |
| RiskScores | `risk_scores` | Fact |
| RecommendedActions | `recommended_actions` | Fact |
| AccessTasks | `access_tasks` | Fact |
| ReminderEvents | `reminder_events` | Fact |
| WaitlistRequests | `vw_waitlist_queue` | Fact |
| OpenSlots | `open_slots` | Fact |
| Patients | `patients` | Dimension |
| Providers | `providers` | Dimension |
| Clinics | `clinics` | Dimension |
| DateDim | `date_dim` | Date dimension (marked as date table) |

Relationships: single-direction star — `Appointments[patient_id] → Patients`,
`Appointments[provider_id] → Providers`, `Appointments[clinic_id] → Clinics`,
`Appointments[appointment_datetime] (date) → DateDim[full_date]`, and
`RiskScores/RecommendedActions/AccessTasks/ReminderEvents[appointment_id] →
Appointments`.

## Dashboard pages

1. **Executive Summary** — network KPIs and trend
2. **No-Show Risk Analysis** — risk drivers and the high-risk list
3. **Clinic Utilization** — capacity, leakage, recovery by clinic
4. **Provider Schedule Performance** — utilization ranking and gaps
5. **Waitlist & Access Gaps** — demand vs. open supply
6. **Staff Action Tracker** — outreach workload and completion
7. **Before / After Automation Impact** — simulated operational impact

Screenshot placeholders for each page are in `dashboard_screenshots/`
(rendered mock layouts generated from the same data the API serves).

## Core DAX measures

```dax
Total Appointments = COUNTROWS(Appointments)

Completed Appointments =
CALCULATE(COUNTROWS(Appointments), Appointments[appointment_status] = "Completed")

No Show Rate =
DIVIDE(
    CALCULATE(COUNTROWS(Appointments), Appointments[no_show_flag] = TRUE()),
    CALCULATE(COUNTROWS(Appointments),
        Appointments[appointment_status] IN {"Completed", "No-Show"})
)

Cancellation Rate =
DIVIDE(
    CALCULATE(COUNTROWS(Appointments), Appointments[appointment_status] = "Cancelled"),
    COUNTROWS(Appointments)
)

High Risk Appointments =
CALCULATE(COUNTROWS(RiskScores), RiskScores[risk_category] = "High")

Medium Risk Appointments =
CALCULATE(COUNTROWS(RiskScores), RiskScores[risk_category] = "Medium")

Low Risk Appointments =
CALCULATE(COUNTROWS(RiskScores), RiskScores[risk_category] = "Low")

Open Slot Count =
CALCULATE(COUNTROWS(OpenSlots), OpenSlots[slot_status] = "Open")

Recovered Slot Count =
CALCULATE(COUNTROWS(OpenSlots), OpenSlots[slot_status] = "Released (Cancellation)")

Available Appointment Slots =
SUMX(VALUES(Providers[provider_id]), Providers[daily_capacity] * 10)

Clinic Utilization =
DIVIDE([Completed Appointments], [Available Appointment Slots])

Average Lead Time = AVERAGE(Appointments[lead_time_days])

Average Waitlist Days = AVERAGE(WaitlistRequests[days_waiting])

Pending Outreach Tasks =
CALCULATE(COUNTROWS(AccessTasks), AccessTasks[task_status] IN {"Pending", "In Progress"})

Overdue Tasks =
CALCULATE(
    COUNTROWS(AccessTasks),
    AccessTasks[task_status] <> "Completed",
    AccessTasks[due_date] < TODAY()
)

Completed Tasks =
CALCULATE(COUNTROWS(AccessTasks), AccessTasks[task_status] = "Completed")

Action Completion Rate = DIVIDE([Completed Tasks], COUNTROWS(AccessTasks))

Reminder Completion Rate =
DIVIDE(
    CALCULATE(COUNTROWS(ReminderEvents), ReminderEvents[patient_response] = "Confirmed"),
    CALCULATE(COUNTROWS(ReminderEvents), ReminderEvents[delivery_status] = "Delivered")
)
```
