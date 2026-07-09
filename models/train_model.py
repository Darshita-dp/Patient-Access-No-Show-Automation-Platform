"""Train the appointment no-show prediction model.

Compares Logistic Regression, Random Forest, and Gradient Boosting on a
TEMPORAL split (train on the first 80% of appointments by date, test on the
most recent 20%) so evaluation mirrors production: score future visits using
only past behavior. All patient/clinic/provider history features are built
from prior appointments only (see etl/feature_engineering.py), so there is no
target leakage.

Outputs:
    models/no_show_model.pkl      final fitted sklearn Pipeline
    models/risk_thresholds.json   probability cutoffs for Low/Medium/High
    models/model_metrics.json     comparison table + final model metrics
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "etl"))
from common import DATA_PROCESSED, MODELS_DIR, SEED  # noqa: E402

MODEL_VERSION = "v1.0"

NUMERIC_FEATURES = [
    "age", "lead_time_days", "handicap_flag",
    "patient_previous_appointments", "patient_previous_no_shows",
    "patient_no_show_rate", "clinic_no_show_rate", "provider_no_show_rate",
    "appointment_hour", "reminder_count",
]
BINARY_FEATURES = [
    "sms_received", "scholarship_flag", "hypertension_flag",
    "diabetes_flag", "alcoholism_flag", "is_weekend",
]
CATEGORICAL_FEATURES = [
    "gender", "appointment_day_of_week", "scheduled_day_of_week",
    "appointment_type", "clinic_id", "provider_id", "appointment_month",
]
TARGET = "no_show_flag"


def build_candidates() -> dict[str, Pipeline]:
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("bin", "passthrough", BINARY_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    return {
        "LogisticRegression": Pipeline([
            ("prep", preprocess),
            # No class_weight rebalancing: keeps predicted probabilities
            # calibrated to the true ~20% base rate so the UI shows honest
            # numbers. Imbalance is handled by the F1-optimal threshold.
            ("clf", LogisticRegression(max_iter=2000, random_state=SEED)),
        ]),
        "RandomForestClassifier": Pipeline([
            ("prep", preprocess),
            ("clf", RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_leaf=20,
                n_jobs=-1, random_state=SEED)),
        ]),
        "GradientBoostingClassifier": Pipeline([
            ("prep", preprocess),
            ("clf", GradientBoostingClassifier(
                n_estimators=250, learning_rate=0.08, max_depth=3,
                subsample=0.9, random_state=SEED)),
        ]),
    }


def f1_optimal_threshold(pipe: Pipeline, X_train, y_train) -> float:
    """Pick the decision threshold that maximizes F1 on the training data.

    A fixed 0.5 cutoff is meaningless on an imbalanced target; choosing the
    operating point on train keeps the test evaluation honest.
    """
    proba = pipe.predict_proba(X_train)[:, 1]
    best_t, best_f1 = 0.5, -1.0
    for t in np.arange(0.05, 0.95, 0.01):
        f1 = f1_score(y_train, proba >= t)
        if f1 > best_f1:
            best_t, best_f1 = float(t), f1
    return round(best_t, 2)


def evaluate(name: str, pipe: Pipeline, X_test, y_test, threshold: float) -> dict:
    proba = pipe.predict_proba(X_test)[:, 1]
    pred = (proba >= threshold).astype(int)
    cm = confusion_matrix(y_test, pred)
    return {
        "model_name": name,
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred), 4),
        "recall": round(recall_score(y_test, pred), 4),
        "f1_score": round(f1_score(y_test, pred), 4),
        "decision_threshold": threshold,
        "confusion_matrix": {
            "true_negative": int(cm[0, 0]), "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]), "true_positive": int(cm[1, 1]),
        },
    }


def top_feature_importances(pipe: Pipeline, n: int = 15) -> list[dict]:
    clf = pipe.named_steps["clf"]
    names = pipe.named_steps["prep"].get_feature_names_out()
    if hasattr(clf, "feature_importances_"):
        imp = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        imp = np.abs(clf.coef_[0])  # standardized inputs, so |coef| ranks drivers
    else:
        return []
    # Aggregate one-hot dummies back to their source feature so the ranking
    # reads as business drivers, not individual provider/clinic codes.
    base_features = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES
    grouped: dict[str, list[float]] = {}
    for raw_name, value in zip(names, imp):
        short = str(raw_name).split("__", 1)[-1]
        base = next((b for b in sorted(base_features, key=len, reverse=True)
                     if short == b or short.startswith(b + "_")), short)
        grouped.setdefault(base, []).append(float(value))
    scores = {b: float(np.mean(v)) for b, v in grouped.items()}
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [{"feature": f, "importance": round(s, 4)} for f, s in top]


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "appointments_features.csv",
                     parse_dates=["appointment_datetime"])
    df = df.sort_values("appointment_datetime").reset_index(drop=True)

    features = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES
    X, y = df[features], df[TARGET].astype(int)

    split = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    print(f"Temporal split: {len(X_train):,} train / {len(X_test):,} test "
          f"(test period starts {df['appointment_datetime'].iloc[split].date()})")
    print(f"Base no-show rate — train {y_train.mean():.1%}, test {y_test.mean():.1%}\n")

    results = []
    fitted = {}
    for name, pipe in build_candidates().items():
        pipe.fit(X_train, y_train)
        threshold = f1_optimal_threshold(pipe, X_train, y_train)
        metrics = evaluate(name, pipe, X_test, y_test, threshold)
        results.append(metrics)
        fitted[name] = pipe
        print(f"{name:<28} AUC={metrics['roc_auc']:.3f}  "
              f"recall={metrics['recall']:.3f}  precision={metrics['precision']:.3f}  "
              f"F1={metrics['f1_score']:.3f}")

    # Select on ROC-AUC; recall matters operationally but the risk categories
    # (percentile-based) drive outreach volume, not the 0.5 threshold.
    best = max(results, key=lambda r: r["roc_auc"])
    best_name = best["model_name"]
    best_pipe = fitted[best_name]
    print(f"\nSelected model: {best_name} (ROC-AUC {best['roc_auc']:.3f})")

    # Risk thresholds from the TRAINING probability distribution:
    # Low = bottom 50%, Medium = 50th-80th percentile, High = top 20%.
    train_proba = best_pipe.predict_proba(X_train)[:, 1]
    thresholds = {
        "model_version": MODEL_VERSION,
        "medium_threshold": round(float(np.percentile(train_proba, 50)), 4),
        "high_threshold": round(float(np.percentile(train_proba, 80)), 4),
        "logic": "Low < p50 of train probabilities; Medium = p50-p80; High >= p80",
    }
    print(f"Risk thresholds: Medium >= {thresholds['medium_threshold']}, "
          f"High >= {thresholds['high_threshold']}")

    # Recall of actual no-shows captured by the High-risk band (the number
    # the operations team actually cares about).
    test_proba = best_pipe.predict_proba(X_test)[:, 1]
    high_mask = test_proba >= thresholds["high_threshold"]
    high_recall = float(y_test[high_mask].sum() / y_test.sum())
    high_precision = float(y_test[high_mask].mean()) if high_mask.any() else 0.0
    print(f"High-risk band captures {high_recall:.1%} of test-period no-shows; "
          f"{high_precision:.1%} of flagged appointments were true no-shows.")

    final = {
        **{k: best[k] for k in ("model_name", "roc_auc", "accuracy", "precision",
                                "recall", "f1_score", "decision_threshold",
                                "confusion_matrix")},
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "split_strategy": "temporal 80/20 (train on earlier appointments)",
        "high_risk_band": {
            "share_of_appointments": 0.20,
            "no_show_recall": round(high_recall, 4),
            "no_show_precision": round(high_precision, 4),
        },
        "model_comparison": results,
        "top_features": top_feature_importances(best_pipe),
    }

    joblib.dump(best_pipe, MODELS_DIR / "no_show_model.pkl")
    (MODELS_DIR / "risk_thresholds.json").write_text(json.dumps(thresholds, indent=2))
    (MODELS_DIR / "model_metrics.json").write_text(json.dumps(final, indent=2))
    print(f"\nSaved no_show_model.pkl, risk_thresholds.json, model_metrics.json "
          f"-> {MODELS_DIR}")


if __name__ == "__main__":
    main()
