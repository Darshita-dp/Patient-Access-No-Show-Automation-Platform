# Demo Walkthrough — 60 to 90 Seconds

A tight tour of the Patient Access & No-Show Automation Platform for LinkedIn,
interviews, or recruiter screens. Everything here uses the eight React views
that ship with the repo. Use one of the paths below depending on how much time
you have.

- **60-second path** — Command Center → Work Queue (filter High) → Appointment
  Detail → Waitlist Manager → Action Tracker → close.
- **90-second path** — the same, plus a short mention of the Power BI
  reporting-layer design and the fairness audit.

---

## 1. 60-Second Demo Flow

1. **Open the Command Center.** Point out today's KPIs and the "High-Risk
   Appointments Needing Action" list.
2. **Open the Appointment Work Queue.** Filter by **Risk Category = High**.
3. **Open one High-risk Appointment Detail.** Read the no-show probability and
   the plain-language risk reason.
4. **Show the recommended action** on the same page (e.g. "Call patient
   directly and confirm attendance").
5. **Open the Waitlist Manager.** Show the ranked replacement candidates and
   the match reason for the top match.
6. **Open the Action Tracker.** Show the staff task board with priorities,
   overdue flags, and completion by staff.
7. **Mention the Power BI reporting-layer design** and the mock executive
   summary — this is the manager view (design/spec/mock, not a built `.pbix`).
8. **Close with the product story:**
   *Prediction → Risk category → Recommended action → Staff task → Waitlist
   match → Manager dashboard.*

---

## 2. Speaker Script

Read this out loud once; it fits inside 75 seconds at a natural pace.

> "This is a Patient Access & No-Show Automation Platform I built end to end
> — Python, PostgreSQL, FastAPI, and React, with a Power BI reporting-layer
> design on top of the same data model.
>
> The problem: about one in five outpatient appointments becomes a no-show.
> Each one wastes provider capacity and pushes waitlisted patients further
> back. Most scheduling teams work reactively from a flat schedule and send
> the same reminder to everyone.
>
> [Command Center] I open on the Command Center. This is the morning view for
> a patient access team — today's appointments, no-show rate, open slots,
> waitlist size, and the high-risk appointments that need outreach today.
>
> [Work Queue, filter High] From here I go to the Work Queue and filter to
> High risk. Every high-risk appointment has a probability, a risk category,
> a recommended staff action, and a task status.
>
> [Appointment Detail] I open one appointment. The model gives a no-show
> probability, but the important part is the explanation — long lead time,
> prior no-show history, no reminder response — in plain language a
> coordinator can read to the patient.
>
> [Recommended action] The recommended action here is 'Call patient directly
> and confirm attendance.' The model predicts risk, but the action engine
> translates that risk into an operational next step for scheduling staff.
>
> [Waitlist Manager] If a slot opens, the Waitlist Manager ranks eligible
> patients using urgency, days waiting, availability match, attendance
> likelihood, and provider preference — with a human-readable reason for
> every match.
>
> [Action Tracker] The Action Tracker is the manager's view of everything in
> flight — pending, overdue, completed by staff.
>
> [Power BI] The Power BI reporting layer sits above this — a seven-page
> executive dashboard design with the DAX measures documented. It's a design
> and mock, not a built `.pbix`.
>
> The whole product story is: prediction, risk category, recommended action,
> staff task, waitlist match, manager dashboard. That is what turns a model
> into a decision-support system for a real scheduling operation."

Two swaps if you want to trim to 60 seconds: drop the Power BI paragraph, and
condense the two Appointment Detail beats ("probability" and "recommended
action") into one sentence.

---

## 3. Screen-by-Screen Checklist

| # | Screen | What to click | What to say | Why it matters |
|---|---|---|---|---|
| 1 | **Command Center** | Nothing — just point at the KPI row and the "High-Risk Appointments Needing Action" panel | *"This is the morning view — today's appointments, no-show rate, open slots, waitlist, and today's high-risk outreach list."* | Establishes the platform as an operational tool, not a report |
| 2 | **Appointment Work Queue** | Set the **Risk Category** filter to **High** | *"Every appointment has a risk score, a category, a recommended action, and a task status — filtered here to just the High-risk ones."* | Shows the prioritized queue that focuses limited staff capacity |
| 3 | **Appointment Detail** (any High-risk one) | Click a row from the queue | *"The model gives a probability, but the explanation is what a coordinator can act on — long lead time, prior no-show history, no reminder response."* | Turns a black-box score into something staff and patients can hear |
| 4 | **Recommended action** (same page) | Scroll to the action panel | *"The recommended action is 'Call patient directly.' The model predicts risk; the action engine turns that into a next step."* | The core product thesis — prediction alone isn't the product |
| 5 | **Waitlist Manager** | Sidebar → Waitlist Manager | *"When a slot opens, this ranks eligible patients by urgency, wait time, availability fit, and attendance likelihood — with a match reason."* | Shows the slot-recovery half of the loop |
| 6 | **Action Tracker** | Sidebar → Action Tracker | *"The manager sees pending, overdue, and completed tasks by staff — that's the accountability layer."* | Ties the operational loop to a manager-visible outcome |
| 7 | **Power BI mock** (optional) | Open the mock image in `powerbi/dashboard_screenshots/` or link the folder in the README | *"Above all this is a Power BI reporting-layer design — seven-page executive dashboard with DAX measures documented. It's a design and mock, not a completed `.pbix`."* | Executive layer, honestly scoped |
| 8 | **Close** | Return to Command Center | *"The product story: prediction → risk category → recommended action → staff task → waitlist match → manager dashboard."* | Leaves the interviewer with the one line to remember |

---

## 4. LinkedIn Video Caption

Use this as the post body when you attach a screen recording.

> I built a Patient Access & No-Show Automation Platform to help scheduling
> teams act on no-show risk before the slot is lost.
>
> A quick tour:
> • Command Center — today's no-show risk, open slots, and outreach queue at
>   a glance
> • Appointment Work Queue — every visit prioritized with a risk category, a
>   recommended action, and a task status
> • Appointment Detail — a plain-language risk explanation a coordinator can
>   read to the patient
> • Waitlist Manager — released slots matched to ranked, ready-to-attend
>   candidates with a human-readable match reason
> • Action Tracker — pending, overdue, and completed staff tasks by owner
>
> The biggest lesson from this project: prediction alone isn't the product.
> The model predicts risk; the action engine turns that risk into an
> operational next step for scheduling staff.
>
> Prediction → Risk category → Recommended action → Staff task → Waitlist
> match → Manager dashboard.
>
> Stack: Python · scikit-learn · FastAPI · React · PostgreSQL · Power BI
> reporting-layer design.
>
> All data is synthetic — no PHI. Repository in the comments.
>
> #HealthcareAnalytics #PatientAccess #ProductAnalytics
> #HealthcareOperations #Python #FastAPI #React #PowerBI

Shorter variant (for a comment, or if you record without a face on camera):

> Quick 90-second tour of the Patient Access & No-Show Automation Platform
> I built — from today's high-risk outreach queue, into an appointment's
> risk explanation and recommended action, into the waitlist match that
> recovers the slot, and out to the manager's action tracker. Prediction is
> the input; the operational workflow is the product. Synthetic data, no
> PHI. Repo in the comments.

---

## 5. Recording Guidance

- **Do not link a video or GIF from the README until one actually exists.**
  The README currently uses static screenshots only, which is honest. If you
  record a walkthrough later, add it as a `docs/demo.gif` or a YouTube link
  and embed it near the hero — but not before.
- **If you record a GIF:** aim for 15–30 seconds and 1200 px wide. Trim to
  the four beats that carry the story on their own: Command Center → Work
  Queue (High filter engaged) → Appointment Detail → Waitlist Manager. The
  Action Tracker is worth a screenshot but reads poorly in a GIF because
  the value is in the table.
- **If you record a video:** 60–90 seconds, screen only, no face required.
  Use the speaker script above verbatim. Record with the API and the
  frontend both running locally (`uvicorn api.main:app --port 8000` and
  `vite` on `:5173`) so the data is live, not stubbed.
- **Interview delivery tip:** memorize the closing line ("prediction → risk
  category → recommended action → staff task → waitlist match → manager
  dashboard") word-for-word. Every other beat can be paraphrased; that one
  is the sentence you want the interviewer to write down.
- **What to skip in a short demo:** the Provider Schedule and Clinic
  Utilization views are strong but don't fit inside 60–90 seconds. Save
  them for a follow-up question ("what does a manager see?").
