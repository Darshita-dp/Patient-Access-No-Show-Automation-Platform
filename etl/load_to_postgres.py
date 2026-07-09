"""Load the processed and synthetic tables into PostgreSQL.

Connection comes from the DATABASE_URL environment variable, e.g.:

    postgresql+psycopg2://access_admin:access_admin@localhost:5432/patient_access

If no database is reachable the script exits gracefully — the platform runs in
CSV mode by default (the FastAPI backend reads the same CSVs directly), so
PostgreSQL is an optional deployment target, not a requirement.

Run sql/01_schema.sql against the database first to create the tables.
"""

import os
import sys

import pandas as pd

from common import DATA_PROCESSED, DATA_SYNTHETIC, REPO_ROOT

DEFAULT_URL = "postgresql+psycopg2://access_admin:access_admin@localhost:5432/patient_access"

# table name -> (source file, subset of columns to load or None for all)
LOAD_PLAN = {
    "clinics": (DATA_SYNTHETIC / "clinics.csv", None),
    "providers": (DATA_SYNTHETIC / "providers.csv", None),
    "patients": (DATA_SYNTHETIC / "patients.csv", None),
    "staff_users": (DATA_SYNTHETIC / "staff_users.csv", None),
    "date_dim": (DATA_SYNTHETIC / "date_dim.csv", None),
    "appointments": (DATA_SYNTHETIC / "appointments_full.csv", [
        "appointment_id", "patient_id", "provider_id", "clinic_id",
        "scheduled_datetime", "appointment_datetime", "appointment_status",
        "no_show_flag", "sms_received", "lead_time_days", "appointment_type",
        "specialty", "appointment_hour",
    ]),
    "open_slots": (DATA_SYNTHETIC / "open_slots.csv", None),
    "waitlist_requests": (DATA_SYNTHETIC / "waitlist_requests.csv", [
        "waitlist_id", "patient_id", "requested_specialty", "preferred_clinic_id",
        "preferred_provider_id", "requested_date", "urgency_level",
        "availability_window", "waitlist_status",
    ]),
    "reminder_events": (DATA_SYNTHETIC / "reminder_events.csv", None),
    "risk_scores": (DATA_PROCESSED / "risk_scores.csv", None),
    "recommended_actions": (DATA_PROCESSED / "recommended_actions.csv", None),
    "access_tasks": (DATA_PROCESSED / "access_tasks.csv", None),
    "waitlist_match_results": (DATA_PROCESSED / "waitlist_match_results.csv", None),
}


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure means CSV mode
        print("PostgreSQL not reachable — staying in CSV mode (this is fine).")
        print(f"  Reason: {type(exc).__name__}: {exc}")
        print("  To load Postgres later: set DATABASE_URL, run sql/01_schema.sql, "
              "then re-run this script.")
        sys.exit(0)

    print(f"Connected to {url.split('@')[-1]}")
    loaded, skipped = 0, []
    for table, (path, cols) in LOAD_PLAN.items():
        if not path.exists():
            skipped.append(table)
            continue
        df = pd.read_csv(path)
        if cols:
            df = df[[c for c in cols if c in df.columns]]
        if table == "appointments" and "no_show_flag" in df.columns:
            df["no_show_flag"] = (
                df["no_show_flag"].astype(str).str.lower().map(
                    {"true": True, "false": False}).astype("boolean")
            )
        df.to_sql(table, engine, if_exists="append", index=False, method="multi",
                  chunksize=2_000)
        print(f"  {table:<24} {len(df):>8,} rows")
        loaded += 1

    if skipped:
        print(f"Skipped (source file not generated yet): {', '.join(skipped)}")
        print("Run models/train_model.py and models/score_appointments.py, "
              "then re-run this loader for the scoring tables.")
    print(f"Done. {loaded} tables loaded from {REPO_ROOT}.")


if __name__ == "__main__":
    main()
