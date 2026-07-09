"""Provider directory and daily schedule endpoints."""

from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api.database import df_records, get_store

router = APIRouter(prefix="/providers", tags=["providers"])

WEEKDAYS_IN_WINDOW = 10  # next 14 calendar days = 10 clinic days


@router.get("")
def list_providers(clinic_id: int | None = None):
    """Providers with utilization and risk load over the next two weeks."""
    store = get_store()
    providers = store.providers
    if clinic_id:
        providers = providers[providers["clinic_id"] == clinic_id]

    upcoming = store.worklist[store.worklist["appointment_status"] == "Scheduled"]
    agg = upcoming.groupby("provider_id").agg(
        booked=("appointment_id", "count"),
        high_risk=("risk_category", lambda s: int((s == "High").sum())),
        avg_probability=("no_show_probability", "mean"),
    )
    out = providers.merge(agg, on="provider_id", how="left").fillna(
        {"booked": 0, "high_risk": 0})
    out = out.merge(store.clinics[["clinic_id", "clinic_name"]], on="clinic_id")
    out["capacity_two_weeks"] = out["daily_capacity"] * WEEKDAYS_IN_WINDOW
    out["utilization_rate"] = (out["booked"] / out["capacity_two_weeks"]).round(4)
    out["avg_probability"] = out["avg_probability"].round(4)
    out = out.sort_values("utilization_rate")
    return {"count": len(out), "providers": df_records(out)}


@router.get("/{provider_id}/schedule")
def provider_schedule(
    provider_id: int,
    date: str | None = Query(None, description="YYYY-MM-DD; defaults to today"),
    days: int = Query(5, le=14),
):
    """Day-by-day slot view: booked visits with risk, plus open slots."""
    store = get_store()
    prow = store.providers[store.providers["provider_id"] == provider_id]
    if prow.empty:
        raise HTTPException(404, f"Provider {provider_id} not found.")
    provider = prow.iloc[0]
    clinic = store.clinics[store.clinics["clinic_id"] == provider["clinic_id"]].iloc[0]

    start = pd.Timestamp(date).normalize() if date else pd.Timestamp.now().normalize()

    schedule_days = []
    d = start
    while len(schedule_days) < days:
        if d.weekday() < 5:
            schedule_days.append(d)
        d += timedelta(days=1)

    appts = store.worklist[
        (store.worklist["provider_id"] == provider_id)
        & (store.worklist["appointment_datetime"] >= start)
        & (store.worklist["appointment_datetime"] < schedule_days[-1] + timedelta(days=1))
    ]
    slots = store.open_slots[
        (store.open_slots["provider_id"] == provider_id)
        & (store.open_slots["slot_datetime"] >= start)
        & (store.open_slots["slot_datetime"] < schedule_days[-1] + timedelta(days=1))
    ]

    days_out = []
    for day in schedule_days:
        day_appts = appts[appts["appointment_datetime"].dt.date == day.date()] \
            .sort_values("appointment_datetime")
        day_slots = slots[slots["slot_datetime"].dt.date == day.date()]
        booked = day_appts[day_appts["appointment_status"] == "Scheduled"]
        cancelled = day_appts[day_appts["appointment_status"] == "Cancelled"]
        high_risk = int((booked["risk_category"] == "High").sum())
        capacity = int(provider["daily_capacity"])
        utilization = round(len(booked) / capacity, 4) if capacity else None

        days_out.append({
            "date": day.date().isoformat(),
            "day_of_week": day.day_name(),
            "capacity": capacity,
            "booked": len(booked),
            "cancelled": len(cancelled),
            "open_slots": int((day_slots["slot_status"] == "Open").sum()),
            "released_slots": int(
                (day_slots["slot_status"] == "Released (Cancellation)").sum()),
            "high_risk_appointments": high_risk,
            "utilization_rate": utilization,
            "insight": (
                f"{provider['provider_name']} is at {utilization:.0%} utilization "
                f"on {day.day_name()}"
                + (f" with {high_risk} high-risk appointment"
                   f"{'s' if high_risk != 1 else ''} to protect." if high_risk
                   else ".")
            ),
            "appointments": df_records(day_appts[[
                "appointment_id", "appointment_datetime", "patient_name",
                "appointment_type", "appointment_status", "no_show_probability",
                "risk_category", "recommended_action", "reminder_status",
            ]]),
        })

    return {
        "provider": {
            "provider_id": int(provider["provider_id"]),
            "provider_name": provider["provider_name"],
            "specialty": provider["specialty"],
            "clinic_name": clinic["clinic_name"],
            "daily_capacity": int(provider["daily_capacity"]),
        },
        "start_date": start.date().isoformat(),
        "days": days_out,
    }
