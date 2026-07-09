"""Load the raw appointment dataset.

Prefers the real Kaggle Medical Appointment No Shows file
(`data/raw/KaggleV2-May-2016.csv`). When it is not present, generates a
synthetic dataset with the exact same schema and realistic no-show behavior so
the full pipeline runs without external downloads.

Output: data/raw/appointments_raw.csv
"""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from common import DATA_RAW, NEIGHBOURHOODS, SEED, ensure_dirs

KAGGLE_FILE = DATA_RAW / "KaggleV2-May-2016.csv"
OUTPUT_FILE = DATA_RAW / "appointments_raw.csv"

N_PATIENTS = 6_500
N_APPOINTTMENTS = 32_000
HISTORY_DAYS = 300  # historical window ending yesterday
TARGET_NO_SHOW_RATE = 0.202  # matches the real Kaggle dataset


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_synthetic_raw() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    today = date.today()
    history_start = today - timedelta(days=HISTORY_DAYS)

    # --- Patient master with a latent no-show propensity (random effect) ---
    candidates = rng.integers(10_000_000_000, 99_999_999_999,
                              size=N_PATIENTS * 2, dtype=np.int64)
    patient_ids = np.unique(candidates)[:N_PATIENTS]
    rng.shuffle(patient_ids)
    genders = rng.choice(["F", "M"], size=N_PATIENTS, p=[0.65, 0.35])
    ages = np.clip(rng.gamma(shape=4.2, scale=10.5, size=N_PATIENTS).astype(int), 0, 98)
    hoods, hood_w = zip(*NEIGHBOURHOODS)
    hood_w = np.array(hood_w) / np.sum(hood_w)
    neighbourhoods = rng.choice(hoods, size=N_PATIENTS, p=hood_w)
    scholarship = (rng.random(N_PATIENTS) < 0.098).astype(int)
    hypertension = (rng.random(N_PATIENTS) < (0.05 + 0.004 * ages)).astype(int)
    diabetes = (rng.random(N_PATIENTS) < (0.02 + 0.0015 * ages)).astype(int)
    alcoholism = (rng.random(N_PATIENTS) < 0.03).astype(int)
    handicap = rng.choice([0, 1, 2, 3, 4], size=N_PATIENTS,
                          p=[0.972, 0.020, 0.005, 0.002, 0.001])
    # Latent propensity: most patients reliable, a tail of frequent no-showers.
    latent = rng.normal(0.0, 0.9, size=N_PATIENTS)

    # --- Appointments: patients weighted so some book repeatedly ---
    visit_weight = rng.gamma(shape=1.4, scale=1.0, size=N_PATIENTS)
    visit_weight /= visit_weight.sum()
    idx = rng.choice(N_PATIENTS, size=N_APPOINTTMENTS, p=visit_weight)

    # Appointment day: business days only, mild weekday seasonality.
    offsets = rng.integers(1, HISTORY_DAYS, size=N_APPOINTTMENTS)
    appt_days = np.array([history_start + timedelta(days=int(o)) for o in offsets])
    appt_days = np.array([
        d + timedelta(days=(7 - d.weekday())) if d.weekday() >= 5 else d
        for d in appt_days
    ])
    appt_days = np.array([d if d < today else d - timedelta(days=7) for d in appt_days])

    # Lead time: mixture of same-week bookings and long-lead bookings.
    lead = np.where(
        rng.random(N_APPOINTTMENTS) < 0.35,
        rng.integers(0, 4, size=N_APPOINTTMENTS),
        np.minimum(rng.gamma(2.0, 9.0, size=N_APPOINTTMENTS).astype(int), 120),
    )
    sched_days = np.array([d - timedelta(days=int(l)) for d, l in zip(appt_days, lead)])
    sched_hours = rng.integers(7, 18, size=N_APPOINTTMENTS)
    sched_minutes = rng.integers(0, 60, size=N_APPOINTTMENTS)
    sched_seconds = rng.integers(0, 60, size=N_APPOINTTMENTS)

    # SMS reminders are only sent for appointments booked >= 3 days ahead.
    sms = ((lead >= 3) & (rng.random(N_APPOINTTMENTS) < 0.62)).astype(int)

    # --- No-show probability: realistic drivers, calibrated to ~20% ---
    a = ages[idx]
    dow = np.array([d.weekday() for d in appt_days])
    z_raw = (
        0.045 * np.clip(lead, 0, 75)            # long lead time raises risk
        - 1.20 * (lead == 0)                    # same-day bookings rarely no-show
        - 0.028 * a                              # younger patients riskier
        + 0.50 * scholarship[idx]
        + 0.60 * alcoholism[idx]
        - 0.55 * sms                             # reminders reduce risk
        + 0.12 * (hypertension[idx])
        + 0.30 * (dow == 0) + 0.18 * (dow == 4)  # Monday/Friday effect
        + 1.00 * latent[idx]                     # per-patient behavior
        + rng.normal(0, 0.20, size=N_APPOINTTMENTS)
    )
    # Solve the intercept so the overall rate lands on the Kaggle benchmark.
    lo, hi = -6.0, 2.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if _sigmoid(z_raw + mid).mean() < TARGET_NO_SHOW_RATE:
            lo = mid
        else:
            hi = mid
    no_show = (rng.random(N_APPOINTTMENTS) < _sigmoid(z_raw + (lo + hi) / 2)).astype(int)

    df = pd.DataFrame({
        "PatientId": patient_ids[idx].astype(float),
        "AppointmentID": np.arange(5_600_000, 5_600_000 + N_APPOINTTMENTS),
        "Gender": genders[idx],
        "ScheduledDay": [
            datetime(d.year, d.month, d.day, h, m, s).strftime("%Y-%m-%dT%H:%M:%SZ")
            for d, h, m, s in zip(sched_days, sched_hours, sched_minutes, sched_seconds)
        ],
        "AppointmentDay": [
            datetime(d.year, d.month, d.day).strftime("%Y-%m-%dT%H:%M:%SZ")
            for d in appt_days
        ],
        "Age": a,
        "Neighbourhood": neighbourhoods[idx],
        "Scholarship": scholarship[idx],
        "Hipertension": hypertension[idx],
        "Diabetes": diabetes[idx],
        "Alcoholism": alcoholism[idx],
        "Handcap": handicap[idx],
        "SMS_received": sms,
        "No-show": np.where(no_show == 1, "Yes", "No"),
    })
    return df.sort_values("AppointmentDay").reset_index(drop=True)


def main() -> None:
    ensure_dirs()
    if KAGGLE_FILE.exists():
        print(f"Found Kaggle dataset at {KAGGLE_FILE.name}; using real data.")
        df = pd.read_csv(KAGGLE_FILE)
    else:
        print("Kaggle file not found; generating synthetic raw dataset "
              "(same schema, realistic no-show patterns).")
        df = generate_synthetic_raw()

    df.to_csv(OUTPUT_FILE, index=False)
    rate = (df["No-show"].astype(str).str.strip().str.lower() == "yes").mean()
    print(f"Wrote {len(df):,} rows -> {OUTPUT_FILE}")
    print(f"Overall no-show rate: {rate:.1%}")


if __name__ == "__main__":
    main()
