"""Risk-focused endpoints: the high-risk outreach list and risk mix."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from api.database import df_records, get_store
from api.routes.appointments import QUEUE_COLUMNS

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/high")
def high_risk_appointments(
    hours_ahead: int = Query(72, description="Look-ahead window in hours"),
    limit: int = Query(50, le=200),
):
    """High-risk scheduled appointments inside the outreach window — the
    'who needs a call today' list."""
    store = get_store()
    now = datetime.now()
    horizon = now + timedelta(hours=hours_ahead)

    df = store.worklist
    df = df[
        (df["appointment_status"] == "Scheduled")
        & (df["risk_category"] == "High")
        & (df["appointment_datetime"] >= now)
        & (df["appointment_datetime"] <= horizon)
    ].sort_values("no_show_probability", ascending=False)

    return {
        "window_hours": hours_ahead,
        "total_high_risk_in_window": len(df),
        "appointments": df_records(df.head(limit)[QUEUE_COLUMNS]),
    }


@router.get("/summary")
def risk_summary():
    """Risk mix across the entire upcoming schedule."""
    store = get_store()
    df = store.worklist
    scheduled = df[df["appointment_status"] == "Scheduled"]

    mix = scheduled["risk_category"].value_counts().to_dict()
    by_day = (
        scheduled.assign(day=scheduled["appointment_datetime"].dt.date.astype(str))
        .groupby(["day", "risk_category"]).size().unstack(fill_value=0)
        .reset_index()
    )
    return {
        "scheduled_appointments": len(scheduled),
        "risk_mix": {
            "High": int(mix.get("High", 0)),
            "Medium": int(mix.get("Medium", 0)),
            "Low": int(mix.get("Low", 0)),
        },
        "average_no_show_probability": round(
            float(scheduled["no_show_probability"].mean()), 4),
        "by_day": df_records(by_day),
    }
