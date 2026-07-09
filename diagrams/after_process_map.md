# After Automation — Proactive Patient Access Process

Risk is scored at booking, work is prioritized automatically, and released
slots are refilled from the waitlist before they expire.

```mermaid
flowchart TD
    A["Patient schedules appointment"] --> B["Appointment data flows into<br/>access platform (ETL)"]
    B --> C["No-show risk score is generated<br/>(ML model, calibrated probability)"]
    C --> D["Risk category and recommended<br/>action are assigned"]
    D --> E["High-risk appointment creates<br/>outreach task (assigned + due-dated)"]
    E --> F["Reminder / call workflow is triggered<br/>(SMS first, live call inside 48h)"]
    F --> G["Open slots are matched to<br/>waitlist patients (priority score)"]
    G --> H["Manager tracks utilization and<br/>action completion in real time"]

    style C fill:#eaf3fb,stroke:#1d6fb8,color:#1a2632
    style E fill:#e7f5f6,stroke:#0e7f86,color:#1a2632
    style G fill:#e7f4ec,stroke:#1e7d46,color:#1a2632
```

**What changed:** outreach capacity concentrates on the top-20% risk band,
reminders escalate by risk instead of being uniform, cancellations
immediately produce ranked waitlist offers, and the manager dashboard shows
pending work — not just last month's losses.
