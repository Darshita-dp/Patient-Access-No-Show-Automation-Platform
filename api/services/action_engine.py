"""Recommended action engine.

The model predicts risk; this engine translates that risk into operational
next steps for scheduling staff. Rules are deliberately transparent — a
patient access manager should be able to read this file and recognize their
own playbook.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Staff rotation for task assignment (coordinators handle calls/reminders,
# the outreach specialist takes escalations, the manager reviews utilization).
COORDINATORS = ["Monica Reyes", "Jordan Blake", "Aisha Thompson", "Kevin O'Neal"]
OUTREACH_SPECIALIST = "Luis Herrera"
ACCESS_MANAGER = "Sandra Kim"

ACTION_TASK_MAP = {
    "Call patient directly and confirm attendance": ("Call Patient", "High"),
    "Send SMS reminder and create staff follow-up task": ("Send Reminder", "High"),
    "Escalate to access team for direct outreach": ("Escalate Access Issue", "High"),
    "Send automated reminder": ("Send Reminder", "Medium"),
    "Confirm transportation and attendance": ("Confirm Transportation", "High"),
}


def recommend_action(row: dict) -> tuple[str, str, str]:
    """Return (recommended_action, action_reason, priority) for one appointment.

    Expects: risk_category, hours_until_appointment, patient_no_show_rate,
    sms_received, handicap_flag.
    """
    risk = row["risk_category"]
    hours_until_appt = row["hours_until_appointment"]
    previous_no_show_rate = row.get("patient_no_show_rate", 0.0)
    sms_received = bool(row.get("sms_received", False))
    mobility_need = int(row.get("handicap_flag", 0) or 0) >= 2

    if risk == "High" and previous_no_show_rate >= 0.5:
        return (
            "Escalate to access team for direct outreach",
            f"High risk with a {previous_no_show_rate:.0%} personal no-show history — "
            "standard reminders have not worked for this patient.",
            "High",
        )
    if risk == "High" and mobility_need and hours_until_appt <= 72:
        return (
            "Confirm transportation and attendance",
            "High risk with a documented mobility need and the visit is inside 72 "
            "hours — transportation is the most common failure point.",
            "High",
        )
    if risk == "High" and hours_until_appt <= 48:
        return (
            "Call patient directly and confirm attendance",
            "High risk and the appointment is within 48 hours — a live call is the "
            "highest-conversion intervention this close to the visit.",
            "High",
        )
    if risk == "High" and not sms_received:
        return (
            "Send SMS reminder and create staff follow-up task",
            "High risk and no SMS reminder has been sent yet — close the reminder "
            "gap first, then follow up.",
            "High",
        )
    if risk == "High":
        return (
            "Call patient directly and confirm attendance",
            "High no-show risk — proactive confirmation protects the slot.",
            "High",
        )
    if risk == "Medium" and hours_until_appt <= 72:
        return (
            "Send automated reminder",
            "Medium risk inside the 72-hour window — an automated reminder is "
            "sufficient at this risk level.",
            "Medium",
        )
    if risk == "Low":
        return (
            "No manual action needed",
            "Low predicted no-show risk — automated confirmations cover this visit.",
            "Low",
        )
    return (
        "Monitor appointment",
        "Medium risk outside the reminder window — re-evaluate as the visit "
        "approaches.",
        "Medium",
    )


def build_recommended_actions(scored: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """One recommendation per scheduled, scored appointment."""
    df = scored.copy()
    df["hours_until_appointment"] = (
        (pd.to_datetime(df["appointment_datetime"]) - now).dt.total_seconds() / 3600
    ).round(1)
    recs = df.apply(lambda r: recommend_action(r.to_dict()), axis=1, result_type="expand")
    recs.columns = ["recommended_action", "action_reason", "priority"]
    out = pd.concat([df[["appointment_id"]], recs], axis=1)
    out.insert(0, "action_id", range(1, len(out) + 1))
    out["created_at"] = now.isoformat(timespec="seconds")
    return out


def build_access_tasks(
    scored: pd.DataFrame, actions: pd.DataFrame, now: datetime,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Create staff work items for every recommendation that needs a human.

    Tasks for visits early in the window get simulated progress (completed /
    in progress / overdue) so the Action Tracker reflects a live operation.
    """
    merged = actions.merge(
        scored[["appointment_id", "appointment_datetime", "risk_category"]],
        on="appointment_id",
    )
    needs_task = merged[merged["recommended_action"].isin(ACTION_TASK_MAP)].reset_index(drop=True)

    rows = []
    for i, r in needs_task.iterrows():
        task_type, priority = ACTION_TASK_MAP[r["recommended_action"]]
        appt_dt = pd.to_datetime(r["appointment_datetime"])
        if r["recommended_action"] == "Escalate to access team for direct outreach":
            assignee = OUTREACH_SPECIALIST
        else:
            assignee = COORDINATORS[i % len(COORDINATORS)]
        due = min(appt_dt - timedelta(days=1), now + timedelta(days=2))
        due_date = max(due.date(), now.date())

        days_out = (appt_dt - now).days
        if days_out <= 1:
            status = str(rng.choice(["Completed", "In Progress", "Pending"],
                                    p=[0.45, 0.30, 0.25]))
        elif days_out <= 4:
            status = str(rng.choice(["Completed", "In Progress", "Pending"],
                                    p=[0.20, 0.25, 0.55]))
        else:
            status = "Pending"
        completed = (now.date() if status == "Completed" else "")
        rows.append({
            "appointment_id": r["appointment_id"],
            "assigned_to": assignee,
            "task_type": task_type,
            "priority": priority,
            "due_date": due_date.isoformat(),
            "task_status": status,
            "completed_date": completed,
        })

    tasks = pd.DataFrame(rows)
    tasks.insert(0, "task_id", range(1, len(tasks) + 1))
    return tasks


def build_manager_tasks(
    provider_util: pd.DataFrame, clinic_stats: pd.DataFrame, now: datetime,
    start_task_id: int,
) -> pd.DataFrame:
    """Operational-review tasks from the utilization and leakage rules:

    - provider utilization below 75%  -> Review Provider Schedule
    - clinic no-show rate above target -> Escalate Access Issue to manager
    """
    rows = []
    low_util = provider_util[provider_util["utilization_rate"] < 0.75]
    for _, p in low_util.iterrows():
        rows.append({
            "appointment_id": "",
            "assigned_to": ACCESS_MANAGER,
            "task_type": "Review Provider Schedule",
            "priority": "Medium",
            "due_date": (now + timedelta(days=3)).date().isoformat(),
            "task_status": "Pending",
            "completed_date": "",
            "context": f"{p['provider_name']} at {p['utilization_rate']:.0%} "
                       f"utilization over the next two weeks (target 75%+).",
        })
    hot_clinics = clinic_stats[
        clinic_stats["no_show_rate"] > clinic_stats["no_show_rate"].mean() + 0.02
    ]
    for _, c in hot_clinics.iterrows():
        rows.append({
            "appointment_id": "",
            "assigned_to": ACCESS_MANAGER,
            "task_type": "Escalate Access Issue",
            "priority": "High",
            "due_date": (now + timedelta(days=2)).date().isoformat(),
            "task_status": "Pending",
            "completed_date": "",
            "context": f"{c['clinic_name']} no-show rate {c['no_show_rate']:.1%} is "
                       "running above the network average — review outreach coverage.",
        })
    tasks = pd.DataFrame(rows)
    if not tasks.empty:
        tasks.insert(0, "task_id", range(start_task_id, start_task_id + len(tasks)))
    return tasks
