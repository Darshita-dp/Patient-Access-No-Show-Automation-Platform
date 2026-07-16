"""ETL cleaning and feature-engineering behavior.

Exercises the real `clean()` from etl/clean_appointments.py against small,
hand-built frames in the raw Kaggle column format, so the rules that protect
the model (lead time, impossible ages, target conversion) stay locked down.
"""

import pandas as pd
import pytest

from clean_appointments import clean


def raw_row(**overrides) -> dict:
    """One appointment in the raw Kaggle schema; override any field."""
    row = {
        "PatientId": 12345678901.0,
        "AppointmentID": 5600001,
        "Gender": "F",
        "ScheduledDay": "2026-04-01T10:15:00Z",
        "AppointmentDay": "2026-04-08T00:00:00Z",
        "Age": 42,
        "Neighbourhood": "CENTRO",
        "Scholarship": 0,
        "Hipertension": 0,
        "Diabetes": 0,
        "Alcoholism": 0,
        "Handcap": 0,
        "SMS_received": 1,
        "No-show": "No",
    }
    row.update(overrides)
    return row


def raw_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestColumnStandardization:
    def test_columns_are_renamed_to_snake_case(self):
        out = clean(raw_frame([raw_row()]))

        for col in ("patient_id", "appointment_id", "scheduled_datetime",
                    "appointment_datetime", "neighborhood", "scholarship_flag",
                    "hypertension_flag", "sms_received", "no_show_flag"):
            assert col in out.columns

        # Raw Kaggle spellings must not survive cleaning.
        for col in ("Hipertension", "Handcap", "No-show", "Neighbourhood"):
            assert col not in out.columns

    def test_no_show_target_becomes_boolean(self):
        out = clean(raw_frame([
            raw_row(AppointmentID=1, **{"No-show": "Yes"}),
            raw_row(AppointmentID=2, **{"No-show": "No"}),
        ]))

        assert out["no_show_flag"].dtype == bool
        by_id = out.set_index("appointment_id")["no_show_flag"]
        assert bool(by_id.loc[1]) is True
        assert bool(by_id.loc[2]) is False

    def test_no_show_parsing_tolerates_case_and_whitespace(self):
        out = clean(raw_frame([raw_row(**{"No-show": " YES "})]))

        assert bool(out["no_show_flag"].iloc[0]) is True


class TestLeadTimeDays:
    def test_lead_time_is_calendar_days_between_scheduling_and_visit(self):
        out = clean(raw_frame([raw_row(
            ScheduledDay="2026-04-01T10:15:00Z",
            AppointmentDay="2026-04-08T00:00:00Z",
        )]))

        assert out["lead_time_days"].iloc[0] == 7

    def test_same_day_booking_has_zero_lead_time(self):
        # Booked at 09:30, seen the same day: the time-of-day difference must
        # not round the lead time up or down to a non-zero value.
        out = clean(raw_frame([raw_row(
            ScheduledDay="2026-04-08T09:30:00Z",
            AppointmentDay="2026-04-08T00:00:00Z",
        )]))

        assert out["lead_time_days"].iloc[0] == 0

    def test_lead_time_ignores_time_of_day(self):
        # Scheduled late on day 1 for early on day 2 is still a 1-day lead.
        out = clean(raw_frame([raw_row(
            ScheduledDay="2026-04-07T23:50:00Z",
            AppointmentDay="2026-04-08T00:00:00Z",
        )]))

        assert out["lead_time_days"].iloc[0] == 1

    def test_negative_lead_time_rows_are_removed(self):
        # Scheduling *after* the visit day is a data error, not a real booking.
        out = clean(raw_frame([
            raw_row(AppointmentID=1),
            raw_row(AppointmentID=2, ScheduledDay="2026-04-10T10:00:00Z",
                    AppointmentDay="2026-04-08T00:00:00Z"),
        ]))

        assert out["appointment_id"].tolist() == [1]
        assert (out["lead_time_days"] >= 0).all()


class TestImpossibleAges:
    def test_negative_age_is_removed(self):
        # The real Kaggle extract contains an Age = -1 record.
        out = clean(raw_frame([
            raw_row(AppointmentID=1, Age=30),
            raw_row(AppointmentID=2, Age=-1),
        ]))

        assert out["appointment_id"].tolist() == [1]

    def test_implausible_old_age_is_removed(self):
        out = clean(raw_frame([
            raw_row(AppointmentID=1, Age=99),
            raw_row(AppointmentID=2, Age=115),
        ]))

        assert out["appointment_id"].tolist() == [1]

    @pytest.mark.parametrize("age", [0, 1, 50, 100])
    def test_valid_ages_are_kept(self, age):
        # Age 0 is a real newborn visit and must survive; 100 is the boundary.
        out = clean(raw_frame([raw_row(Age=age)]))

        assert len(out) == 1
        assert out["age"].iloc[0] == age


class TestDeduplicationAndCalendarFeatures:
    def test_duplicate_appointment_ids_are_dropped(self):
        out = clean(raw_frame([raw_row(AppointmentID=7), raw_row(AppointmentID=7)]))

        assert len(out) == 1

    def test_calendar_features_match_the_appointment_date(self):
        # 2026-04-08 is a Wednesday; it was scheduled Wednesday 2026-04-01.
        out = clean(raw_frame([raw_row(
            ScheduledDay="2026-04-01T10:15:00Z",
            AppointmentDay="2026-04-08T00:00:00Z",
        )]))
        row = out.iloc[0]

        assert row["appointment_day_of_week"] == "Wednesday"
        assert row["scheduled_day_of_week"] == "Wednesday"
        assert row["appointment_month"] == 4
        assert bool(row["is_weekend"]) is False

    def test_weekend_appointment_is_flagged(self):
        # 2026-04-11 is a Saturday.
        out = clean(raw_frame([raw_row(
            ScheduledDay="2026-04-01T10:15:00Z",
            AppointmentDay="2026-04-11T00:00:00Z",
        )]))

        assert bool(out["is_weekend"].iloc[0]) is True
        assert out["appointment_day_of_week"].iloc[0] == "Saturday"
