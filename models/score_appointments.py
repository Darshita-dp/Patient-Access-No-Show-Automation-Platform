"""Score upcoming appointments and generate the operational work products.

Pipeline (run after etl/ and models/train_model.py):
    1. Score every scheduled appointment with the trained model
    2. Convert probabilities to Low/Medium/High risk categories
    3. Run the recommended-action engine  -> recommended_actions.csv
    4. Create staff tasks                 -> access_tasks.csv
    5. Match open slots to the waitlist   -> waitlist_match_results.csv

Outputs land in data/processed/ and are served by the FastAPI backend
(and loadable into PostgreSQL via etl/load_to_postgres.py).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "etl"))

from common import DATA_PROCESSED, DATA_SYNTHETIC, MODELS_DIR, SEED  # noqa: E402
from api.services.action_engine import (  # noqa: E402
    build_access_tasks, build_manager_tasks, build_recommended_actions,
)
from api.services.waitlist_matching import build_match_results  # noqa: E402

from train_model import BINARY_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES  # noqa: E402

MODEL_VERSION = "v1.0"


def categorize(proba: np.ndarray, thresholds: dict) -> np.ndarray:
    cats = np.full(len(proba), "Low", dtype=object)
    cats[proba >= thresholds["medium_threshold"]] = "Medium"
    cats[proba >= thresholds["high_threshold"]] = "High"
    return cats


def provider_utilization(appts: pd.DataFrame, providers: pd.DataFrame) -> pd.DataFrame:
    upcoming = appts[appts["appointment_status"] == "Scheduled"]
    booked = upcoming.groupby("provider_id").size().rename("booked")
    util = providers.set_index("provider_id").join(booked).fillna({"booked": 0})
    util["capacity_two_weeks"] = util["daily_capacity"] * 10  # 10 weekdays
    util["utilization_rate"] = (util["booked"] / util["capacity_two_weeks"]).round(4)
    return util.reset_index()


def clinic_no_show_stats(appts: pd.DataFrame, clinics: pd.DataFrame) -> pd.DataFrame:
    hist = appts[appts["appointment_status"].isin(["Completed", "No-Show"])].copy()
    hist["no_show"] = hist["no_show_flag"].astype(str).str.lower().eq("true")
    stats = hist.groupby("clinic_id")["no_show"].mean().rename("no_show_rate")
    return clinics.merge(stats, on="clinic_id")


def main() -> None:
    now = datetime.now()
    rng = np.random.default_rng(SEED)

    model = joblib.load(MODELS_DIR / "no_show_model.pkl")
    thresholds = json.loads((MODELS_DIR / "risk_thresholds.json").read_text())

    upcoming = pd.read_csv(DATA_PROCESSED / "upcoming_features.csv",
                           parse_dates=["appointment_datetime", "scheduled_datetime"])
    scheduled = upcoming[upcoming["appointment_status"] == "Scheduled"].copy()

    features = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES
    proba = model.predict_proba(scheduled[features])[:, 1]
    scheduled["no_show_probability"] = np.round(proba, 4)
    scheduled["risk_category"] = categorize(proba, thresholds)

    risk_scores = scheduled[["appointment_id", "no_show_probability", "risk_category"]].copy()
    risk_scores.insert(0, "risk_score_id", range(1, len(risk_scores) + 1))
    risk_scores.insert(2, "model_version", MODEL_VERSION)
    risk_scores["scored_at"] = now.isoformat(timespec="seconds")
    risk_scores.to_csv(DATA_PROCESSED / "risk_scores.csv", index=False)
    mix = scheduled["risk_category"].value_counts()
    print(f"Scored {len(scheduled):,} scheduled appointments "
          f"(High {mix.get('High', 0):,} / Medium {mix.get('Medium', 0):,} / "
          f"Low {mix.get('Low', 0):,})")

    actions = build_recommended_actions(scheduled, now)
    actions.to_csv(DATA_PROCESSED / "recommended_actions.csv", index=False)
    print(f"Recommended actions: {len(actions):,}")

    tasks = build_access_tasks(scheduled, actions, now, rng)

    appts_full = pd.read_csv(DATA_SYNTHETIC / "appointments_full.csv",
                             dtype={"no_show_flag": str})
    providers = pd.read_csv(DATA_SYNTHETIC / "providers.csv")
    clinics = pd.read_csv(DATA_SYNTHETIC / "clinics.csv")
    util = provider_utilization(appts_full, providers)
    clinic_stats = clinic_no_show_stats(appts_full, clinics)
    mgr_tasks = build_manager_tasks(util, clinic_stats, now,
                                    start_task_id=len(tasks) + 1)
    all_tasks = pd.concat([tasks.assign(context=""), mgr_tasks], ignore_index=True)
    all_tasks.to_csv(DATA_PROCESSED / "access_tasks.csv", index=False)
    print(f"Staff tasks: {len(tasks):,} outreach + {len(mgr_tasks):,} manager reviews")

    open_slots = pd.read_csv(DATA_SYNTHETIC / "open_slots.csv")
    waitlist = pd.read_csv(DATA_SYNTHETIC / "waitlist_requests.csv")
    hist = appts_full[appts_full["appointment_status"].isin(["Completed", "No-Show"])].copy()
    hist["no_show"] = hist["no_show_flag"].str.lower().eq("true")
    patient_risk = hist.groupby("patient_id")["no_show"].mean().to_dict()

    matches = build_match_results(open_slots, waitlist, patient_risk, now)
    matches.to_csv(DATA_PROCESSED / "waitlist_match_results.csv", index=False)
    slots_with_matches = matches["slot_id"].nunique() if not matches.empty else 0
    print(f"Waitlist matches: {len(matches):,} candidate offers across "
          f"{slots_with_matches:,} open slots")


if __name__ == "__main__":
    main()
