"""Clean and standardize the raw appointment dataset.

- snake_case column names
- typed dates, boolean target
- impossible-age and negative-lead-time removal
- calendar features (day of week, month, weekend)

Input : data/raw/appointments_raw.csv
Output: data/processed/appointments_clean.csv
"""

import pandas as pd

from common import DATA_PROCESSED, DATA_RAW, ensure_dirs

RENAME_MAP = {
    "PatientId": "patient_id",
    "AppointmentID": "appointment_id",
    "Gender": "gender",
    "ScheduledDay": "scheduled_datetime",
    "AppointmentDay": "appointment_datetime",
    "Age": "age",
    "Neighbourhood": "neighborhood",
    "Scholarship": "scholarship_flag",
    "Hipertension": "hypertension_flag",
    "Diabetes": "diabetes_flag",
    "Alcoholism": "alcoholism_flag",
    "Handcap": "handicap_flag",
    "SMS_received": "sms_received",
    "No-show": "no_show_flag",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=RENAME_MAP)

    df["patient_id"] = df["patient_id"].astype("int64")
    df["appointment_id"] = df["appointment_id"].astype("int64")

    df["scheduled_datetime"] = pd.to_datetime(df["scheduled_datetime"], utc=True).dt.tz_localize(None)
    df["appointment_datetime"] = pd.to_datetime(df["appointment_datetime"], utc=True).dt.tz_localize(None)

    df["no_show_flag"] = df["no_show_flag"].astype(str).str.strip().str.lower().eq("yes")
    for col in ["scholarship_flag", "hypertension_flag", "diabetes_flag",
                "alcoholism_flag", "sms_received"]:
        df[col] = df[col].astype(int).astype(bool)
    df["handicap_flag"] = df["handicap_flag"].astype(int)
    df["gender"] = df["gender"].astype(str).str.upper().str[0]

    # Remove impossible ages (Kaggle contains age = -1 and extreme outliers).
    before = len(df)
    df = df[(df["age"] >= 0) & (df["age"] <= 100)]

    # Lead time in days; scheduling timestamps after the visit day are data errors.
    df["lead_time_days"] = (
        df["appointment_datetime"].dt.normalize() - df["scheduled_datetime"].dt.normalize()
    ).dt.days
    df = df[df["lead_time_days"] >= 0]

    df = df.drop_duplicates(subset=["appointment_id"])
    removed = before - len(df)

    # Calendar features.
    df["appointment_day_of_week"] = df["appointment_datetime"].dt.day_name()
    df["scheduled_day_of_week"] = df["scheduled_datetime"].dt.day_name()
    df["appointment_month"] = df["appointment_datetime"].dt.month
    df["is_weekend"] = df["appointment_datetime"].dt.dayofweek >= 5

    print(f"Removed {removed:,} invalid rows (bad age, negative lead time, duplicates).")
    return df.sort_values("appointment_datetime").reset_index(drop=True)


def main() -> None:
    ensure_dirs()
    raw = pd.read_csv(DATA_RAW / "appointments_raw.csv")
    cleaned = clean(raw)
    out = DATA_PROCESSED / "appointments_clean.csv"
    cleaned.to_csv(out, index=False)
    print(f"Wrote {len(cleaned):,} rows -> {out}")
    print(f"No-show rate after cleaning: {cleaned['no_show_flag'].mean():.1%}")


if __name__ == "__main__":
    main()
