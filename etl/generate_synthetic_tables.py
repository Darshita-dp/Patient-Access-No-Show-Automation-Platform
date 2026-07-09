"""Generate the synthetic operational tables that the Kaggle dataset lacks.

The Kaggle Medical Appointment No Shows data is a flat historical extract; a
real patient access platform also needs providers, clinics, upcoming
schedules, open slots, a waitlist, reminders, and staff. This script builds
those tables deterministically (seed 42) on top of the cleaned appointments.

Inputs : data/processed/appointments_clean.csv
Outputs: data/synthetic/clinics.csv
         data/synthetic/providers.csv
         data/synthetic/patients.csv
         data/synthetic/appointments_full.csv   (history + next 14 days)
         data/synthetic/open_slots.csv
         data/synthetic/waitlist_requests.csv
         data/synthetic/reminder_events.csv
         data/synthetic/staff_users.csv
         data/synthetic/date_dim.csv
"""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from common import (
    APPOINTMENT_TYPE_WEIGHTS,
    APPOINTMENT_TYPES,
    CLINICS,
    DATA_PROCESSED,
    DATA_SYNTHETIC,
    PROVIDER_FIRST,
    PROVIDER_LAST,
    SEED,
    SPECIALTIES_BY_CLINIC,
    STAFF_USERS,
    ensure_dirs,
)

UPCOMING_DAYS = 14
SLOT_MINUTES = 30
CLINIC_OPEN_HOUR = 8


def build_clinics() -> pd.DataFrame:
    return pd.DataFrame(
        CLINICS,
        columns=["clinic_id", "clinic_name", "location", "service_line", "target_utilization"],
    )


def build_providers(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    pid = 1
    name_idx = rng.permutation(len(PROVIDER_FIRST))
    for clinic_id, specialties in SPECIALTIES_BY_CLINIC.items():
        n_providers = 6
        for i in range(n_providers):
            spec = specialties[i % len(specialties)]
            first = PROVIDER_FIRST[name_idx[(pid - 1) % len(PROVIDER_FIRST)]]
            last = PROVIDER_LAST[name_idx[(pid - 1) % len(PROVIDER_LAST)]]
            rows.append({
                "provider_id": pid,
                "provider_name": f"Dr. {first} {last}",
                "clinic_id": clinic_id,
                "specialty": spec,
                "daily_capacity": int(rng.integers(12, 17)),
            })
            pid += 1
    return pd.DataFrame(rows)


def assign_clinic(age: int, gender: str, patient_id: int) -> int:
    """Deterministic clinic assignment with clinically sensible routing."""
    h = patient_id % 100
    if age < 16:
        return 4 if h < 85 else 1
    if gender == "F" and 16 <= age <= 45 and h < 25:
        return 5
    if h < 12:
        return 6
    if h < 40:
        return 3 if age >= 50 else 2
    return 1 if h < 70 else 2


def build_patients(clean: pd.DataFrame) -> pd.DataFrame:
    latest = clean.sort_values("appointment_datetime").groupby("patient_id").last()
    patients = latest[[
        "gender", "age", "neighborhood", "scholarship_flag", "hypertension_flag",
        "diabetes_flag", "alcoholism_flag", "handicap_flag",
    ]].reset_index()
    # Synthetic display names — clearly labeled so no one mistakes them for PHI.
    patients["patient_name"] = [
        f"Synthetic Patient {i:05d}" for i in range(1, len(patients) + 1)
    ]
    return patients


def attach_operational_columns(
    clean: pd.DataFrame, providers: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Map historical appointments to clinics/providers and add visit metadata."""
    df = clean.copy()
    df["clinic_id"] = [
        assign_clinic(a, g, p)
        for a, g, p in zip(df["age"], df["gender"], df["patient_id"])
    ]
    prov_by_clinic = {
        c: providers.loc[providers["clinic_id"] == c, "provider_id"].to_numpy()
        for c in providers["clinic_id"].unique()
    }
    df["provider_id"] = [
        int(prov_by_clinic[c][pid % len(prov_by_clinic[c])])
        for c, pid in zip(df["clinic_id"], df["patient_id"])
    ]
    spec_map = providers.set_index("provider_id")["specialty"]
    df["specialty"] = df["provider_id"].map(spec_map)

    # The Kaggle appointment day has no time component; assign clinic-hours slots.
    slot_offsets = rng.integers(0, 18, size=len(df))  # 8:00 .. 16:30
    df["appointment_datetime"] = (
        pd.to_datetime(df["appointment_datetime"]).dt.normalize()
        + pd.to_timedelta(CLINIC_OPEN_HOUR * 60 + slot_offsets * SLOT_MINUTES, unit="m")
    )
    df["appointment_hour"] = df["appointment_datetime"].dt.hour
    df["appointment_type"] = rng.choice(
        APPOINTMENT_TYPES, size=len(df), p=APPOINTMENT_TYPE_WEIGHTS
    )
    df["appointment_status"] = np.where(df["no_show_flag"], "No-Show", "Completed")
    return df


def build_upcoming(
    patients: pd.DataFrame, providers: pd.DataFrame, rng: np.random.Generator,
    start_appt_id: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Book the next 14 days of provider schedules; leftover slots stay open."""
    today = date.today()
    booked_rows, open_rows = [], []
    appt_id = start_appt_id
    patient_pool = patients["patient_id"].to_numpy()
    page = patients.set_index("patient_id")

    for _, prov in providers.iterrows():
        for d in range(UPCOMING_DAYS):
            day = today + timedelta(days=d)
            if day.weekday() >= 5:
                continue
            capacity = int(prov["daily_capacity"])
            fill_rate = float(rng.uniform(0.62, 0.92))
            n_booked = int(round(capacity * fill_rate))
            slots = [
                datetime(day.year, day.month, day.day, CLINIC_OPEN_HOUR, 0)
                + timedelta(minutes=SLOT_MINUTES * s)
                for s in range(capacity)
            ]
            booked_slots = list(rng.choice(len(slots), size=n_booked, replace=False))
            for s_idx, slot_dt in enumerate(slots):
                if s_idx not in booked_slots:
                    open_rows.append({
                        "slot_datetime": slot_dt,
                        "provider_id": prov["provider_id"],
                        "clinic_id": prov["clinic_id"],
                        "specialty": prov["specialty"],
                        "slot_status": "Open",
                    })
                    continue
                pid = int(rng.choice(patient_pool))
                lead = int(min(rng.gamma(2.0, 8.0), 90))
                sched = datetime.combine(day, datetime.min.time()) - timedelta(
                    days=lead, hours=int(rng.integers(-8, 8))
                )
                sms = bool(lead >= 3 and rng.random() < 0.68)
                cancelled = rng.random() < 0.055
                prow = page.loc[pid]
                booked_rows.append({
                    "appointment_id": appt_id,
                    "patient_id": pid,
                    "provider_id": prov["provider_id"],
                    "clinic_id": prov["clinic_id"],
                    "specialty": prov["specialty"],
                    "scheduled_datetime": sched,
                    "appointment_datetime": slot_dt,
                    "appointment_status": "Cancelled" if cancelled else "Scheduled",
                    "no_show_flag": "",
                    "sms_received": sms,
                    "gender": prow["gender"],
                    "age": int(prow["age"]),
                    "neighborhood": prow["neighborhood"],
                    "scholarship_flag": bool(prow["scholarship_flag"]),
                    "hypertension_flag": bool(prow["hypertension_flag"]),
                    "diabetes_flag": bool(prow["diabetes_flag"]),
                    "alcoholism_flag": bool(prow["alcoholism_flag"]),
                    "handicap_flag": int(prow["handicap_flag"]),
                    "appointment_type": str(rng.choice(
                        APPOINTMENT_TYPES, p=APPOINTMENT_TYPE_WEIGHTS)),
                })
                if cancelled:
                    open_rows.append({
                        "slot_datetime": slot_dt,
                        "provider_id": prov["provider_id"],
                        "clinic_id": prov["clinic_id"],
                        "specialty": prov["specialty"],
                        "slot_status": "Released (Cancellation)",
                    })
                appt_id += 1

    upcoming = pd.DataFrame(booked_rows)
    upcoming["lead_time_days"] = (
        pd.to_datetime(upcoming["appointment_datetime"]).dt.normalize()
        - pd.to_datetime(upcoming["scheduled_datetime"]).dt.normalize()
    ).dt.days.clip(lower=0)
    upcoming["appointment_day_of_week"] = pd.to_datetime(
        upcoming["appointment_datetime"]).dt.day_name()
    upcoming["scheduled_day_of_week"] = pd.to_datetime(
        upcoming["scheduled_datetime"]).dt.day_name()
    upcoming["appointment_month"] = pd.to_datetime(
        upcoming["appointment_datetime"]).dt.month
    upcoming["is_weekend"] = False
    upcoming["appointment_hour"] = pd.to_datetime(
        upcoming["appointment_datetime"]).dt.hour

    open_slots = pd.DataFrame(open_rows).sort_values("slot_datetime")
    open_slots.insert(0, "slot_id", range(1, len(open_slots) + 1))
    return upcoming, open_slots


def build_waitlist(
    patients: pd.DataFrame, providers: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    today = date.today()
    n = 170
    pids = rng.choice(patients["patient_id"].to_numpy(), size=n, replace=False)
    page = patients.set_index("patient_id")
    rows = []
    windows = [
        "Weekday mornings", "Weekday afternoons", "Any weekday", "Mon/Wed/Fri only",
        "Tue/Thu only", "Mornings before 10am", "After 3pm only", "Any time",
    ]
    for i, pid in enumerate(pids, start=1):
        prov = providers.iloc[int(rng.integers(0, len(providers)))]
        days_waiting = int(rng.gamma(2.2, 9.0)) + 1
        urgency = str(rng.choice(["Routine", "Soon", "Urgent"], p=[0.55, 0.30, 0.15]))
        status = str(rng.choice(
            ["Active", "Active", "Active", "Contacted", "Scheduled Elsewhere"],
            p=[0.55, 0.15, 0.10, 0.12, 0.08]))
        rows.append({
            "waitlist_id": i,
            "patient_id": int(pid),
            "patient_name": page.loc[int(pid), "patient_name"],
            "requested_specialty": prov["specialty"],
            "preferred_clinic_id": int(prov["clinic_id"]),
            "preferred_provider_id": int(prov["provider_id"]) if rng.random() < 0.4 else "",
            "requested_date": (today - timedelta(days=days_waiting)).isoformat(),
            "urgency_level": urgency,
            "availability_window": str(rng.choice(windows)),
            "waitlist_status": status,
        })
    return pd.DataFrame(rows)


def build_reminders(appts_full: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    rid = 1
    sent_mask = appts_full["sms_received"].astype(bool)
    for _, appt in appts_full[sent_mask].iterrows():
        appt_dt = pd.to_datetime(appt["appointment_datetime"])
        is_upcoming = appt["appointment_status"] in ("Scheduled", "Cancelled")
        hours_before = int(rng.choice([24, 48, 72], p=[0.25, 0.35, 0.40]))
        sent_dt = appt_dt - timedelta(hours=hours_before)
        delivery = str(rng.choice(["Delivered", "Delivered", "Delivered", "Failed"],
                                  p=[0.60, 0.20, 0.12, 0.08]))
        if delivery == "Failed":
            response = "No Response"
        elif is_upcoming:
            response = str(rng.choice(
                ["Confirmed", "No Response", "Reschedule Requested", "Declined"],
                p=[0.44, 0.42, 0.09, 0.05]))
        else:
            no_show = bool(appt["no_show_flag"])
            response = str(rng.choice(
                ["No Response", "Confirmed"], p=[0.75, 0.25])) if no_show else str(
                rng.choice(["Confirmed", "No Response"], p=[0.55, 0.45]))
        rows.append({
            "reminder_id": rid,
            "appointment_id": appt["appointment_id"],
            "reminder_type": "SMS",
            "sent_datetime": sent_dt,
            "delivery_status": delivery,
            "patient_response": response,
        })
        rid += 1
    return pd.DataFrame(rows)


def build_date_dim() -> pd.DataFrame:
    today = date.today()
    start = today - timedelta(days=320)
    end = today + timedelta(days=30)
    days = pd.date_range(start, end, freq="D")
    return pd.DataFrame({
        "date_key": days.strftime("%Y%m%d").astype(int),
        "full_date": days.date,
        "year": days.year,
        "month": days.month,
        "month_name": days.strftime("%B"),
        "week_of_year": days.isocalendar().week.astype(int),
        "day_of_week": days.day_name(),
        "is_weekend": days.dayofweek >= 5,
    })


def main() -> None:
    ensure_dirs()
    rng = np.random.default_rng(SEED)
    clean = pd.read_csv(DATA_PROCESSED / "appointments_clean.csv",
                        parse_dates=["scheduled_datetime", "appointment_datetime"])

    clinics = build_clinics()
    providers = build_providers(rng)
    patients = build_patients(clean)
    historical = attach_operational_columns(clean, providers, rng)

    next_id = int(historical["appointment_id"].max()) + 1
    upcoming, open_slots = build_upcoming(patients, providers, rng, next_id)

    hist_cols = historical.assign(no_show_flag=historical["no_show_flag"].astype(bool))
    appts_full = pd.concat([hist_cols, upcoming], ignore_index=True, sort=False)

    waitlist = build_waitlist(patients, providers, rng)
    reminders = build_reminders(appts_full, rng)
    staff = pd.DataFrame(STAFF_USERS, columns=["staff_id", "staff_name", "role"])
    date_dim = build_date_dim()

    outputs = {
        "clinics.csv": clinics,
        "providers.csv": providers,
        "patients.csv": patients,
        "appointments_full.csv": appts_full,
        "open_slots.csv": open_slots,
        "waitlist_requests.csv": waitlist,
        "reminder_events.csv": reminders,
        "staff_users.csv": staff,
        "date_dim.csv": date_dim,
    }
    for name, frame in outputs.items():
        path = DATA_SYNTHETIC / name
        frame.to_csv(path, index=False)
        print(f"Wrote {len(frame):,} rows -> {path.name}")

    n_upcoming = (appts_full["appointment_status"] == "Scheduled").sum()
    print(f"\nUpcoming scheduled appointments (next {UPCOMING_DAYS} days): {n_upcoming:,}")
    print(f"Open slots available for waitlist matching: {len(open_slots):,}")


if __name__ == "__main__":
    main()
