# System Architecture

The platform connects patient access data, predictive modeling, operational
rules, and dashboard reporting into one workflow that supports scheduling
staff and healthcare managers.

```mermaid
flowchart TD
    subgraph DATA["Data Layer"]
        A["Raw Appointment Data<br/>(Kaggle schema / synthetic fallback)"]
        B["Python ETL + Feature Engineering<br/>etl/*.py — cleaning, history features,<br/>synthetic operational tables"]
        C[("PostgreSQL<br/>Healthcare Access Database<br/>(CSV mode fallback)")]
    end

    subgraph ML["Decision Layer"]
        D["No-Show ML Model<br/>scikit-learn pipeline, temporal split"]
        E["Risk Scores + Action Recommendations<br/>Low/Medium/High bands →<br/>action engine + waitlist matching"]
    end

    subgraph SERVE["Application Layer"]
        F["FastAPI Backend<br/>appointments · risk · waitlist ·<br/>providers · clinics · tasks"]
        G["React Scheduling Team App<br/>8 operational views"]
    end

    subgraph REPORT["Management Layer"]
        H["Power BI Executive Dashboard<br/>7-page design + DAX measures"]
        I["Power Automate / SharePoint<br/>Task Workflow (simulated)"]
    end

    A --> B --> C --> D --> E --> F --> G
    C --> H
    E --> I
    F --> H
    I --> G
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| `etl/` | Ingest raw appointments, clean to snake_case, engineer leakage-safe features, generate providers/clinics/waitlist/reminders/schedule tables |
| `sql/` | PostgreSQL schema, reporting views, KPI queries |
| `models/` | Train and compare classifiers, persist model + risk thresholds, score upcoming appointments |
| `api/services/` | Recommended-action rules and waitlist priority scoring |
| `api/` | REST endpoints for every operational view; CSV-mode data store |
| `frontend/` | Scheduling team application (Command Center → Action Tracker) |
| `powerbi/` | Executive dashboard design, DAX, before/after simulation |
| `workflows/` | Power Automate flow specs + SharePoint task list mock |
```
