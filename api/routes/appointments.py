"""Appointment queue, search, detail, and reminder simulation endpoints."""

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api.database import df_records, get_store
from api.services.action_engine import build_risk_explanation
from api.services.waitlist_matching import rank_candidates_for_slot

router = APIRouter(prefix="/appointments", tags=["appointments"])

QUEUE_COLUMNS = [
    "appointment_id", "appointment_datetime", "patient_id", "patient_name",
    "clinic_id", "clinic_name", "provider_id", "provider_name", "specialty",
    "appointment_type", "appointment_status", "lead_time_days",
    "no_show_probability", "risk_category", "recommended_action", "priority",
    "reminder_status", "task_id", "task_status", "assigned_to",
]

RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2}


@router.get("")
def list_appointments(
    risk_category: str | None = None,
    clinic_id: int | None = None,
    provider_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    task_status: str | None = None,
    reminder_status: str | None = None,
    status: str = "Scheduled",
    sort: str = Query("risk", pattern="^(risk|time|probability)$"),
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """The appointment work queue with the filters the UI exposes."""
    store = get_store()
    df = store.worklist
    df = df[df["appointment_status"] == status] if status != "All" else df

    if risk_category:
        df = df[df["risk_category"] == risk_category]
    if clinic_id:
        df = df[df["clinic_id"] == clinic_id]
    if provider_id:
        df = df[df["provider_id"] == provider_id]
    if date_from:
        df = df[df["appointment_datetime"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["appointment_datetime"] <= pd.Timestamp(date_to) + pd.Timedelta(days=1)]
    if task_status:
        if task_status == "No Task":
            df = df[df["task_status"].isna()]
        else:
            df = df[df["task_status"] == task_status]
    if reminder_status:
        df = df[df["reminder_status"] == reminder_status]

    if sort == "risk":
        df = df.assign(_r=df["risk_category"].map(RISK_ORDER).fillna(3)).sort_values(
            ["_r", "appointment_datetime"]).drop(columns="_r")
    elif sort == "probability":
        df = df.sort_values("no_show_probability", ascending=False)
    else:
        df = df.sort_values("appointment_datetime")

    total = len(df)
    page = df.iloc[offset:offset + limit]
    return {"total": total, "count": len(page),
            "appointments": df_records(page[QUEUE_COLUMNS])}


@router.get("/search")
def search_appointments(
    q: str | None = Query(None, description="Patient ID, appointment ID, or patient name"),
    clinic_id: int | None = None,
    provider_id: int | None = None,
    date: str | None = None,
    risk_category: str | None = None,
    limit: int = Query(50, le=200),
):
    """Search across upcoming AND historical appointments."""
    store = get_store()
    df = store.worklist

    if q:
        q_str = q.strip()
        mask = df["patient_name"].str.contains(q_str, case=False, na=False)
        if q_str.isdigit():
            num = int(q_str)
            mask = mask | (df["appointment_id"] == num) | (df["patient_id"] == num) \
                | df["patient_id"].astype(str).str.startswith(q_str) \
                | df["appointment_id"].astype(str).str.startswith(q_str)
        df = df[mask]
    if clinic_id:
        df = df[df["clinic_id"] == clinic_id]
    if provider_id:
        df = df[df["provider_id"] == provider_id]
    if date:
        df = df[df["appointment_datetime"].dt.date == pd.Timestamp(date).date()]
    if risk_category:
        df = df[df["risk_category"] == risk_category]

    df = df.sort_values("appointment_datetime").head(limit)
    return {"count": len(df), "results": df_records(df[QUEUE_COLUMNS])}


@router.get("/{appointment_id}")
def appointment_detail(appointment_id: int):
    store = get_store()
    match = store.worklist[store.worklist["appointment_id"] == appointment_id]
    if match.empty:
        raise HTTPException(404, f"Appointment {appointment_id} not found on the "
                            "upcoming schedule.")
    appt = match.iloc[0]
    patient_id = int(appt["patient_id"])

    patient = store.patients[store.patients["patient_id"] == patient_id].iloc[0]
    history = store.patient_history(patient_id)
    prev_total = len(history)
    prev_no_shows = int(history["no_show_bool"].sum())

    feature_row = store.upcoming_features[
        store.upcoming_features["appointment_id"] == appointment_id]
    features = feature_row.iloc[0].to_dict() if not feature_row.empty else {}

    explanation = build_risk_explanation({
        "lead_time_days": appt["lead_time_days"],
        "patient_previous_no_shows": features.get("patient_previous_no_shows",
                                                  prev_no_shows),
        "patient_previous_appointments": features.get("patient_previous_appointments",
                                                      prev_total),
        "sms_received": appt["sms_received"],
        "patient_response": appt["patient_response"],
        "age": patient["age"],
        "risk_category": appt["risk_category"],
        "no_show_probability": appt["no_show_probability"],
    })

    reminders = store.reminders[store.reminders["appointment_id"] == appointment_id] \
        .sort_values("sent_datetime", ascending=False)

    # Waitlist replacement option: who could take this slot if it releases.
    slot = {
        "slot_id": None,
        "slot_datetime": appt["appointment_datetime"],
        "provider_id": appt["provider_id"],
        "clinic_id": appt["clinic_id"],
        "specialty": appt["specialty"],
    }
    wl = store.waitlist.merge(store.patients[["patient_id", "patient_name"]],
                              on="patient_id", how="left",
                              suffixes=("", "_p"))
    candidates = rank_candidates_for_slot(slot, wl, store.patient_risk,
                                          datetime.now(), top_n=3)

    appt_tasks = store.tasks[store.tasks["appointment_id"] == appointment_id]

    return {
        "appointment": df_records(match[QUEUE_COLUMNS + [
            "scheduled_datetime", "sms_received"]])[0],
        "patient": {
            "patient_id": patient_id,
            "patient_name": patient["patient_name"],
            "gender": patient["gender"],
            "age": int(patient["age"]),
            "neighborhood": patient["neighborhood"],
            "conditions": [name for flag, name in [
                (patient["hypertension_flag"], "Hypertension"),
                (patient["diabetes_flag"], "Diabetes"),
                (patient["alcoholism_flag"], "Alcohol use disorder"),
            ] if flag],
            "scholarship": bool(patient["scholarship_flag"]),
            "mobility_support_level": int(patient["handicap_flag"]),
        },
        "risk_explanation": explanation,
        "previous_behavior": {
            "total_visits": prev_total,
            "no_shows": prev_no_shows,
            "no_show_rate": round(prev_no_shows / prev_total, 3) if prev_total else None,
            "recent_visits": df_records(history.head(6)[[
                "appointment_id", "appointment_datetime", "clinic_name",
                "provider_name", "appointment_status"]]),
        },
        "reminder_history": df_records(reminders[[
            "reminder_id", "reminder_type", "sent_datetime", "delivery_status",
            "patient_response"]]),
        "waitlist_replacement": {
            "available": len(candidates) > 0,
            "candidates": candidates,
        },
        "tasks": df_records(appt_tasks[[
            "task_id", "task_type", "priority", "assigned_to", "due_date",
            "task_status", "completed_date"]]),
    }


@router.post("/{appointment_id}/send-reminder")
def send_reminder(appointment_id: int):
    """Simulate sending an SMS reminder (mutates the in-memory store)."""
    store = get_store()
    match = store.worklist[store.worklist["appointment_id"] == appointment_id]
    if match.empty:
        raise HTTPException(404, f"Appointment {appointment_id} not found.")

    now = datetime.now()
    new_reminder = {
        "reminder_id": store.next_reminder_id(),
        "appointment_id": appointment_id,
        "reminder_type": "SMS",
        "sent_datetime": now,
        "delivery_status": "Delivered",
        "patient_response": "No Response",
    }
    store.reminders = pd.concat(
        [store.reminders, pd.DataFrame([new_reminder])], ignore_index=True)
    idx = store.worklist["appointment_id"] == appointment_id
    store.worklist.loc[idx, "reminder_status"] = "Sent — No Response"
    store.worklist.loc[idx, "sms_received"] = True

    return {"status": "sent",
            "message": f"SMS reminder queued for appointment {appointment_id}.",
            "reminder": {**new_reminder,
                         "sent_datetime": now.isoformat(timespec="seconds")}}


@router.post("/{appointment_id}/mark-contacted")
def mark_contacted(appointment_id: int):
    """Record that staff reached the patient; completes any open task."""
    store = get_store()
    idx = store.worklist["appointment_id"] == appointment_id
    if not idx.any():
        raise HTTPException(404, f"Appointment {appointment_id} not found.")

    today = datetime.now().date().isoformat()
    task_idx = (store.tasks["appointment_id"] == appointment_id) & \
               (store.tasks["task_status"] != "Completed")
    completed = int(task_idx.sum())
    store.tasks.loc[task_idx, ["task_status", "completed_date"]] = ["Completed", today]
    store.worklist.loc[idx, "task_status"] = "Completed"
    store.worklist.loc[idx, "reminder_status"] = "Confirmed"
    return {"status": "contacted", "tasks_completed": completed,
            "message": "Patient marked as contacted; open outreach tasks closed."}
