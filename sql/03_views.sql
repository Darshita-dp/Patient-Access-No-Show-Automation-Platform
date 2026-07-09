-- ============================================================================
-- 03_views.sql — operational views consumed by the API and Power BI model
-- ============================================================================

-- One row per appointment with its latest risk score and recommended action.
CREATE OR REPLACE VIEW vw_appointment_risk AS
SELECT
    a.appointment_id,
    a.patient_id,
    p.patient_name,
    a.provider_id,
    pr.provider_name,
    a.clinic_id,
    c.clinic_name,
    a.specialty,
    a.appointment_datetime,
    a.appointment_status,
    a.appointment_type,
    a.lead_time_days,
    a.sms_received,
    rs.no_show_probability,
    rs.risk_category,
    ra.recommended_action,
    ra.priority AS action_priority
FROM appointments a
JOIN patients  p  ON p.patient_id  = a.patient_id
JOIN providers pr ON pr.provider_id = a.provider_id
JOIN clinics   c  ON c.clinic_id   = a.clinic_id
LEFT JOIN LATERAL (
    SELECT no_show_probability, risk_category
    FROM risk_scores r
    WHERE r.appointment_id = a.appointment_id
    ORDER BY r.scored_at DESC
    LIMIT 1
) rs ON TRUE
LEFT JOIN LATERAL (
    SELECT recommended_action, priority
    FROM recommended_actions x
    WHERE x.appointment_id = a.appointment_id
    ORDER BY x.created_at DESC
    LIMIT 1
) ra ON TRUE;

-- Upcoming high-risk appointments that still need staff attention.
CREATE OR REPLACE VIEW vw_high_risk_worklist AS
SELECT
    v.*,
    t.task_id,
    t.task_status,
    t.assigned_to,
    t.due_date
FROM vw_appointment_risk v
LEFT JOIN access_tasks t ON t.appointment_id = v.appointment_id
WHERE v.appointment_status = 'Scheduled'
  AND v.risk_category = 'High'
ORDER BY v.appointment_datetime;

-- Clinic-level utilization for the next 14 days.
CREATE OR REPLACE VIEW vw_clinic_utilization AS
WITH capacity AS (
    SELECT c.clinic_id,
           SUM(pr.daily_capacity) * 10 AS slots_next_two_weeks  -- 10 weekdays
    FROM clinics c
    JOIN providers pr ON pr.clinic_id = c.clinic_id
    GROUP BY c.clinic_id
),
booked AS (
    SELECT clinic_id,
           COUNT(*) FILTER (WHERE appointment_status = 'Scheduled') AS booked_appointments,
           COUNT(*) FILTER (WHERE appointment_status = 'Cancelled') AS cancelled_appointments
    FROM appointments
    WHERE appointment_datetime >= CURRENT_DATE
    GROUP BY clinic_id
)
SELECT
    c.clinic_id,
    c.clinic_name,
    c.service_line,
    c.target_utilization,
    cap.slots_next_two_weeks,
    COALESCE(b.booked_appointments, 0)   AS booked_appointments,
    COALESCE(b.cancelled_appointments, 0) AS cancelled_appointments,
    ROUND(COALESCE(b.booked_appointments, 0)::NUMERIC
          / NULLIF(cap.slots_next_two_weeks, 0), 4) AS utilization_rate
FROM clinics c
JOIN capacity cap ON cap.clinic_id = c.clinic_id
LEFT JOIN booked b ON b.clinic_id = c.clinic_id;

-- Historical no-show rate by clinic (for leakage benchmarking).
CREATE OR REPLACE VIEW vw_clinic_no_show_rate AS
SELECT
    c.clinic_id,
    c.clinic_name,
    COUNT(*)                                            AS total_appointments,
    COUNT(*) FILTER (WHERE a.no_show_flag)              AS no_shows,
    ROUND(AVG(CASE WHEN a.no_show_flag THEN 1 ELSE 0 END)::NUMERIC, 4) AS no_show_rate
FROM appointments a
JOIN clinics c ON c.clinic_id = a.clinic_id
WHERE a.appointment_status IN ('Completed', 'No-Show')
GROUP BY c.clinic_id, c.clinic_name;

-- Provider daily schedule summary (bookings + risk) for schedule views.
CREATE OR REPLACE VIEW vw_provider_daily_schedule AS
SELECT
    pr.provider_id,
    pr.provider_name,
    pr.clinic_id,
    pr.specialty,
    pr.daily_capacity,
    a.appointment_datetime::DATE                        AS schedule_date,
    COUNT(*) FILTER (WHERE a.appointment_status = 'Scheduled') AS booked,
    COUNT(*) FILTER (WHERE a.appointment_status = 'Cancelled') AS cancelled,
    COUNT(*) FILTER (WHERE rs.risk_category = 'High'
                     AND a.appointment_status = 'Scheduled')   AS high_risk_booked
FROM providers pr
JOIN appointments a ON a.provider_id = pr.provider_id
LEFT JOIN LATERAL (
    SELECT risk_category
    FROM risk_scores r
    WHERE r.appointment_id = a.appointment_id
    ORDER BY r.scored_at DESC
    LIMIT 1
) rs ON TRUE
WHERE a.appointment_datetime >= CURRENT_DATE
GROUP BY pr.provider_id, pr.provider_name, pr.clinic_id, pr.specialty,
         pr.daily_capacity, a.appointment_datetime::DATE;

-- Waitlist queue with wait ages, for access-gap reporting.
CREATE OR REPLACE VIEW vw_waitlist_queue AS
SELECT
    w.waitlist_id,
    w.patient_id,
    p.patient_name,
    w.requested_specialty,
    w.preferred_clinic_id,
    c.clinic_name AS preferred_clinic,
    w.urgency_level,
    w.availability_window,
    w.waitlist_status,
    w.requested_date,
    (CURRENT_DATE - w.requested_date) AS days_waiting
FROM waitlist_requests w
JOIN patients p ON p.patient_id = w.patient_id
LEFT JOIN clinics c ON c.clinic_id = w.preferred_clinic_id
WHERE w.waitlist_status IN ('Active', 'Contacted')
ORDER BY w.urgency_level DESC, days_waiting DESC;

-- Staff task board with overdue flags.
CREATE OR REPLACE VIEW vw_task_board AS
SELECT
    t.task_id,
    t.appointment_id,
    t.assigned_to,
    t.task_type,
    t.priority,
    t.due_date,
    t.task_status,
    t.completed_date,
    (t.task_status NOT IN ('Completed') AND t.due_date < CURRENT_DATE) AS is_overdue,
    v.risk_category,
    v.appointment_datetime
FROM access_tasks t
LEFT JOIN vw_appointment_risk v ON v.appointment_id = t.appointment_id;
