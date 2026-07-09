-- ============================================================================
-- 02_seed_data.sql — reference data seeds
--
-- Bulk data (patients, appointments, reminders, risk scores, tasks) is loaded
-- from the generated CSVs by etl/load_to_postgres.py. This file seeds the
-- small reference tables so the schema is usable immediately, and shows the
-- COPY commands for a manual psql load.
-- ============================================================================

INSERT INTO clinics (clinic_id, clinic_name, location, service_line, target_utilization) VALUES
    (1, 'Downtown Family Medicine',              'Centro',          'Primary Care',   0.85),
    (2, 'Northside Community Health Center',     'Maria Ortiz',     'Primary Care',   0.82),
    (3, 'Harbor Internal Medicine & Cardiology', 'Jardim Camburi',  'Specialty Care', 0.80),
    (4, 'Eastside Pediatrics & Family Care',     'Jardim da Penha', 'Pediatrics',     0.85),
    (5, 'Riverside Women''s Health Center',      'Praia do Canto',  'Women''s Health',0.80),
    (6, 'Lakeview Behavioral Health & Dermatology','Maruipe',       'Specialty Care', 0.78)
ON CONFLICT (clinic_id) DO NOTHING;

INSERT INTO specialties (specialty_name) VALUES
    ('Family Medicine'), ('Internal Medicine'), ('Cardiology'), ('Endocrinology'),
    ('Pediatrics'), ('Obstetrics & Gynecology'), ('Behavioral Health'), ('Dermatology')
ON CONFLICT (specialty_name) DO NOTHING;

INSERT INTO staff_users (staff_id, staff_name, role) VALUES
    (1, 'Monica Reyes',   'Patient Access Coordinator'),
    (2, 'Jordan Blake',   'Patient Access Coordinator'),
    (3, 'Aisha Thompson', 'Scheduling Specialist'),
    (4, 'Kevin O''Neal',  'Scheduling Specialist'),
    (5, 'Sandra Kim',     'Patient Access Manager'),
    (6, 'Luis Herrera',   'Outreach Specialist')
ON CONFLICT (staff_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Manual bulk load via psql (alternative to etl/load_to_postgres.py).
-- Run from the repository root:
-- ---------------------------------------------------------------------------
-- \copy providers            FROM 'data/synthetic/providers.csv'          CSV HEADER
-- \copy patients (patient_id, gender, age, neighborhood, scholarship_flag, hypertension_flag, diabetes_flag, alcoholism_flag, handicap_flag, patient_name)
--                            FROM 'data/synthetic/patients.csv'           CSV HEADER
-- \copy date_dim             FROM 'data/synthetic/date_dim.csv'           CSV HEADER
-- \copy open_slots           FROM 'data/synthetic/open_slots.csv'         CSV HEADER
-- \copy reminder_events      FROM 'data/synthetic/reminder_events.csv'    CSV HEADER
-- (appointments / waitlist / risk / actions / tasks: use etl/load_to_postgres.py,
--  which selects and orders the correct column subsets.)
