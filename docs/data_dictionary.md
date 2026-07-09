# Data Dictionary

Sources: **K** = Kaggle Medical Appointment No Shows schema (or synthetic
fallback with identical columns), **S** = synthetic operational data,
**E** = engineered by ETL, **M** = model/engine output.

## appointments (`data/synthetic/appointments_full.csv` → `appointments`)

| Column | Type | Src | Description |
|---|---|---|---|
| appointment_id | BIGINT | K | Unique visit identifier (PK) |
| patient_id | BIGINT | K | Patient identifier (FK patients) |
| provider_id | INT | S | Rendering provider (FK providers) |
| clinic_id | INT | S | Clinic site (FK clinics) |
| scheduled_datetime | TIMESTAMP | K | When the booking was made |
| appointment_datetime | TIMESTAMP | K/S | When the visit occurs (time-of-day assigned synthetically; Kaggle is day-only) |
| appointment_status | VARCHAR | S | Completed · No-Show · Scheduled · Cancelled |
| no_show_flag | BOOLEAN | K | Outcome (NULL for future visits) |
| sms_received | BOOLEAN | K | Whether an SMS reminder was sent |
| lead_time_days | INT | E | Days between booking and visit |
| appointment_type | VARCHAR | S | Follow-up · New Patient · Annual Physical · Procedure · Telehealth |
| specialty | VARCHAR | S | Provider specialty at booking |
| appointment_hour | INT | E | Visit hour (clinic hours 8–17) |
| appointment_day_of_week / scheduled_day_of_week | VARCHAR | E | Day names |
| appointment_month | INT | E | Calendar month |
| is_weekend | BOOLEAN | E | Weekend visit flag |

## patients (`data/synthetic/patients.csv`)

| Column | Type | Src | Description |
|---|---|---|---|
| patient_id | BIGINT | K | PK |
| patient_name | VARCHAR | S | Synthetic display name ("Synthetic Patient NNNNN" — never real PHI) |
| gender | VARCHAR | K | F / M |
| age | INT | K | Age at latest visit (0–100 after cleaning) |
| neighborhood | VARCHAR | K | Residential neighbourhood |
| scholarship_flag | BOOLEAN | K | Social-program enrollment (Bolsa Família) |
| hypertension_flag / diabetes_flag / alcoholism_flag | BOOLEAN | K | Condition flags |
| handicap_flag | INT | K | Mobility/support level 0–4 |

## providers (`data/synthetic/providers.csv`)

provider_id (PK) · provider_name · clinic_id (FK) · specialty ·
daily_capacity (slots/day, 12–16).

## clinics (`data/synthetic/clinics.csv`)

clinic_id (PK) · clinic_name · location · service_line · target_utilization
(e.g., 0.85).

## waitlist_requests (`data/synthetic/waitlist_requests.csv`)

| Column | Description |
|---|---|
| waitlist_id | PK |
| patient_id | FK patients |
| requested_specialty | Specialty needed |
| preferred_clinic_id / preferred_provider_id | Optional preferences |
| requested_date | When the request was filed (drives days_waiting) |
| urgency_level | Routine · Soon · Urgent |
| availability_window | e.g., "Weekday mornings", "Tue/Thu only" |
| waitlist_status | Active · Contacted · Offered · Accepted · Declined · Scheduled Elsewhere |

## reminder_events (`data/synthetic/reminder_events.csv`)

reminder_id (PK) · appointment_id (FK) · reminder_type (SMS) · sent_datetime ·
delivery_status (Delivered/Failed) · patient_response (Confirmed · No
Response · Reschedule Requested · Declined).

## open_slots (`data/synthetic/open_slots.csv`)

slot_id (PK) · slot_datetime · provider_id · clinic_id · specialty ·
slot_status (Open · Released (Cancellation)).

## Model & engine outputs (`data/processed/`)

| File | Grain | Key columns |
|---|---|---|
| risk_scores.csv | 1/scored appointment | no_show_probability (0–1), risk_category (Low/Medium/High), model_version, scored_at |
| recommended_actions.csv | 1/scored appointment | recommended_action, action_reason, priority |
| access_tasks.csv | 1/staff work item | task_type, priority, assigned_to, due_date, task_status, completed_date, context |
| waitlist_match_results.csv | top-3/open slot | slot_id, waitlist_id, match_rank, match_score (0–1), match_reason |

## Engineered model features (`data/processed/appointments_features.csv`)

| Feature | Definition |
|---|---|
| patient_previous_appointments | Count of this patient's visits strictly before this one |
| patient_previous_no_shows | Of those, how many were missed |
| patient_no_show_rate | previous_no_shows ÷ previous_appointments (global rate when no history) |
| clinic_no_show_rate / provider_no_show_rate | Expanding historical rate, smoothed with 20 pseudo-observations, excluding the current row |
| reminder_count | Reminders sent for this appointment |
| last_reminder_hours_before_appt | Hours between the last reminder and the visit |

**Leakage rule:** every history feature uses only appointments that occurred
before the appointment being scored.

## staff_users / date_dim

`staff_users`: staff_id · staff_name · role (coordinators, specialists,
manager). `date_dim`: date_key (YYYYMMDD) · full_date · year · month ·
month_name · week_of_year · day_of_week · is_weekend — reporting dimension
for Power BI.
