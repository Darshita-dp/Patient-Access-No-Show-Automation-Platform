# Before Automation — Reactive Scheduling Process

Every step is manual, and problems are discovered **after** the slot is
already lost.

```mermaid
flowchart TD
    A["Patient schedules appointment"] --> B["Appointment sits on schedule<br/>(no risk visibility)"]
    B --> C["Generic reminder may or may not be sent<br/>(same message for every patient)"]
    C --> D["Patient does not show"]
    D --> E["Provider slot is wasted<br/>(~$150–$200 of unused capacity)"]
    E --> F["Staff manually reviews schedule gaps<br/>(after the fact)"]
    F --> G["Waitlist patient may not be<br/>contacted in time"]
    G --> H["Manager sees issue after the fact<br/>(monthly utilization report)"]

    style D fill:#fbeceb,stroke:#b3372f,color:#1a2632
    style E fill:#fbeceb,stroke:#b3372f,color:#1a2632
    style H fill:#fdf3e0,stroke:#995f0c,color:#1a2632
```

**Failure modes:** no prioritization of outreach, reminder effort spread
evenly across low- and high-risk patients, released slots discovered too late
to refill, and managers reporting on losses instead of preventing them.
