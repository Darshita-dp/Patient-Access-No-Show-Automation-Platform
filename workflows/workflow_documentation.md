# Workflow Automation Documentation

> **Scope — read first.** This document is a **Power Automate-style workflow
> specification and simulation**, written for future Microsoft 365
> implementation. **No live Power Automate cloud flow is deployed, and there is
> no live SharePoint list, Outlook, Teams, or SMS integration in this version.**
> No Microsoft 365 tenant is connected. The outreach loop is **simulated using
> local API state transitions** (reminder sent → task created → task completed
> or escalated), and the SharePoint list is a **static CSV mock** exported from
> the platform's own task data. The connector tables below are implementation
> sketches, not configured flows.

The platform's decision chain — **prediction → risk category → recommended
action → staff task → waitlist match → manager dashboard** — is designed to be
automated with Power Automate and SharePoint in a Microsoft-shop clinic
environment. This document specifies the flows; the repository simulates their
outputs (`data/processed/access_tasks.csv` and the mock SharePoint list) so
the full experience is demonstrable without an M365 tenant.

## Flow 1 — High-Risk Appointment Outreach (primary)

See [high_risk_outreach_workflow.md](high_risk_outreach_workflow.md) for the
full diagram, trigger, condition, and the four actions (send reminder, create
follow-up task, update SharePoint, escalate to manager at 24h).

**Power Automate implementation sketch**

| Step | Connector | Configuration |
|---|---|---|
| Trigger | SQL Server / PostgreSQL (via gateway) | "When an item is created or modified" on `risk_scores`, filter `risk_category eq 'High'` |
| Condition | Built-in | `appointment_datetime <= addHours(utcNow(), 72)` |
| Send SMS | Twilio / Azure Communication Services | Templated reminder with confirm link |
| Create task | SharePoint — Create item | List: *Patient Access Tasks* (columns below) |
| Escalation | Scheduled child flow (recurrence: 1h) | Items where `Status ne 'Completed'` and `Created <= addHours(utcNow(), -24)` → set `Escalation Flag`, post Teams message to manager |

## Flow 2 — Cancelled Slot → Waitlist Offer

| Step | Configuration |
|---|---|
| Trigger | `appointments.appointment_status` changes to `Cancelled` |
| Action 1 | Call platform API `GET /waitlist/matches/{appointment_id}` for ranked candidates |
| Action 2 | Create *Offer Waitlist Slot* task for the top candidate (SharePoint) |
| Action 3 | If declined, advance to the next-ranked candidate (max 3 attempts) |
| Action 4 | On acceptance, book the slot and mark the waitlist request `Accepted` |

## Flow 3 — Daily Operations Digest

Recurrence 7:00 AM weekdays: pull `/dashboard/summary`, post an adaptive card
to the scheduling team's channel with appointments today, high-risk count,
open slots, overdue tasks, and a deep link into the Command Center.

## Mock SharePoint task list

`sharepoint_task_list_mock.csv` contains a real extract of the platform's
generated tasks in the exact column shape the SharePoint list would use:

| Column | Type | Notes |
|---|---|---|
| Task ID | Number | Platform task_id |
| Appointment ID | Number | Link back to the appointment |
| Patient ID | Number | Synthetic identifier |
| Risk Category | Choice | High / Medium / Low |
| Recommended Action | Text | From the action engine |
| Assigned Staff | Person | Coordinator rotation |
| Due Date | Date | Day before the visit |
| Status | Choice | Pending / In Progress / Completed |
| Escalation Flag | Yes/No | Set by the 24-hour escalation flow |

## Simulation boundary

No live SMS, Teams, or SharePoint calls are made in this repository. The
FastAPI endpoints (`POST /appointments/{id}/send-reminder`,
`POST /tasks/{id}/complete`) mutate the in-memory store to demonstrate the
same state transitions the flows would drive.
