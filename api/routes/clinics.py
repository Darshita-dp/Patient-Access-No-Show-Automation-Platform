"""Clinic directory and utilization endpoints."""

from datetime import datetime

import pandas as pd
from fastapi import APIRouter

from api.database import df_records, get_store

router = APIRouter(prefix="/clinics", tags=["clinics"])

WEEKDAYS_IN_WINDOW = 10


@router.get("")
def list_clinics():
    store = get_store()
    return {"clinics": df_records(store.clinics)}


@router.get("/utilization")
def clinic_utilization():
    """Capacity, bookings, leakage, and recovery metrics per clinic.

    Utilization        = booked / available slots (next two weeks)
    Recovered slots    = released-by-cancellation slots that have at least
                         one waitlist match candidate
    Potential util.    = (booked + recoverable) / available slots
    """
    store = get_store()
    now = datetime.now()

    capacity = store.providers.groupby("clinic_id")["daily_capacity"].sum() \
        * WEEKDAYS_IN_WINDOW
    upcoming = store.worklist[store.worklist["appointment_datetime"] >= now]
    booked = upcoming[upcoming["appointment_status"] == "Scheduled"] \
        .groupby("clinic_id").size()
    cancelled = upcoming[upcoming["appointment_status"] == "Cancelled"] \
        .groupby("clinic_id").size()
    high_risk = upcoming[(upcoming["appointment_status"] == "Scheduled")
                         & (upcoming["risk_category"] == "High")] \
        .groupby("clinic_id").size()

    future_slots = store.open_slots[store.open_slots["slot_datetime"] >= now]
    open_count = future_slots[future_slots["slot_status"] == "Open"] \
        .groupby("clinic_id").size()
    released = future_slots[future_slots["slot_status"] == "Released (Cancellation)"]
    matched_slot_ids = set(store.matches["slot_id"].unique())
    recoverable = released[released["slot_id"].isin(matched_slot_ids)] \
        .groupby("clinic_id").size()

    hist = store.appointments[store.appointments["is_historical"]]
    no_show_rate = hist.groupby("clinic_id")["no_show_bool"].mean()
    completed = hist[~hist["no_show_bool"]].groupby("clinic_id").size()

    out = store.clinics.copy()
    out["available_slots"] = out["clinic_id"].map(capacity).fillna(0).astype(int)
    out["booked_appointments"] = out["clinic_id"].map(booked).fillna(0).astype(int)
    out["cancelled_appointments"] = out["clinic_id"].map(cancelled).fillna(0).astype(int)
    out["high_risk_appointments"] = out["clinic_id"].map(high_risk).fillna(0).astype(int)
    out["open_slots"] = out["clinic_id"].map(open_count).fillna(0).astype(int)
    out["recoverable_slots"] = out["clinic_id"].map(recoverable).fillna(0).astype(int)
    out["historical_no_show_rate"] = out["clinic_id"].map(no_show_rate).round(4)
    out["historical_completed"] = out["clinic_id"].map(completed).fillna(0).astype(int)
    out["utilization_rate"] = (
        out["booked_appointments"] / out["available_slots"].replace(0, pd.NA)
    ).astype(float).round(4)
    out["potential_utilization"] = (
        (out["booked_appointments"] + out["recoverable_slots"])
        / out["available_slots"].replace(0, pd.NA)
    ).astype(float).round(4)
    out["gap_to_target"] = (out["utilization_rate"] - out["target_utilization"]).round(4)

    # Daily booked trend for the utilization chart.
    trend = (
        upcoming[upcoming["appointment_status"] == "Scheduled"]
        .assign(day=upcoming[upcoming["appointment_status"] == "Scheduled"]
                ["appointment_datetime"].dt.date.astype(str))
        .groupby(["day", "clinic_id"]).size().rename("booked").reset_index()
    )
    trend = trend.merge(store.clinics[["clinic_id", "clinic_name"]], on="clinic_id")

    return {
        "as_of": now.isoformat(timespec="seconds"),
        "window_days": 14,
        "clinics": df_records(out.sort_values("utilization_rate")),
        "daily_trend": df_records(trend),
    }
