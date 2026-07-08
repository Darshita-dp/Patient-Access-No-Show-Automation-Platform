# Raw Data

This project uses the **Kaggle Medical Appointment No Shows** dataset as its base appointment dataset.

- Dataset: https://www.kaggle.com/datasets/joniarroba/noshowappointments
- Expected file: `KaggleV2-May-2016.csv` placed in this folder

## If you do not have Kaggle access

No problem — the pipeline ships with a synthetic fallback. Running:

```bash
python etl/load_raw_data.py
```

will detect that `KaggleV2-May-2016.csv` is missing and generate `appointments_raw.csv` in this folder with the **same columns and realistic statistical patterns** (age/gender mix, lead-time effects, SMS reminder effects, neighbourhood distribution, ~20% no-show rate) so every downstream step — cleaning, feature engineering, model training, API, and frontend — runs end to end.

Raw columns (matching the Kaggle schema):

`PatientId, AppointmentID, Gender, ScheduledDay, AppointmentDay, Age, Neighbourhood, Scholarship, Hipertension, Diabetes, Alcoholism, Handcap, SMS_received, No-show`
