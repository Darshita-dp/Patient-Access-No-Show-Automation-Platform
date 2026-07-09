# High-Risk Appointment Outreach Workflow

This workflow simulates how a patient access team could automate outreach and
escalation for high-risk appointments using Power Automate + SharePoint on top
of the platform's risk scores.

```mermaid
flowchart TD
    A["Trigger:<br/>Appointment scored HIGH RISK<br/>(risk_scores insert/update)"] --> B{"Appointment within<br/>next 72 hours?"}
    B -->|No| C["Queue for daily re-evaluation<br/>(re-enters when inside 72h window)"]
    B -->|Yes| D["Action 1:<br/>Send SMS reminder to patient"]
    D --> E["Action 2:<br/>Create staff follow-up task<br/>(assigned by rotation)"]
    E --> F["Action 3:<br/>Add row to SharePoint task list<br/>with risk + recommended action"]
    F --> G{"Task completed<br/>within 24 hours?"}
    G -->|Yes| H["Mark task complete<br/>Log outreach outcome"]
    G -->|No| I["Action 4:<br/>Notify scheduling manager<br/>(Teams message + escalation flag)"]
    I --> J["Manager reassigns or<br/>calls patient directly"]
    H --> K{"Patient confirmed?"}
    J --> K
    K -->|Yes| L["Keep appointment<br/>Update reminder status"]
    K -->|No / Cancels| M["Release slot"]
    M --> N["Waitlist matching engine<br/>ranks replacement candidates"]
    N --> O["Offer slot to top waitlist patient"]
    O --> P["Update manager dashboard KPIs"]
```

## Trigger

| Property | Value |
|---|---|
| Trigger | When an appointment is scored as **High Risk** |
| Source | `risk_scores` table (new/changed row, `risk_category = 'High'`) |
| Frequency | Near-real-time (on scoring run), plus daily 6:00 AM sweep |

## Condition

Appointment date is within the **next 72 hours** (`appointment_datetime <=
utcNow() + 72h`). High-risk visits outside the window re-enter the flow when
they cross into it.

## Actions

1. **Send reminder message** — SMS to the patient with confirm / reschedule
   options; response is written back to `reminder_events`.
2. **Create staff follow-up task** — task type from the recommended-action
   engine (Call Patient / Send Reminder / Confirm Transportation / Escalate),
   assigned round-robin to patient access coordinators.
3. **Update SharePoint task list** — one row per task (see
   `sharepoint_task_list_mock.csv`) so the access team works from a familiar
   surface.
4. **Notify scheduling manager if not completed within 24 hours** — an
   escalation flag is set and the manager is notified with the appointment's
   risk context.
