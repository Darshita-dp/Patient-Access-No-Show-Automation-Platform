"""Data access layer for the Patient Access API.

Default mode is CSV: the generated data products (synthetic operational
tables + model scoring outputs) are loaded into in-memory DataFrames at
startup and joined into the same shapes the SQL views produce. Setting
DATABASE_URL and loading PostgreSQL via etl/load_to_postgres.py serves the
identical schema for BI tools; the API itself stays on the CSV store so the
demo runs with zero infrastructure.

Write operations (send reminder, complete task, waitlist offers) mutate the
in-memory store — a deliberate simulation boundary for this case study.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_SYNTHETIC = REPO_ROOT / "data" / "synthetic"


class DataStore:
    """Loads, joins, and serves every table the platform needs."""

    def __init__(self) -> None:
        self.loaded_at = datetime.now()
        self.clinics = pd.read_csv(DATA_SYNTHETIC / "clinics.csv")
        self.providers = pd.read_csv(DATA_SYNTHETIC / "providers.csv")
        self.patients = pd.read_csv(DATA_SYNTHETIC / "patients.csv")
        self.staff = pd.read_csv(DATA_SYNTHETIC / "staff_users.csv")
        self.open_slots = pd.read_csv(DATA_SYNTHETIC / "open_slots.csv",
                                      parse_dates=["slot_datetime"])
        self.waitlist = pd.read_csv(DATA_SYNTHETIC / "waitlist_requests.csv")
        self.reminders = pd.read_csv(DATA_SYNTHETIC / "reminder_events.csv",
                                     parse_dates=["sent_datetime"])
        self.appointments = pd.read_csv(
            DATA_SYNTHETIC / "appointments_full.csv",
            parse_dates=["scheduled_datetime", "appointment_datetime"],
            dtype={"no_show_flag": str},
        )
        self.risk_scores = pd.read_csv(DATA_PROCESSED / "risk_scores.csv")
        self.actions = pd.read_csv(DATA_PROCESSED / "recommended_actions.csv")
        self.tasks = pd.read_csv(DATA_PROCESSED / "access_tasks.csv",
                                 dtype={"appointment_id": str, "context": str,
                                        "completed_date": str})
        self.matches = pd.read_csv(DATA_PROCESSED / "waitlist_match_results.csv")
        self.upcoming_features = pd.read_csv(
            DATA_PROCESSED / "upcoming_features.csv",
            parse_dates=["appointment_datetime", "scheduled_datetime"])

        self._normalize()
        self.worklist = self._build_worklist()
        self.patient_risk = self._build_patient_risk()

    # ------------------------------------------------------------------ setup

    def _normalize(self) -> None:
        self.appointments["is_historical"] = self.appointments[
            "appointment_status"].isin(["Completed", "No-Show"])
        self.appointments["no_show_bool"] = (
            self.appointments["no_show_flag"].astype(str).str.lower().eq("true"))
        self.tasks["appointment_id"] = pd.to_numeric(
            self.tasks["appointment_id"], errors="coerce").astype("Int64")
        self.waitlist["preferred_provider_id"] = pd.to_numeric(
            self.waitlist["preferred_provider_id"], errors="coerce").astype("Int64")
        self.waitlist["preferred_clinic_id"] = pd.to_numeric(
            self.waitlist["preferred_clinic_id"], errors="coerce").astype("Int64")

    def _build_worklist(self) -> pd.DataFrame:
        """The operational appointment view: scheduled visits + risk + action
        + task + reminder status, one row per upcoming appointment."""
        appts = self.appointments[
            self.appointments["appointment_status"].isin(["Scheduled", "Cancelled"])
        ].copy()
        appts = appts.merge(
            self.patients[["patient_id", "patient_name"]], on="patient_id", how="left")
        appts = appts.merge(
            self.providers[["provider_id", "provider_name"]], on="provider_id", how="left")
        appts = appts.merge(
            self.clinics[["clinic_id", "clinic_name"]], on="clinic_id", how="left")
        appts = appts.merge(
            self.risk_scores[["appointment_id", "no_show_probability", "risk_category"]],
            on="appointment_id", how="left")
        appts = appts.merge(
            self.actions[["appointment_id", "recommended_action", "action_reason",
                          "priority"]],
            on="appointment_id", how="left")

        appt_tasks = (self.tasks.dropna(subset=["appointment_id"])
                      .sort_values("task_id")
                      .groupby("appointment_id").last().reset_index())
        appts = appts.merge(
            appt_tasks[["appointment_id", "task_id", "task_status", "assigned_to",
                        "due_date"]],
            on="appointment_id", how="left")

        latest_reminder = (self.reminders.sort_values("sent_datetime")
                           .groupby("appointment_id").last().reset_index())
        appts = appts.merge(
            latest_reminder[["appointment_id", "delivery_status", "patient_response",
                             "sent_datetime"]].rename(columns={
                                 "sent_datetime": "last_reminder_at"}),
            on="appointment_id", how="left")

        appts["reminder_status"] = np.select(
            [
                appts["patient_response"].eq("Confirmed"),
                appts["patient_response"].eq("Reschedule Requested"),
                appts["patient_response"].eq("Declined"),
                appts["delivery_status"].eq("Failed"),
                appts["delivery_status"].notna(),
            ],
            ["Confirmed", "Reschedule Requested", "Declined", "Delivery Failed",
             "Sent — No Response"],
            default="Not Sent",
        )
        return appts

    def _build_patient_risk(self) -> dict[int, float]:
        hist = self.appointments[self.appointments["is_historical"]]
        return hist.groupby("patient_id")["no_show_bool"].mean().to_dict()

    # ---------------------------------------------------------------- helpers

    def patient_history(self, patient_id: int) -> pd.DataFrame:
        hist = self.appointments[
            (self.appointments["patient_id"] == patient_id)
            & self.appointments["is_historical"]
        ].sort_values("appointment_datetime", ascending=False)
        hist = hist.merge(
            self.providers[["provider_id", "provider_name"]], on="provider_id", how="left")
        hist = hist.merge(
            self.clinics[["clinic_id", "clinic_name"]], on="clinic_id", how="left")
        return hist

    def next_task_id(self) -> int:
        return int(self.tasks["task_id"].max()) + 1 if len(self.tasks) else 1

    def next_reminder_id(self) -> int:
        return int(self.reminders["reminder_id"].max()) + 1 if len(self.reminders) else 1


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store


# ------------------------------------------------------------- serialization

def df_records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe records: NaN/NaT -> None, timestamps -> ISO strings."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
    out = out.replace({np.nan: None, pd.NaT: None})
    return out.to_dict(orient="records")
