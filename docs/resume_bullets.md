# Resume Bullets

**Patient Access & Appointment No-Show Automation Platform**

- Built an end-to-end patient access automation platform using Python,
  PostgreSQL, FastAPI, React, and Power BI to predict appointment no-show
  risk and improve scheduling visibility

- Developed a no-show prediction model using appointment, patient, reminder,
  and scheduling features, converting model probabilities into low, medium,
  and high operational risk categories

- Designed SQL data model for patient access operations, including
  appointments, providers, clinics, waitlists, reminders, risk scores, and
  staff action tracking

- Created recommended-action and waitlist-matching logic to help scheduling
  teams prioritize outreach, fill open slots, and reduce manual scheduling
  follow-up

- Built Power BI executive dashboard tracking no-show rate, clinic
  utilization, provider schedule gaps, high-risk appointments, waitlist
  demand, and staff action completion

## Variants with quantified detail

- Trained and compared Logistic Regression, Random Forest, and Gradient
  Boosting classifiers on 32,000 appointments with a temporal train/test
  split and leakage-safe history features, reaching 0.72 ROC-AUC with a
  top-20% risk band that captures 45% of all no-shows at 2× base-rate
  precision

- Engineered a waitlist priority score (urgency 35%, wait time 25%,
  availability fit 20%, attendance likelihood 15%, provider preference 5%)
  that ranks replacement candidates for every released appointment slot with
  a plain-language match reason

- Delivered an 8-view React operations app (command center, work queue,
  search, appointment detail with risk explanation, waitlist manager,
  provider schedules, clinic utilization, action tracker) backed by a
  13-endpoint FastAPI service
