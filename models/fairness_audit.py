"""Subgroup fairness audit for the no-show risk model.

This is a **portfolio-level fairness audit on synthetic data**. Its purpose is
to *identify potential disparities*, not to certify the model as fair or
production-ready. Subgroup performance should be reviewed on real, target-
population data before any production use.

The audit evaluates the shipped model against the exact temporal test split
used in training (last 20% of appointments by date), then slices metrics by:

  - gender
  - age group (child / adolescent / young adult / adult / older adult / senior)
  - clinic
  - scholarship / social-program status
  - risk category (Low / Medium / High)

For each subgroup we report: group size, actual no-show rate, average predicted
risk, high-risk assignment rate, precision, recall, false-positive rate, and
false-negative rate. We also compare each subgroup against the overall test-set
value and flag notable gaps.

Because the intended intervention is **assistive** (an extra reminder or a
short call), we treat **equal opportunity (recall parity)** and **calibration
within subgroups (avg predicted vs. actual)** as the metrics that matter most.
Selection-rate differences that track true differences in outcome are not
themselves evidence of unfairness — mis-calibration and unequal recall are.

Run from the repository root:

    python models/fairness_audit.py

Outputs:
    data/processed/fairness_by_gender.csv
    data/processed/fairness_by_age_group.csv
    data/processed/fairness_by_clinic.csv
    data/processed/fairness_by_scholarship.csv
    data/processed/fairness_by_risk_category.csv
    data/processed/fairness_audit_summary.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "etl"))

from common import DATA_PROCESSED, MODELS_DIR  # noqa: E402
from score_appointments import categorize  # noqa: E402
from train_model import (  # noqa: E402
    BINARY_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET,
)

# Gap threshold used purely to flag rows for human review — not a
# certification threshold. Chosen for readability of the audit table.
GAP_FLAG = 0.05


def load_test_data() -> pd.DataFrame:
    """Reproduce the training temporal split and return only the test slice."""
    df = pd.read_csv(
        DATA_PROCESSED / "appointments_features.csv",
        parse_dates=["scheduled_datetime", "appointment_datetime"],
    ).sort_values("appointment_datetime").reset_index(drop=True)

    split = int(len(df) * 0.8)
    return df.iloc[split:].reset_index(drop=True)


def score(test: pd.DataFrame) -> pd.DataFrame:
    """Attach model probability and risk category to the test set."""
    model = joblib.load(MODELS_DIR / "no_show_model.pkl")
    thresholds = json.loads(
        (MODELS_DIR / "risk_thresholds.json").read_text(encoding="utf-8"))
    metrics = json.loads(
        (MODELS_DIR / "model_metrics.json").read_text(encoding="utf-8"))

    features = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES
    proba = model.predict_proba(test[features])[:, 1]

    out = test.copy()
    out["no_show_probability"] = proba
    out["risk_category"] = categorize(proba, thresholds)
    # Predict-positive uses the F1-optimal threshold from training, not the
    # risk-band cutoff, so precision/recall match the model card numbers.
    out["predicted_positive"] = proba >= float(metrics["decision_threshold"])
    return out


def age_group(age: int | float) -> str:
    a = int(age)
    if a <= 12: return "0-12 (child)"
    if a <= 17: return "13-17 (adolescent)"
    if a <= 30: return "18-30 (young adult)"
    if a <= 50: return "31-50 (adult)"
    if a <= 64: return "51-64 (older adult)"
    return "65+ (senior)"


def subgroup_metrics(df: pd.DataFrame, group_col: str,
                     base_no_show: float, base_recall: float,
                     base_precision: float) -> pd.DataFrame:
    """Compute per-subgroup performance for one grouping column."""
    rows = []
    for name, g in df.groupby(group_col, dropna=False):
        y = g[TARGET].astype(int).to_numpy()
        p = g["predicted_positive"].astype(int).to_numpy()
        proba = g["no_show_probability"].to_numpy()

        n = len(g)
        positives = int(y.sum())
        negatives = n - positives
        tp = int(((p == 1) & (y == 1)).sum())
        fp = int(((p == 1) & (y == 0)).sum())
        fn = int(((p == 0) & (y == 1)).sum())
        tn = int(((p == 0) & (y == 0)).sum())

        no_show_rate = positives / n if n else np.nan
        avg_pred = float(np.mean(proba)) if n else np.nan
        high_rate = float((g["risk_category"] == "High").mean()) if n else np.nan
        precision = tp / (tp + fp) if (tp + fp) else np.nan
        recall = tp / positives if positives else np.nan
        fpr = fp / negatives if negatives else np.nan
        fnr = fn / positives if positives else np.nan

        rows.append({
            "subgroup": name,
            "n": n,
            "actual_no_show_rate": round(no_show_rate, 4),
            "avg_predicted_risk": round(avg_pred, 4),
            "calibration_gap": round(avg_pred - no_show_rate, 4),
            "high_risk_assignment_rate": round(high_rate, 4),
            "precision": round(precision, 4) if precision == precision else np.nan,
            "recall": round(recall, 4) if recall == recall else np.nan,
            "false_positive_rate": round(fpr, 4) if fpr == fpr else np.nan,
            "false_negative_rate": round(fnr, 4) if fnr == fnr else np.nan,
            "recall_gap_vs_overall": round(recall - base_recall, 4)
                                     if recall == recall else np.nan,
            "precision_gap_vs_overall": round(precision - base_precision, 4)
                                        if precision == precision else np.nan,
            "flag_recall_gap": bool(recall == recall
                                    and abs(recall - base_recall) >= GAP_FLAG),
            "flag_calibration": bool(no_show_rate == no_show_rate
                                     and abs(avg_pred - no_show_rate) >= GAP_FLAG),
        })
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def overall_metrics(scored: pd.DataFrame) -> dict:
    y = scored[TARGET].astype(int).to_numpy()
    p = scored["predicted_positive"].astype(int).to_numpy()
    tp = int(((p == 1) & (y == 1)).sum())
    fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum())
    return {
        "n": len(scored),
        "no_show_rate": round(float(y.mean()), 4),
        "avg_predicted_risk": round(float(scored["no_show_probability"].mean()), 4),
        "precision": round(tp / (tp + fp), 4) if (tp + fp) else np.nan,
        "recall": round(tp / y.sum(), 4) if y.sum() else np.nan,
        "high_risk_assignment_rate": round(
            float((scored["risk_category"] == "High").mean()), 4),
    }


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n=== {title} ===")
    cols = ["subgroup", "n", "actual_no_show_rate", "avg_predicted_risk",
            "calibration_gap", "high_risk_assignment_rate", "precision",
            "recall", "false_positive_rate", "false_negative_rate",
            "flag_recall_gap", "flag_calibration"]
    with pd.option_context("display.width", 200, "display.max_columns", None,
                           "display.max_rows", None):
        print(df[cols].to_string(index=False))


def main() -> None:
    print("Portfolio fairness audit — synthetic data, not a production certification.\n")

    test = load_test_data()
    scored = score(test)

    overall = overall_metrics(scored)
    print("Overall test-set performance:")
    print(f"  n = {overall['n']:,}")
    print(f"  actual no-show rate:        {overall['no_show_rate']:.1%}")
    print(f"  avg predicted risk:         {overall['avg_predicted_risk']:.1%}")
    print(f"  precision:                  {overall['precision']:.3f}")
    print(f"  recall:                     {overall['recall']:.3f}")
    print(f"  high-risk assignment rate:  {overall['high_risk_assignment_rate']:.1%}")

    scored["age_group"] = scored["age"].apply(age_group)
    scored["scholarship_status"] = np.where(
        scored["scholarship_flag"].astype(bool),
        "Scholarship (social-program flag)", "No scholarship")

    slices = {
        "gender": ("Gender", "fairness_by_gender.csv"),
        "age_group": ("Age group", "fairness_by_age_group.csv"),
        "clinic_id": ("Clinic", "fairness_by_clinic.csv"),
        "scholarship_status": ("Scholarship / social-program status",
                               "fairness_by_scholarship.csv"),
        "risk_category": ("Risk category", "fairness_by_risk_category.csv"),
    }

    audit = {"overall": overall, "gap_flag_threshold": GAP_FLAG, "slices": {}}
    for col, (title, fname) in slices.items():
        table = subgroup_metrics(scored, col, overall["no_show_rate"],
                                 overall["recall"], overall["precision"])
        print_table(title, table)
        out_path = DATA_PROCESSED / fname
        table.to_csv(out_path, index=False)
        audit["slices"][col] = {
            "title": title,
            "output": str(out_path.relative_to(REPO_ROOT).as_posix()),
            "n_subgroups": int(len(table)),
            "n_flagged_recall_gap": int(table["flag_recall_gap"].sum()),
            "n_flagged_calibration": int(table["flag_calibration"].sum()),
        }

    summary_path = DATA_PROCESSED / "fairness_audit_summary.json"
    summary_path.write_text(json.dumps(audit, indent=2, default=str),
                            encoding="utf-8")
    print(f"\nAudit summary written to {summary_path.relative_to(REPO_ROOT).as_posix()}")
    print("\nInterpretation: this audit surfaces gaps for human review. It does NOT")
    print("certify the model as fair or production-ready. See docs/fairness_audit.md.")


if __name__ == "__main__":
    main()
