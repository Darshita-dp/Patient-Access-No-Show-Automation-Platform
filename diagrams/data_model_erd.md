# Data Model — Entity Relationship Diagram

PostgreSQL schema (`sql/01_schema.sql`). Star-friendly: `appointments` is the
central fact; model outputs and workflow tables hang off it one-to-many.

```mermaid
erDiagram
    CLINICS ||--o{ PROVIDERS : "staffs"
    CLINICS ||--o{ APPOINTMENTS : "hosts"
    PROVIDERS ||--o{ APPOINTMENTS : "sees"
    PATIENTS ||--o{ APPOINTMENTS : "books"
    APPOINTMENTS ||--o{ RISK_SCORES : "is scored"
    APPOINTMENTS ||--o{ RECOMMENDED_ACTIONS : "gets"
    APPOINTMENTS ||--o{ ACCESS_TASKS : "creates"
    APPOINTMENTS ||--o{ REMINDER_EVENTS : "receives"
    APPOINTMENTS ||--o{ APPOINTMENT_STATUS_HISTORY : "logs"
    PATIENTS ||--o{ WAITLIST_REQUESTS : "requests"
    CLINICS ||--o{ WAITLIST_REQUESTS : "preferred by"
    PROVIDERS ||--o{ WAITLIST_REQUESTS : "preferred by"
    WAITLIST_REQUESTS ||--o{ WAITLIST_MATCH_RESULTS : "matched in"
    OPEN_SLOTS ||--o{ WAITLIST_MATCH_RESULTS : "offered as"
    PROVIDERS ||--o{ OPEN_SLOTS : "has capacity"

    CLINICS {
        int clinic_id PK
        varchar clinic_name
        varchar location
        varchar service_line
        numeric target_utilization
    }
    PROVIDERS {
        int provider_id PK
        varchar provider_name
        int clinic_id FK
        varchar specialty
        int daily_capacity
    }
    PATIENTS {
        bigint patient_id PK
        varchar patient_name
        varchar gender
        int age
        varchar neighborhood
        boolean scholarship_flag
        boolean hypertension_flag
        boolean diabetes_flag
        boolean alcoholism_flag
        int handicap_flag
    }
    APPOINTMENTS {
        bigint appointment_id PK
        bigint patient_id FK
        int provider_id FK
        int clinic_id FK
        timestamp scheduled_datetime
        timestamp appointment_datetime
        varchar appointment_status
        boolean no_show_flag
        boolean sms_received
        int lead_time_days
        varchar appointment_type
        varchar specialty
    }
    RISK_SCORES {
        int risk_score_id PK
        bigint appointment_id FK
        varchar model_version
        numeric no_show_probability
        varchar risk_category
        timestamp scored_at
    }
    RECOMMENDED_ACTIONS {
        int action_id PK
        bigint appointment_id FK
        varchar recommended_action
        text action_reason
        varchar priority
    }
    ACCESS_TASKS {
        int task_id PK
        bigint appointment_id FK
        varchar assigned_to
        varchar task_type
        varchar priority
        date due_date
        varchar task_status
        date completed_date
    }
    WAITLIST_REQUESTS {
        int waitlist_id PK
        bigint patient_id FK
        varchar requested_specialty
        int preferred_clinic_id FK
        int preferred_provider_id FK
        date requested_date
        varchar urgency_level
        varchar availability_window
        varchar waitlist_status
    }
    WAITLIST_MATCH_RESULTS {
        int match_id PK
        int waitlist_id FK
        int slot_id FK
        numeric match_score
        text match_reason
    }
    OPEN_SLOTS {
        int slot_id PK
        timestamp slot_datetime
        int provider_id FK
        int clinic_id FK
        varchar specialty
        varchar slot_status
    }
    REMINDER_EVENTS {
        int reminder_id PK
        bigint appointment_id FK
        varchar reminder_type
        timestamp sent_datetime
        varchar delivery_status
        varchar patient_response
    }
```

Supporting tables not shown: `specialties`, `staff_users`, `date_dim`
(reporting dimension for Power BI).
