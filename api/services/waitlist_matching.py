"""Waitlist matching engine.

Ranks active waitlist patients against an open appointment slot. The goal is
NOT to hand slots to the riskiest patients — it is to fill the slot with
someone who urgently needs care, has waited longest, fits the slot time, and
is likely to actually attend. That is why low no-show risk scores POSITIVELY.

    waitlist_priority_score =
          urgency_score            * 0.35
        + days_waiting_score       * 0.25
        + availability_match_score * 0.20
        + low_no_show_risk_score   * 0.15
        + same_provider_score      * 0.05
"""

from datetime import datetime

import pandas as pd

WEIGHTS = {
    "urgency": 0.35,
    "days_waiting": 0.25,
    "availability": 0.20,
    "low_risk": 0.15,
    "same_provider": 0.05,
}

URGENCY_SCORES = {"Urgent": 1.0, "Soon": 0.6, "Routine": 0.3}

MORNING_WINDOWS = {"Weekday mornings", "Mornings before 10am"}
AFTERNOON_WINDOWS = {"Weekday afternoons", "After 3pm only"}
ANY_WINDOWS = {"Any weekday", "Any time"}


def availability_match_score(window: str, slot_dt: datetime) -> float:
    """How well the patient's stated availability fits the slot time."""
    hour, dow = slot_dt.hour, slot_dt.weekday()
    if window in ANY_WINDOWS:
        return 1.0
    if window == "Mornings before 10am":
        return 1.0 if hour < 10 else 0.15
    if window in MORNING_WINDOWS:
        return 1.0 if hour < 12 else 0.2
    if window == "After 3pm only":
        return 1.0 if hour >= 15 else 0.15
    if window in AFTERNOON_WINDOWS:
        return 1.0 if hour >= 12 else 0.2
    if window == "Mon/Wed/Fri only":
        return 1.0 if dow in (0, 2, 4) else 0.1
    if window == "Tue/Thu only":
        return 1.0 if dow in (1, 3) else 0.1
    return 0.5  # unknown window text — neutral


def days_waiting_score(days: int) -> float:
    """Saturates at 30 days so extreme waits don't drown other factors."""
    return min(max(days, 0) / 30.0, 1.0)


def build_match_reason(cand: dict, slot: dict) -> str:
    parts = [f"requested {slot['specialty']}"]
    if cand["urgency_level"] == "Urgent":
        parts.append("has urgent clinical priority")
    elif cand["urgency_level"] == "Soon":
        parts.append("has elevated priority")
    parts.append(f"has waited {cand['days_waiting']} days")
    if cand["availability_score"] >= 0.99:
        parts.append("is available during the open appointment window")
    if cand["same_provider_score"] > 0:
        parts.append("prefers this provider")
    if cand["low_risk_score"] >= 0.8:
        parts.append("has a strong attendance history")
    return "Matched because patient " + ", ".join(parts) + "."


def rank_candidates_for_slot(
    slot: dict,
    waitlist: pd.DataFrame,
    patient_risk: dict[int, float],
    now: datetime,
    top_n: int = 5,
) -> list[dict]:
    """Score every eligible waitlist patient against one open slot.

    slot: {slot_id, slot_datetime, provider_id, clinic_id, specialty}
    patient_risk: patient_id -> historical/predicted no-show rate (0-1)
    """
    slot_dt = pd.to_datetime(slot["slot_datetime"]).to_pydatetime()

    eligible = waitlist[
        (waitlist["requested_specialty"] == slot["specialty"])
        & (waitlist["waitlist_status"].isin(["Active", "Contacted"]))
        & (
            (waitlist["preferred_clinic_id"].isna())
            | (waitlist["preferred_clinic_id"] == slot["clinic_id"])
        )
    ]

    results = []
    for _, w in eligible.iterrows():
        days = int((now.date() - pd.to_datetime(w["requested_date"]).date()).days)
        risk = float(patient_risk.get(int(w["patient_id"]), 0.2))
        preferred = w.get("preferred_provider_id")
        same_provider = float(
            pd.notna(preferred) and str(preferred) not in ("", "nan")
            and int(float(preferred)) == int(slot["provider_id"])
        )
        components = {
            "urgency_score": URGENCY_SCORES.get(w["urgency_level"], 0.3),
            "days_waiting_raw": days,
            "availability_score": availability_match_score(
                str(w["availability_window"]), slot_dt),
            "low_risk_score": round(1.0 - min(risk, 1.0), 4),
            "same_provider_score": same_provider,
        }
        score = (
            components["urgency_score"] * WEIGHTS["urgency"]
            + days_waiting_score(days) * WEIGHTS["days_waiting"]
            + components["availability_score"] * WEIGHTS["availability"]
            + components["low_risk_score"] * WEIGHTS["low_risk"]
            + components["same_provider_score"] * WEIGHTS["same_provider"]
        )
        cand = {
            "waitlist_id": int(w["waitlist_id"]),
            "patient_id": int(w["patient_id"]),
            "patient_name": w.get("patient_name", ""),
            "urgency_level": w["urgency_level"],
            "days_waiting": days,
            "availability_window": w["availability_window"],
            "match_score": round(float(score), 4),
            **components,
        }
        cand["match_reason"] = build_match_reason(cand, slot)
        results.append(cand)

    results.sort(key=lambda c: c["match_score"], reverse=True)
    return results[:top_n]


def build_match_results(
    open_slots: pd.DataFrame,
    waitlist: pd.DataFrame,
    patient_risk: dict[int, float],
    now: datetime,
    top_n_per_slot: int = 3,
) -> pd.DataFrame:
    """Batch-match every future open slot; returns the persistable result set."""
    rows = []
    match_id = 1
    for _, s in open_slots.iterrows():
        slot = s.to_dict()
        if pd.to_datetime(slot["slot_datetime"]) < now:
            continue
        for rank, cand in enumerate(
            rank_candidates_for_slot(slot, waitlist, patient_risk, now,
                                     top_n=top_n_per_slot), start=1):
            rows.append({
                "match_id": match_id,
                "slot_id": slot["slot_id"],
                "waitlist_id": cand["waitlist_id"],
                "appointment_id": "",
                "match_rank": rank,
                "match_score": cand["match_score"],
                "match_reason": cand["match_reason"],
                "created_at": now.isoformat(timespec="seconds"),
            })
            match_id += 1
    return pd.DataFrame(rows)
