"""Build model-ready features for historical and upcoming appointments.

Leakage control: every historical rate (patient, clinic, provider) is computed
from appointments that happened strictly BEFORE the appointment being scored,
using a shifted expanding window. Upcoming appointments use rates computed
from the full historical period, which is exactly what production scoring
would see.

Inputs : data/synthetic/appointments_full.csv, reminder_events.csv
Outputs: data/processed/appointments_features.csv (historical, for training)
         data/processed/upcoming_features.csv     (scheduled, for scoring)
"""

import numpy as np
import pandas as pd

from common import DATA_PROCESSED, DATA_SYNTHETIC, ensure_dirs

SMOOTHING = 20  # pseudo-observations pulling small-sample rates to the mean


def add_reminder_features(df: pd.DataFrame, reminders: pd.DataFrame) -> pd.DataFrame:
    rem = reminders.copy()
    rem["sent_datetime"] = pd.to_datetime(rem["sent_datetime"])
    agg = rem.groupby("appointment_id").agg(
        reminder_count=("reminder_id", "count"),
        last_reminder_sent=("sent_datetime", "max"),
    )
    df = df.merge(agg, on="appointment_id", how="left")
    df["reminder_count"] = df["reminder_count"].fillna(0).astype(int)
    df["last_reminder_hours_before_appt"] = (
        (df["appointment_datetime"] - df["last_reminder_sent"])
        .dt.total_seconds() / 3600.0
    ).round(1)
    return df.drop(columns=["last_reminder_sent"])


def add_patient_history(df: pd.DataFrame, global_rate: float) -> pd.DataFrame:
    """Per-patient prior visit counts and no-show rate (prior visits only)."""
    df = df.sort_values(["appointment_datetime", "appointment_id"]).reset_index(drop=True)
    grp = df.groupby("patient_id")
    df["patient_previous_appointments"] = grp.cumcount()
    outcome = df["no_show_outcome"].fillna(0.0)
    df["patient_previous_no_shows"] = (
        outcome.groupby(df["patient_id"]).cumsum() - outcome
    ).astype(int)
    df["patient_no_show_rate"] = np.where(
        df["patient_previous_appointments"] > 0,
        df["patient_previous_no_shows"] / df["patient_previous_appointments"].replace(0, 1),
        global_rate,
    ).round(4)
    return df


def expanding_group_rate(df: pd.DataFrame, key: str, global_rate: float) -> pd.Series:
    """Smoothed expanding no-show rate per group, excluding the current row."""
    outcome = df["no_show_outcome"].fillna(0.0)
    prior_n = df.groupby(key).cumcount()
    prior_sum = outcome.groupby(df[key]).cumsum() - outcome
    return ((prior_sum + SMOOTHING * global_rate) / (prior_n + SMOOTHING)).round(4)


def main() -> None:
    ensure_dirs()
    appts = pd.read_csv(
        DATA_SYNTHETIC / "appointments_full.csv",
        parse_dates=["scheduled_datetime", "appointment_datetime"],
        dtype={"no_show_flag": str},
    )
    reminders = pd.read_csv(DATA_SYNTHETIC / "reminder_events.csv")

    # Numeric outcome: 1/0 for history, NaN for upcoming (unknown).
    is_hist = appts["appointment_status"].isin(["Completed", "No-Show"])
    appts["no_show_outcome"] = np.where(
        is_hist, appts["no_show_flag"].astype(str).str.lower().eq("true").astype(float), np.nan
    )
    global_rate = appts.loc[is_hist, "no_show_outcome"].mean()

    appts = add_reminder_features(appts, reminders)
    appts = add_patient_history(appts, global_rate)
    appts["clinic_no_show_rate"] = expanding_group_rate(appts, "clinic_id", global_rate)
    appts["provider_no_show_rate"] = expanding_group_rate(appts, "provider_id", global_rate)

    historical = appts[is_hist.reindex(appts.index, fill_value=False)].copy()
    historical["no_show_flag"] = historical["no_show_outcome"].astype(int)
    upcoming = appts[~is_hist.reindex(appts.index, fill_value=False)].copy()
    upcoming = upcoming.drop(columns=["no_show_flag"])

    drop = ["no_show_outcome"]
    historical.drop(columns=drop).to_csv(
        DATA_PROCESSED / "appointments_features.csv", index=False)
    upcoming.drop(columns=drop).to_csv(
        DATA_PROCESSED / "upcoming_features.csv", index=False)

    print(f"Historical feature rows: {len(historical):,} "
          f"(no-show rate {historical['no_show_flag'].mean():.1%})")
    print(f"Upcoming feature rows:   {len(upcoming):,}")
    print(f"Global historical no-show rate used for cold-start priors: {global_rate:.3f}")


if __name__ == "__main__":
    main()
