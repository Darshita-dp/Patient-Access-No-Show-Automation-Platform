-- ============================================================================
-- Patient Access & No-Show Automation Platform
-- 01_schema.sql — PostgreSQL data model for patient access operations
--
-- Grain notes:
--   appointments          one row per booked visit (historical + upcoming)
--   risk_scores           one row per scored appointment per model version
--   recommended_actions   one row per appointment per action recommendation
--   access_tasks          one row per staff work item
--   open_slots            one row per unbooked provider slot (next 14 days)
-- ============================================================================

DROP TABLE IF EXISTS waitlist_match_results, access_tasks, recommended_actions,
    risk_scores, reminder_events, appointment_status_history, open_slots,
    appointments, waitlist_requests, patients, providers, specialties,
    clinics, staff_users, date_dim CASCADE;

-- ---------------------------------------------------------------------------
-- Reference / dimension tables
-- ---------------------------------------------------------------------------

CREATE TABLE clinics (
    clinic_id           SERIAL PRIMARY KEY,
    clinic_name         VARCHAR(100) NOT NULL,
    location            VARCHAR(100),
    service_line        VARCHAR(100),
    target_utilization  NUMERIC(5,2)          -- e.g. 0.85 = 85% target
);

CREATE TABLE specialties (
    specialty_id    SERIAL PRIMARY KEY,
    specialty_name  VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE providers (
    provider_id     SERIAL PRIMARY KEY,
    provider_name   VARCHAR(100) NOT NULL,
    clinic_id       INT REFERENCES clinics(clinic_id),
    specialty       VARCHAR(100),
    daily_capacity  INT CHECK (daily_capacity > 0)
);

CREATE TABLE patients (
    patient_id        BIGINT PRIMARY KEY,
    patient_name      VARCHAR(120),           -- synthetic display name, not PHI
    gender            VARCHAR(10),
    age               INT CHECK (age BETWEEN 0 AND 120),
    neighborhood      VARCHAR(150),
    scholarship_flag  BOOLEAN,
    hypertension_flag BOOLEAN,
    diabetes_flag     BOOLEAN,
    alcoholism_flag   BOOLEAN,
    handicap_flag     INT
);

CREATE TABLE staff_users (
    staff_id    SERIAL PRIMARY KEY,
    staff_name  VARCHAR(100) NOT NULL,
    role        VARCHAR(100)
);

CREATE TABLE date_dim (
    date_key      INT PRIMARY KEY,            -- YYYYMMDD
    full_date     DATE NOT NULL,
    year          INT,
    month         INT,
    month_name    VARCHAR(20),
    week_of_year  INT,
    day_of_week   VARCHAR(20),
    is_weekend    BOOLEAN
);

-- ---------------------------------------------------------------------------
-- Core operational tables
-- ---------------------------------------------------------------------------

CREATE TABLE appointments (
    appointment_id        BIGINT PRIMARY KEY,
    patient_id            BIGINT REFERENCES patients(patient_id),
    provider_id           INT REFERENCES providers(provider_id),
    clinic_id             INT REFERENCES clinics(clinic_id),
    scheduled_datetime    TIMESTAMP,           -- when the booking was made
    appointment_datetime  TIMESTAMP,           -- when the visit happens
    appointment_status    VARCHAR(50),         -- Scheduled/Completed/No-Show/Cancelled
    no_show_flag          BOOLEAN,             -- NULL until outcome is known
    sms_received          BOOLEAN,
    lead_time_days        INT,
    appointment_type      VARCHAR(50),
    specialty             VARCHAR(100),
    appointment_hour      INT
);

CREATE TABLE appointment_status_history (
    history_id      SERIAL PRIMARY KEY,
    appointment_id  BIGINT REFERENCES appointments(appointment_id),
    old_status      VARCHAR(50),
    new_status      VARCHAR(50),
    changed_by      VARCHAR(100),
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE open_slots (
    slot_id        SERIAL PRIMARY KEY,
    slot_datetime  TIMESTAMP NOT NULL,
    provider_id    INT REFERENCES providers(provider_id),
    clinic_id      INT REFERENCES clinics(clinic_id),
    specialty      VARCHAR(100),
    slot_status    VARCHAR(50)                 -- Open / Released (Cancellation)
);

CREATE TABLE waitlist_requests (
    waitlist_id            SERIAL PRIMARY KEY,
    patient_id             BIGINT REFERENCES patients(patient_id),
    requested_specialty    VARCHAR(100),
    preferred_clinic_id    INT REFERENCES clinics(clinic_id),
    preferred_provider_id  INT REFERENCES providers(provider_id),
    requested_date         DATE,
    urgency_level          VARCHAR(20),        -- Routine / Soon / Urgent
    availability_window    VARCHAR(100),
    waitlist_status        VARCHAR(50)
);

CREATE TABLE reminder_events (
    reminder_id       SERIAL PRIMARY KEY,
    appointment_id    BIGINT REFERENCES appointments(appointment_id),
    reminder_type     VARCHAR(50),
    sent_datetime     TIMESTAMP,
    delivery_status   VARCHAR(50),
    patient_response  VARCHAR(50)
);

-- ---------------------------------------------------------------------------
-- Model output and workflow tables
-- ---------------------------------------------------------------------------

CREATE TABLE risk_scores (
    risk_score_id        SERIAL PRIMARY KEY,
    appointment_id       BIGINT REFERENCES appointments(appointment_id),
    model_version        VARCHAR(50),
    no_show_probability  NUMERIC(6,4) CHECK (no_show_probability BETWEEN 0 AND 1),
    risk_category        VARCHAR(20),          -- Low / Medium / High
    scored_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recommended_actions (
    action_id           SERIAL PRIMARY KEY,
    appointment_id      BIGINT REFERENCES appointments(appointment_id),
    recommended_action  VARCHAR(200),
    action_reason       TEXT,
    priority            VARCHAR(20),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE access_tasks (
    task_id         SERIAL PRIMARY KEY,
    appointment_id  BIGINT REFERENCES appointments(appointment_id),
    assigned_to     VARCHAR(100),
    task_type       VARCHAR(100),
    priority        VARCHAR(20),
    due_date        DATE,
    task_status     VARCHAR(50),               -- Pending / In Progress / Completed / Overdue
    completed_date  DATE
);

CREATE TABLE waitlist_match_results (
    match_id        SERIAL PRIMARY KEY,
    waitlist_id     INT REFERENCES waitlist_requests(waitlist_id),
    appointment_id  BIGINT REFERENCES appointments(appointment_id),
    slot_id         INT REFERENCES open_slots(slot_id),
    match_score     NUMERIC(6,4),
    match_reason    TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- Indexes for the access patterns the API and dashboard use most
-- ---------------------------------------------------------------------------

CREATE INDEX idx_appt_patient      ON appointments (patient_id);
CREATE INDEX idx_appt_provider_dt  ON appointments (provider_id, appointment_datetime);
CREATE INDEX idx_appt_clinic_dt    ON appointments (clinic_id, appointment_datetime);
CREATE INDEX idx_appt_status       ON appointments (appointment_status);
CREATE INDEX idx_risk_appt         ON risk_scores (appointment_id);
CREATE INDEX idx_risk_category     ON risk_scores (risk_category);
CREATE INDEX idx_action_appt       ON recommended_actions (appointment_id);
CREATE INDEX idx_task_status       ON access_tasks (task_status, due_date);
CREATE INDEX idx_reminder_appt     ON reminder_events (appointment_id);
CREATE INDEX idx_slot_provider     ON open_slots (provider_id, slot_datetime);
CREATE INDEX idx_waitlist_status   ON waitlist_requests (waitlist_status, urgency_level);
