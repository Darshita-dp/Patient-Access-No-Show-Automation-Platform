# Business Case — Patient Access & No-Show Automation Platform

## The problem

Healthcare scheduling teams struggle with appointment no-shows, waitlist gaps,
manual scheduling follow-up, poor access visibility, underused provider
schedules, and inconsistent staff outreach. Missed appointments create unused
provider time, delay care for other patients, reduce clinic utilization, and
make scheduling operations reactive instead of proactive.

The scale is material. Industry studies consistently place ambulatory no-show
rates between 15% and 30%, with an average cost of roughly **$150–$200 per
missed appointment** in unused provider and room capacity. For a six-clinic
network running ~5,000 appointment slots every two weeks (this platform's
demonstration footprint), a 20% no-show rate leaks the equivalent of
**hundreds of provider-hours per month** — while waitlisted patients wait
weeks for exactly those slots.

## Why the current process fails

1. **No risk visibility.** Every appointment looks the same on the schedule;
   staff cannot tell which bookings are likely to fail.
2. **Uniform reminders.** The same SMS goes to the reliable 80% and the
   high-risk 20%, so outreach effort is wasted where it isn't needed and
   insufficient where it is.
3. **Slow slot recovery.** Cancellations are discovered ad hoc; by the time a
   waitlist patient is called, the slot has often expired.
4. **No workflow accountability.** Follow-up lives in staff memory and
   spreadsheets; managers see utilization losses in month-end reports rather
   than pending work in real time.

## The solution

A decision-support platform for scheduling operations that closes the loop
from prediction to action:

**Prediction → Risk category → Recommended action → Staff task → Waitlist
match → Manager dashboard**

- A no-show model ranks every upcoming appointment; the **top-20% band**
  becomes the daily outreach list — sized to real staff capacity.
- A **recommended-action engine** converts risk into concrete next steps
  (call, targeted SMS, escalation, transportation check).
- A **waitlist matching engine** ranks replacement candidates for every open
  or released slot by urgency, wait time, availability fit, and attendance
  likelihood.
- A **React operations app** gives schedulers a work queue, search, appointment
  detail with risk explanation, waitlist manager, provider schedules, clinic
  utilization, and a manager action tracker.
- A **Power BI executive layer** tracks the KPIs leadership cares about, and a
  **Power Automate/SharePoint workflow design** shows how outreach and
  escalation would run inside a Microsoft-shop clinic.

## Quantified opportunity (simulated)

Based on synthetic workflow assumptions, clearly not measured hospital
results:

| Metric | Before | After |
|---|---|---|
| No-show rate | 18.5% | 14.2% |
| Manual outreach hours/week | 22 | 9 |
| Recovered open slots/week | 4 | 17 |
| High-risk appointments contacted | 35% | 82% |
| Average waitlist days | 21 | 14 |

Mechanics behind the numbers: the high-risk band concentrates ~2× the base
no-show rate, so focusing calls there converts the most preventable misses;
released slots get ranked waitlist offers within minutes instead of days;
automation absorbs low/medium-risk reminders that previously consumed staff
hours.

## Target users

| User | What they get |
|---|---|
| Scheduling staff | A prioritized work queue with a recommended action per appointment |
| Patient access manager | Task accountability, overdue escalations, outreach completion rates |
| Clinic operations leader | Utilization vs. target, access leakage, recovered-slot performance |

## Investment & risks

Built entirely on commodity open-source (Python, PostgreSQL, FastAPI, React)
plus the Microsoft stack most health systems already license (Power BI, Power
Automate, SharePoint). Key risks: model fairness across patient subgroups
(audit before go-live), integration effort with the scheduling system of
record (HL7/FHIR interface not included in this demonstration), and change
management for staff workflow adoption.
