-- ============================================================================
-- 04_kpi_queries.sql — operational KPI queries
-- These are the numbers the Command Center cards and the Power BI executive
-- page report. Each query is self-contained.
-- ============================================================================

-- 1. Overall no-show rate (historical outcomes only)
SELECT ROUND(AVG(CASE WHEN no_show_flag THEN 1 ELSE 0 END)::NUMERIC, 4) AS no_show_rate
FROM appointments
WHERE appointment_status IN ('Completed', 'No-Show');

-- 2. Cancellation rate on upcoming schedule
SELECT ROUND(
    COUNT(*) FILTER (WHERE appointment_status = 'Cancelled')::NUMERIC
    / NULLIF(COUNT(*), 0), 4) AS cancellation_rate
FROM appointments
WHERE appointment_datetime >= CURRENT_DATE;

-- 3. Appointments today
SELECT COUNT(*) AS appointments_today
FROM appointments
WHERE appointment_datetime::DATE = CURRENT_DATE
  AND appointment_status = 'Scheduled';

-- 4. Risk mix on the upcoming schedule
SELECT rs.risk_category, COUNT(*) AS appointments
FROM appointments a
JOIN LATERAL (
    SELECT risk_category FROM risk_scores r
    WHERE r.appointment_id = a.appointment_id
    ORDER BY scored_at DESC LIMIT 1
) rs ON TRUE
WHERE a.appointment_status = 'Scheduled'
GROUP BY rs.risk_category
ORDER BY CASE rs.risk_category WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;

-- 5. High-risk appointments in the next 48 hours (today's outreach list)
SELECT v.appointment_id, v.patient_name, v.clinic_name, v.provider_name,
       v.appointment_datetime, v.no_show_probability, v.recommended_action
FROM vw_appointment_risk v
WHERE v.appointment_status = 'Scheduled'
  AND v.risk_category = 'High'
  AND v.appointment_datetime BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
ORDER BY v.no_show_probability DESC;

-- 6. Open slots and released (recoverable) slots by clinic
SELECT c.clinic_name,
       COUNT(*) FILTER (WHERE s.slot_status = 'Open')                      AS open_slots,
       COUNT(*) FILTER (WHERE s.slot_status = 'Released (Cancellation)')   AS released_slots
FROM open_slots s
JOIN clinics c ON c.clinic_id = s.clinic_id
WHERE s.slot_datetime >= NOW()
GROUP BY c.clinic_name
ORDER BY open_slots DESC;

-- 7. Clinic utilization vs. target
SELECT clinic_name, utilization_rate, target_utilization,
       ROUND(utilization_rate - target_utilization, 4) AS gap_to_target
FROM vw_clinic_utilization
ORDER BY gap_to_target;

-- 8. Provider utilization ranking (next 14 days)
SELECT pr.provider_name, c.clinic_name,
       SUM(s.booked)                                        AS booked,
       SUM(s.booked + s.cancelled)                          AS scheduled_or_cancelled,
       pr.daily_capacity * 10                               AS capacity,
       ROUND(SUM(s.booked)::NUMERIC / (pr.daily_capacity * 10), 4) AS utilization_rate
FROM vw_provider_daily_schedule s
JOIN providers pr ON pr.provider_id = s.provider_id
JOIN clinics c ON c.clinic_id = pr.clinic_id
GROUP BY pr.provider_name, c.clinic_name, pr.daily_capacity
ORDER BY utilization_rate;

-- 9. Average lead time by risk category
SELECT rs.risk_category, ROUND(AVG(a.lead_time_days), 1) AS avg_lead_time_days
FROM appointments a
JOIN LATERAL (
    SELECT risk_category FROM risk_scores r
    WHERE r.appointment_id = a.appointment_id
    ORDER BY scored_at DESC LIMIT 1
) rs ON TRUE
WHERE a.appointment_status = 'Scheduled'
GROUP BY rs.risk_category;

-- 10. Does the SMS reminder correlate with fewer no-shows? (historical)
SELECT sms_received,
       COUNT(*) AS appointments,
       ROUND(AVG(CASE WHEN no_show_flag THEN 1 ELSE 0 END)::NUMERIC, 4) AS no_show_rate
FROM appointments
WHERE appointment_status IN ('Completed', 'No-Show')
GROUP BY sms_received;

-- 11. Waitlist demand and average wait by specialty
SELECT requested_specialty,
       COUNT(*)                                   AS active_requests,
       COUNT(*) FILTER (WHERE urgency_level = 'Urgent') AS urgent_requests,
       ROUND(AVG(CURRENT_DATE - requested_date), 1)     AS avg_days_waiting
FROM waitlist_requests
WHERE waitlist_status IN ('Active', 'Contacted')
GROUP BY requested_specialty
ORDER BY active_requests DESC;

-- 12. Staff action tracker: pending, overdue, completion rate
SELECT
    COUNT(*) FILTER (WHERE task_status = 'Pending')                        AS pending_tasks,
    COUNT(*) FILTER (WHERE task_status = 'In Progress')                    AS in_progress_tasks,
    COUNT(*) FILTER (WHERE task_status NOT IN ('Completed')
                     AND due_date < CURRENT_DATE)                          AS overdue_tasks,
    COUNT(*) FILTER (WHERE task_status = 'Completed')                      AS completed_tasks,
    ROUND(COUNT(*) FILTER (WHERE task_status = 'Completed')::NUMERIC
          / NULLIF(COUNT(*), 0), 4)                                        AS action_completion_rate
FROM access_tasks;

-- 13. Reminder funnel: delivery and confirmation
SELECT
    COUNT(*)                                                        AS reminders_sent,
    COUNT(*) FILTER (WHERE delivery_status = 'Delivered')           AS delivered,
    COUNT(*) FILTER (WHERE patient_response = 'Confirmed')          AS confirmed,
    ROUND(COUNT(*) FILTER (WHERE patient_response = 'Confirmed')::NUMERIC
          / NULLIF(COUNT(*) FILTER (WHERE delivery_status = 'Delivered'), 0), 4)
                                                                    AS confirmation_rate
FROM reminder_events;

-- 14. Weekly no-show trend (historical)
SELECT DATE_TRUNC('week', appointment_datetime)::DATE AS week_start,
       COUNT(*)                                       AS appointments,
       ROUND(AVG(CASE WHEN no_show_flag THEN 1 ELSE 0 END)::NUMERIC, 4) AS no_show_rate
FROM appointments
WHERE appointment_status IN ('Completed', 'No-Show')
GROUP BY 1
ORDER BY 1;

-- 15. Slot recovery opportunity: released slots with at least one active
--     waitlist request in the same specialty
SELECT s.slot_id, s.slot_datetime, c.clinic_name, s.specialty,
       COUNT(w.waitlist_id) AS eligible_waitlist_patients
FROM open_slots s
JOIN clinics c ON c.clinic_id = s.clinic_id
LEFT JOIN waitlist_requests w
       ON w.requested_specialty = s.specialty
      AND w.waitlist_status IN ('Active', 'Contacted')
WHERE s.slot_datetime >= NOW()
GROUP BY s.slot_id, s.slot_datetime, c.clinic_name, s.specialty
HAVING COUNT(w.waitlist_id) > 0
ORDER BY s.slot_datetime
LIMIT 50;
