"""Command Center summary — one call drives the landing page."""

from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter

from api.database import df_records, get_store
from api.routes.appointments import QUEUE_COLUMNS

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary():
    store = get_store()
    now = datetime.now()
    today = now.date()

    wl = store.worklist
    scheduled = wl[wl["appointment_status"] == "Scheduled"]
    today_appts = scheduled[scheduled["appointment_datetime"].dt.date == today]
    high_risk = scheduled[scheduled["risk_category"] == "High"]

    hist = store.appointments[store.appointments["is_historical"]]
    no_show_rate = float(hist["no_show_bool"].mean())

    future_slots = store.open_slots[store.open_slots["slot_datetime"] >= now]
    open_slots = int((future_slots["slot_status"] == "Open").sum())
    released = future_slots[future_slots["slot_status"] == "Released (Cancellation)"]
    matched_ids = set(store.matches["slot_id"].unique())
    recoverable = int(released["slot_id"].isin(matched_ids).sum())

    active_waitlist = store.waitlist[
        store.waitlist["waitlist_status"].isin(["Active", "Contacted"])]

    capacity = int(store.providers["daily_capacity"].sum()) * 10
    provider_utilization = round(len(scheduled) / capacity, 4) if capacity else None

    tasks = store.tasks
    pending_tasks = int((tasks["task_status"].isin(["Pending", "In Progress"])).sum())
    overdue = int(((tasks["task_status"] != "Completed")
                   & (pd.to_datetime(tasks["due_date"])
                      < pd.Timestamp.now().normalize())).sum())

    # High-risk visits needing action in the next 48h, most probable first.
    outreach = high_risk[
        (high_risk["appointment_datetime"] >= now)
        & (high_risk["appointment_datetime"] <= now + timedelta(hours=48))
        & (high_risk["task_status"].fillna("") != "Completed")
    ].sort_values("no_show_probability", ascending=False).head(8)

    # Released slots (cancellations) with waitlist matches ready to offer.
    slot_matches = released[released["slot_id"].isin(matched_ids)] \
        .sort_values("slot_datetime").head(8)
    slot_matches = slot_matches.merge(
        store.clinics[["clinic_id", "clinic_name"]], on="clinic_id", how="left")
    slot_matches = slot_matches.merge(
        store.providers[["provider_id", "provider_name"]], on="provider_id",
        how="left")
    best = store.matches[store.matches["match_rank"] == 1][
        ["slot_id", "match_score", "match_reason", "waitlist_id"]]
    slot_matches = slot_matches.merge(best, on="slot_id", how="left")

    # Manager alerts: clinics above network no-show average, low-utilization
    # providers, and overdue outreach.
    alerts = []
    clinic_ns = hist.groupby("clinic_id")["no_show_bool"].mean()
    for clinic_id, rate in clinic_ns.items():
        if rate > no_show_rate + 0.02:
            name = store.clinics.loc[
                store.clinics["clinic_id"] == clinic_id, "clinic_name"].iloc[0]
            alerts.append({
                "severity": "high",
                "title": f"{name} no-show rate {rate:.1%}",
                "detail": f"Running {rate - no_show_rate:+.1%} vs. the network "
                          f"average of {no_show_rate:.1%}. Review outreach coverage.",
            })
    prov_booked = scheduled.groupby("provider_id").size()
    for _, p in store.providers.iterrows():
        util = prov_booked.get(p["provider_id"], 0) / (p["daily_capacity"] * 10)
        if util < 0.68:
            alerts.append({
                "severity": "medium",
                "title": f"{p['provider_name']} at {util:.0%} utilization",
                "detail": "Schedule is under target for the next two weeks — "
                          "review open slots for waitlist placement.",
            })
    if overdue:
        alerts.append({
            "severity": "high",
            "title": f"{overdue} outreach tasks overdue",
            "detail": "High-risk appointments may go unworked — reassign or "
                      "escalate in the Action Tracker.",
        })
    severity_rank = {"high": 0, "medium": 1}
    alerts = sorted(alerts, key=lambda a: severity_rank.get(a["severity"], 2))[:6]

    trend = (
        scheduled.assign(day=scheduled["appointment_datetime"].dt.date.astype(str))
        .groupby("day").agg(
            booked=("appointment_id", "count"),
            high_risk=("risk_category", lambda s: int((s == "High").sum())),
        ).reset_index()
    )

    return {
        "as_of": now.isoformat(timespec="seconds"),
        "cards": {
            "appointments_today": len(today_appts),
            "high_risk_appointments": len(high_risk),
            "no_show_rate": round(no_show_rate, 4),
            "open_slots": open_slots,
            "waitlist_patients": len(active_waitlist),
            "provider_utilization": provider_utilization,
            "pending_staff_actions": pending_tasks,
            "recovered_slots": recoverable,
        },
        "high_risk_needing_action": df_records(outreach[QUEUE_COLUMNS]),
        "open_slots_with_matches": df_records(slot_matches),
        "utilization_trend": df_records(trend),
        "manager_alerts": alerts,
    }
