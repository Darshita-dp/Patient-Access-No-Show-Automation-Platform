"""Waitlist matching engine.

The business rule that matters most here is counter-intuitive: filling a slot
is NOT the same job as outreach. Outreach targets high-risk patients; slot
filling wants someone who will actually show up. So low no-show risk scores
POSITIVELY, and these tests defend that.
"""

from datetime import datetime

import pandas as pd
import pytest

from api.services.waitlist_matching import (
    WEIGHTS, availability_match_score, days_waiting_score,
    rank_candidates_for_slot,
)

NOW = datetime(2026, 7, 15, 8, 0)

# Wednesday 10:00 — a mid-morning weekday slot.
SLOT = {
    "slot_id": 1,
    "slot_datetime": "2026-07-22 10:00:00",
    "provider_id": 7,
    "clinic_id": 3,
    "specialty": "Cardiology",
}


def waitlist_row(waitlist_id=1, patient_id=1000, **overrides) -> dict:
    row = {
        "waitlist_id": waitlist_id,
        "patient_id": patient_id,
        "patient_name": f"Synthetic Patient {patient_id}",
        "requested_specialty": "Cardiology",
        "preferred_clinic_id": 3,
        "preferred_provider_id": "",
        "requested_date": "2026-07-01",  # 14 days waiting as of NOW
        "urgency_level": "Routine",
        "availability_window": "Any time",
        "waitlist_status": "Active",
    }
    row.update(overrides)
    return row


def waitlist(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


def rank(rows, patient_risk=None, top_n=5):
    return rank_candidates_for_slot(
        SLOT, waitlist(rows), patient_risk or {}, NOW, top_n=top_n)


class TestEligibilityFiltering:
    def test_only_matching_specialty_is_eligible(self):
        results = rank([
            waitlist_row(1, 1000, requested_specialty="Cardiology"),
            waitlist_row(2, 2000, requested_specialty="Dermatology"),
        ])

        assert [c["waitlist_id"] for c in results] == [1]

    def test_patients_preferring_another_clinic_are_excluded(self):
        results = rank([
            waitlist_row(1, 1000, preferred_clinic_id=3),   # slot's clinic
            waitlist_row(2, 2000, preferred_clinic_id=99),  # elsewhere
        ])

        assert [c["waitlist_id"] for c in results] == [1]

    def test_patient_with_no_clinic_preference_is_eligible(self):
        results = rank([waitlist_row(1, 1000, preferred_clinic_id=None)])

        assert len(results) == 1

    @pytest.mark.parametrize("status,eligible", [
        ("Active", True), ("Contacted", True), ("Scheduled Elsewhere", False),
    ])
    def test_only_open_waitlist_statuses_are_offered_slots(self, status, eligible):
        # Someone already booked elsewhere must never be offered a slot.
        results = rank([waitlist_row(1, 1000, waitlist_status=status)])

        assert bool(results) is eligible

    def test_no_eligible_candidates_returns_empty_not_error(self):
        assert rank([waitlist_row(1, 1000, requested_specialty="Oncology")]) == []


class TestPrioritization:
    def test_urgent_patient_outranks_routine_all_else_equal(self):
        results = rank([
            waitlist_row(1, 1000, urgency_level="Routine"),
            waitlist_row(2, 2000, urgency_level="Urgent"),
        ])

        assert results[0]["waitlist_id"] == 2
        assert results[0]["urgency_level"] == "Urgent"

    def test_longer_wait_outranks_shorter_wait_all_else_equal(self):
        results = rank([
            waitlist_row(1, 1000, requested_date="2026-07-13"),  # 2 days
            waitlist_row(2, 2000, requested_date="2026-06-20"),  # 25 days
        ])

        assert results[0]["waitlist_id"] == 2
        assert results[0]["days_waiting"] == 25

    def test_better_availability_fit_outranks_poor_fit(self):
        # Slot is 10:00; "After 3pm only" barely fits.
        results = rank([
            waitlist_row(1, 1000, availability_window="After 3pm only"),
            waitlist_row(2, 2000, availability_window="Any time"),
        ])

        assert results[0]["waitlist_id"] == 2

    def test_provider_preference_breaks_an_otherwise_exact_tie(self):
        results = rank([
            waitlist_row(1, 1000, preferred_provider_id=""),
            waitlist_row(2, 2000, preferred_provider_id=7),  # the slot's provider
        ])

        assert results[0]["waitlist_id"] == 2
        assert results[0]["same_provider_score"] == 1.0

    def test_results_are_sorted_by_descending_match_score(self):
        results = rank([
            waitlist_row(1, 1000, urgency_level="Routine"),
            waitlist_row(2, 2000, urgency_level="Urgent"),
            waitlist_row(3, 3000, urgency_level="Soon"),
        ])

        scores = [c["match_score"] for c in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_limits_returned_candidates(self):
        rows = [waitlist_row(i, 1000 + i) for i in range(1, 8)]

        assert len(rank(rows, top_n=3)) == 3


class TestAttendanceLikelihood:
    def test_reliable_attender_is_preferred_over_frequent_no_shower(self):
        # The core rule: fill the slot with someone likely to attend.
        results = rank(
            [waitlist_row(1, 1000), waitlist_row(2, 2000)],
            patient_risk={1000: 0.8, 2000: 0.05},
        )

        assert results[0]["patient_id"] == 2000

    def test_low_risk_score_is_the_inverse_of_no_show_risk(self):
        results = rank([waitlist_row(1, 1000)], patient_risk={1000: 0.3})

        assert results[0]["low_risk_score"] == pytest.approx(0.7)

    def test_urgency_still_outweighs_attendance_risk(self):
        # Risk is only 15% of the score; an urgent patient should not be
        # displaced by a routine one merely for being more reliable.
        results = rank(
            [
                waitlist_row(1, 1000, urgency_level="Urgent"),
                waitlist_row(2, 2000, urgency_level="Routine"),
            ],
            patient_risk={1000: 0.5, 2000: 0.0},
        )

        assert results[0]["urgency_level"] == "Urgent"

    def test_unknown_patient_risk_falls_back_to_a_neutral_default(self):
        results = rank([waitlist_row(1, 1000)], patient_risk={})

        assert 0.0 < results[0]["low_risk_score"] < 1.0


class TestScoringComponents:
    def test_weights_sum_to_one(self):
        assert sum(WEIGHTS.values()) == pytest.approx(1.0)

    def test_match_score_equals_the_weighted_component_formula(self):
        results = rank(
            [waitlist_row(1, 1000, urgency_level="Urgent",
                          requested_date="2026-07-01", preferred_provider_id=7)],
            patient_risk={1000: 0.2},
        )
        c = results[0]

        expected = (
            c["urgency_score"] * WEIGHTS["urgency"]
            + days_waiting_score(c["days_waiting"]) * WEIGHTS["days_waiting"]
            + c["availability_score"] * WEIGHTS["availability"]
            + c["low_risk_score"] * WEIGHTS["low_risk"]
            + c["same_provider_score"] * WEIGHTS["same_provider"]
        )
        assert c["match_score"] == pytest.approx(expected, abs=1e-4)

    def test_match_score_stays_within_zero_and_one(self):
        best = rank(
            [waitlist_row(1, 1000, urgency_level="Urgent",
                          requested_date="2026-01-01",
                          availability_window="Any time", preferred_provider_id=7)],
            patient_risk={1000: 0.0},
        )[0]
        worst = rank(
            [waitlist_row(2, 2000, urgency_level="Routine",
                          requested_date="2026-07-15",
                          availability_window="Tue/Thu only")],
            patient_risk={2000: 1.0},
        )[0]

        assert 0.0 <= worst["match_score"] < best["match_score"] <= 1.0

    def test_days_waiting_score_saturates_at_thirty_days(self):
        assert days_waiting_score(0) == 0.0
        assert days_waiting_score(15) == pytest.approx(0.5)
        assert days_waiting_score(30) == 1.0
        assert days_waiting_score(365) == 1.0  # no runaway advantage

    def test_negative_days_waiting_does_not_produce_a_negative_score(self):
        assert days_waiting_score(-5) == 0.0


class TestAvailabilityWindows:
    @pytest.mark.parametrize("window,expected_full_match", [
        ("Any time", True),
        ("Any weekday", True),
        ("Weekday mornings", True),        # slot is 10:00
        ("Mornings before 10am", False),   # slot is exactly 10:00 — too late
        ("After 3pm only", False),
        ("Mon/Wed/Fri only", True),        # slot is a Wednesday
        ("Tue/Thu only", False),
    ])
    def test_window_fit_against_a_wednesday_10am_slot(self, window, expected_full_match):
        slot_dt = datetime(2026, 7, 22, 10, 0)

        score = availability_match_score(window, slot_dt)

        assert (score >= 0.99) is expected_full_match
        assert 0.0 <= score <= 1.0

    def test_unknown_window_text_is_scored_neutrally(self):
        score = availability_match_score("Alternate Thursdays", datetime(2026, 7, 22, 10, 0))

        assert score == 0.5


class TestMatchReason:
    def test_reason_is_human_readable_and_cites_the_drivers(self):
        results = rank(
            [waitlist_row(1, 1000, urgency_level="Urgent",
                          requested_date="2026-06-27",  # 18 days
                          availability_window="Any time")],
            patient_risk={1000: 0.05},
        )
        reason = results[0]["match_reason"]

        assert reason.startswith("Matched because patient ")
        assert reason.endswith(".")
        assert "Cardiology" in reason
        assert "urgent clinical priority" in reason
        assert "18 days" in reason
        assert "available during the open appointment window" in reason

    def test_every_candidate_carries_a_reason(self):
        results = rank([waitlist_row(i, 1000 + i) for i in range(1, 4)])

        assert all(c["match_reason"] for c in results)
