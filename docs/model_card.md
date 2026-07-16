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

> **Status:** This model is built for **portfolio and synthetic-data
> demonstration only.** It is trained on a synthetic population, has **not**
> undergone a subgroup fairness audit, and is **not production-safe for
> healthcare deployment**. See [Limitations](#limitations--ethical-considerations)
> and [Future fairness audit](#future-fairness-audit).

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
- **Fairness (portfolio-level audit performed on synthetic data; not a
  production certification):** features include age, gender, and a
  social-program proxy (scholarship). A subgroup audit across gender, age
  group, clinic, scholarship status, and risk category is implemented in
  `models/fairness_audit.py` and interpreted in
  [docs/fairness_audit.md](fairness_audit.md). On the synthetic test set it
  surfaces a **material age disparity** (recall of 22% for the 65+ group vs.
  61% overall), **clinic-level recall gaps**, and a **~5 pp over-prediction
  of risk for the scholarship subgroup**. No bias-mitigation technique has
  been applied — the audit identifies disparities, it does not fix them. The
  intended intervention (extra reminders/support) is assistive, which lowers
  — but does not remove — fairness risk. Before any production use, this
  audit must be repeated on real target-population data with the additions
  listed under [Future fairness audit](#future-fairness-audit).
- **Feedback loops:** successful outreach changes outcomes, which changes
  future training labels. Retraining should exclude outcome periods where
  the intervention was active or model the intervention explicitly.
- **Drift:** lead-time mix, reminder channels, and scheduling policies shift;
  monitor AUC and band no-show rates monthly, retrain quarterly.

## Future fairness audit

A **portfolio-level audit on synthetic data** is now included — see
`models/fairness_audit.py` and [docs/fairness_audit.md](fairness_audit.md). It
covers gender, age group, clinic, scholarship status, and risk category, and
already surfaces material age and clinic disparities. A **full pre-deployment
audit on real, representative data** is still a future enhancement. Before any
production use, subgroup performance should be evaluated across **age bands,
gender, socioeconomic proxy variables (e.g. the scholarship flag and
neighborhood deprivation), and clinic/provider segments**, at minimum
measuring:

- **Selection rate** — what share of each subgroup lands in the High-risk band,
  compared to that subgroup's actual no-show rate (is any group over-flagged
  relative to its true rate?).
- **Equal opportunity** — recall/true-positive rate parity across subgroups, so
  outreach reaches genuinely at-risk patients in every group.
- **Calibration within subgroups** — does a predicted 0.40 mean 40% for each
  group, or is the score systematically off for some?
- **Precision parity** — whether some groups absorb disproportionately more
  false positives (i.e. unnecessary contact).

Because the intervention is assistive rather than punitive, **equal opportunity
and calibration matter more than selection-rate parity here** — the operational
harm of a false positive is a short reminder call, while a false negative is a
missed appointment and a lost slot. Any audit should also confirm that
scholarship and neighborhood features are not acting purely as proxies for
protected characteristics; if they are, the model should be re-fit without them
and the performance cost measured explicitly.
