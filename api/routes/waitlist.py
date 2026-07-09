"""Waitlist queue, open slots, and match endpoints."""

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api.database import df_records, get_store
from api.services.waitlist_matching import rank_candidates_for_slot

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


def _waitlist_view(store) -> pd.DataFrame:
    wl = store.waitlist.merge(
        store.patients[["patient_id", "patient_name"]],
        on="patient_id", how="left", suffixes=("", "_p"))
    if "patient_name_p" in wl.columns:
        wl["patient_name"] = wl["patient_name"].fillna(wl["patient_name_p"])
        wl = wl.drop(columns=["patient_name_p"])
    wl = wl.merge(
        store.clinics[["clinic_id", "clinic_name"]].rename(
            columns={"clinic_id": "preferred_clinic_id",
                     "clinic_name": "preferred_clinic"}),
        on="preferred_clinic_id", how="left")
    wl["days_waiting"] = (
        pd.Timestamp.now().normalize() - pd.to_datetime(wl["requested_date"])
    ).dt.days
    return wl


@router.get("")
def list_waitlist(
    specialty: str | None = None,
    urgency: str | None = None,
    status: str | None = Query(None, description="Default: Active + Contacted"),
):
    store = get_store()
    wl = _waitlist_view(store)
    wl = wl[wl["waitlist_status"].isin(["Active", "Contacted"])] if not status \
        else wl[wl["waitlist_status"] == status]
    if specialty:
        wl = wl[wl["requested_specialty"] == specialty]
    if urgency:
        wl = wl[wl["urgency_level"] == urgency]

    urgency_rank = {"Urgent": 0, "Soon": 1, "Routine": 2}
    wl = wl.assign(_u=wl["urgency_level"].map(urgency_rank)) \
           .sort_values(["_u", "days_waiting"], ascending=[True, False]) \
           .drop(columns="_u")
    return {
        "count": len(wl),
        "average_days_waiting": round(float(wl["days_waiting"].mean()), 1)
        if len(wl) else 0,
        "waitlist": df_records(wl),
    }


@router.get("/slots")
def open_slots_with_matches(
    clinic_id: int | None = None,
    specialty: str | None = None,
    days_ahead: int = Query(14, le=30),
    limit: int = Query(40, le=200),
):
    """Open + released slots with their best waitlist matches — the Waitlist
    Manager's main worklist, ordered soonest first."""
    store = get_store()
    now = datetime.now()
    horizon = now + pd.Timedelta(days=days_ahead)

    slots = store.open_slots
    slots = slots[(slots["slot_datetime"] >= now) & (slots["slot_datetime"] <= horizon)]
    if clinic_id:
        slots = slots[slots["clinic_id"] == clinic_id]
    if specialty:
        slots = slots[slots["specialty"] == specialty]
    slots = slots.sort_values("slot_datetime").head(limit)

    slots = slots.merge(store.clinics[["clinic_id", "clinic_name"]],
                        on="clinic_id", how="left")
    slots = slots.merge(store.providers[["provider_id", "provider_name"]],
                        on="provider_id", how="left")

    wl = _waitlist_view(store)
    out = []
    for _, s in slots.iterrows():
        cands = rank_candidates_for_slot(s.to_dict(), wl, store.patient_risk,
                                         now, top_n=3)
        out.append({
            **df_records(s.to_frame().T)[0],
            "match_count": len(cands),
            "top_matches": cands,
        })
    return {"count": len(out), "slots": out}


@router.get("/matches/{appointment_id}")
def matches_for_appointment(appointment_id: int):
    """Ranked waitlist candidates who could take this appointment's slot if
    the patient cancels or is released."""
    store = get_store()
    match = store.worklist[store.worklist["appointment_id"] == appointment_id]
    if match.empty:
        raise HTTPException(404, f"Appointment {appointment_id} not found.")
    appt = match.iloc[0]

    slot = {
        "slot_id": None,
        "slot_datetime": appt["appointment_datetime"],
        "provider_id": appt["provider_id"],
        "clinic_id": appt["clinic_id"],
        "specialty": appt["specialty"],
    }
    wl = _waitlist_view(store)
    candidates = rank_candidates_for_slot(slot, wl, store.patient_risk,
                                          datetime.now(), top_n=5)
    return {
        "appointment_id": appointment_id,
        "slot_datetime": str(appt["appointment_datetime"]),
        "specialty": appt["specialty"],
        "match_count": len(candidates),
        "candidates": candidates,
    }


@router.post("/{waitlist_id}/status")
def update_waitlist_status(waitlist_id: int, status: str = Query(
        ..., pattern="^(Active|Contacted|Offered|Accepted|Declined|Scheduled Elsewhere)$")):
    """Offer / accept / decline flow for the Waitlist Manager UI."""
    store = get_store()
    idx = store.waitlist["waitlist_id"] == waitlist_id
    if not idx.any():
        raise HTTPException(404, f"Waitlist request {waitlist_id} not found.")
    store.waitlist.loc[idx, "waitlist_status"] = status
    return {"waitlist_id": waitlist_id, "waitlist_status": status,
            "message": f"Waitlist request marked {status}."}
