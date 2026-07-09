# Model Card — Appointment No-Show Prediction

## Model details

| | |
|---|---|
| **Model** | Logistic Regression (scikit-learn `Pipeline`: StandardScaler + OneHotEncoder + LogisticRegression) |
| **Version** | v1.0 |
| **Task** | Binary classification — will a scheduled appointment end in a no-show? |
| **Output** | Calibrated no-show probability (0–1), banded into Low / Medium / High risk |
| **Owner** | Patient access analytics (portfolio project) |
| **Artifacts** | `models/no_show_model.pkl`, `models/risk_thresholds.json`, `models/model_metrics.json` |

Logistic regression was selected over Random Forest (AUC 0.717) and Gradient
Boosting (AUC 0.709) because it scored best (AUC 0.720), and — equally
important in a healthcare operations setting — its coefficients are directly
explainable to scheduling staff and compliance reviewers. No class-weight
rebalancing is applied, so predicted probabilities stay calibrated to the true
~20% base rate; class imbalance is handled at the decision layer (percentile
risk bands and an F1-optimal threshold), not by distorting probabilities.

## Intended use

- **Primary:** rank upcoming appointments so patient access teams focus
  limited outreach capacity (calls, targeted reminders) on the top-20% risk
  band.
- **Users:** scheduling staff, patient access coordinators/managers, clinic
  operations leaders.
- **Out of scope:** clinical decision-making, patient eligibility, coverage
  decisions, or any punitive action against patients (e.g., denying
  bookings). The model prioritizes *help*, not exclusion.

## Training data

- Base schema: Kaggle **Medical Appointment No Shows** (Vitória, Brazil,
  2016). In this repository a **synthetic dataset with the same schema and
  realistic behavioral patterns** is generated when the Kaggle file is absent
  (`etl/load_raw_data.py`), so all reported metrics are on synthetic data.
- 32,000 historical appointments, ~5,700 patients, 6 clinics, 36 providers,
  19.9% no-show rate.
- Split: **temporal 80/20** — trained on the first 80% of appointments by
  date (25,600), evaluated on the most recent 20% (6,400). This mirrors
  production scoring and prevents look-ahead bias.

## Features (18)

Timing (`lead_time_days`, day-of-week, month, hour, weekend), patient
demographics and condition flags, reminder signals (`sms_received`,
`reminder_count`), leakage-safe history (`patient_previous_appointments`,
`patient_previous_no_shows`, `patient_no_show_rate`, smoothed
`clinic_no_show_rate` / `provider_no_show_rate`), and visit context
(appointment type, clinic, provider). Every history feature is computed from
appointments strictly before the one being scored.

## Performance (held-out, most recent 20% of appointments)

| Metric | Value |
|---|---|
| ROC-AUC | **0.720** |
| Recall (no-show class, F1-optimal threshold 0.21) | 0.614 |
| Precision (no-show class) | 0.332 |
| F1-score | 0.431 |
| Accuracy | 0.685 |

Confusion matrix at threshold 0.21: TP 762 · FN 480 · FP 1,536 · TN 3,622.

**Operational metric that matters most:** the High-risk band (top 20% of
probabilities) captures **45% of all actual no-shows**, and **40% of flagged
appointments truly no-show** — about 2× the 19.9% base rate. Staff calling
only the High band find a real no-show risk in 2 of every 5 calls.

Top risk drivers: lead time, patient's prior no-show history, age,
social-program flag, reminder status, and provider/clinic no-show rates.

## Why recall is weighted over precision

A missed no-show costs an unused provider slot (~$150–$200) and delays care
for another patient. A false positive costs a short reminder call. Given that
asymmetry, the operating point favors catching more true no-shows and accepts
extra outreach volume — sized by the top-20% band to match real staff
capacity.

## Risk thresholds

From the training probability distribution: Low < p50 (0.164) ≤ Medium <
p80 (0.286) ≤ High. Percentile bands keep the daily outreach list a
predictable size regardless of probability drift.

## Limitations & ethical considerations

- **Synthetic data:** metrics reflect a simulated population; real-world
  performance requires retraining and re-validation on the target health
  system's data.
- **Fairness:** features include age, gender, and a social-program proxy
  (scholarship). Before production use, subgroup performance (age bands,
  gender, neighborhood deprivation) must be audited; the intended
  intervention (extra reminders/support) is assistive, which lowers — but
  does not remove — fairness risk.
- **Feedback loops:** successful outreach changes outcomes, which changes
  future training labels. Retraining should exclude outcome periods where
  the intervention was active or model the intervention explicitly.
- **Drift:** lead-time mix, reminder channels, and scheduling policies shift;
  monitor AUC and band no-show rates monthly, retrain quarterly.
