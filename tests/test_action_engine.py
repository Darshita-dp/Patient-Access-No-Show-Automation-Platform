"""Recommended action engine.

The model predicts risk; this engine turns risk into an operational next step.
These tests encode the patient access playbook: high risk must always produce a
human touch, low risk must never burn staff time, and every recommendation must
carry a reason a coordinator can read aloud.
"""

import pytest

from api.services.action_engine import ACTION_TASK_MAP, recommend_action


def appt(**overrides) -> dict:
    """A scored appointment as the engine receives it."""
    row = {
        "risk_category": "Low",
        "hours_until_appointment": 100.0,
        "patient_no_show_rate": 0.1,
        "sms_received": True,
        "handicap_flag": 0,
    }
    row.update(overrides)
    return row


class TestHighRisk:
    def test_high_risk_within_48_hours_triggers_a_direct_call(self):
        action, reason, priority = recommend_action(
            appt(risk_category="High", hours_until_appointment=24))

        assert action == "Call patient directly and confirm attendance"
        assert priority == "High"
        assert reason

    def test_high_risk_without_sms_sends_reminder_and_creates_follow_up(self):
        # Outside the call window, so the reminder gap is the thing to close.
        action, _, priority = recommend_action(
            appt(risk_category="High", hours_until_appointment=100,
                 sms_received=False))

        assert action == "Send SMS reminder and create staff follow-up task"
        assert priority == "High"

    def test_repeat_no_show_history_escalates_to_the_access_team(self):
        # Chronic no-shows outrank the generic call rule: reminders have
        # already failed for this patient.
        action, reason, priority = recommend_action(
            appt(risk_category="High", hours_until_appointment=24,
                 patient_no_show_rate=0.6))

        assert action == "Escalate to access team for direct outreach"
        assert priority == "High"
        assert "60%" in reason

    def test_mobility_need_inside_72_hours_confirms_transportation(self):
        action, _, priority = recommend_action(
            appt(risk_category="High", hours_until_appointment=60,
                 handicap_flag=2))

        assert action == "Confirm transportation and attendance"
        assert priority == "High"

    def test_high_risk_far_out_still_gets_a_human_action(self):
        # Even with reminders sent, clean history, and no mobility need, a
        # high-risk visit must never fall through to "no action".
        action, _, priority = recommend_action(
            appt(risk_category="High", hours_until_appointment=300))

        assert action == "Call patient directly and confirm attendance"
        assert priority == "High"

    @pytest.mark.parametrize("hours", [1, 24, 47.9, 48, 72, 200, 500])
    def test_high_risk_never_returns_no_action(self, hours):
        action, _, _ = recommend_action(
            appt(risk_category="High", hours_until_appointment=hours))

        assert action != "No manual action needed"

    def test_escalation_outranks_transportation_and_call_rules(self):
        # All three conditions true at once — history must win.
        action, _, _ = recommend_action(
            appt(risk_category="High", hours_until_appointment=12,
                 patient_no_show_rate=0.75, handicap_flag=3))

        assert action == "Escalate to access team for direct outreach"


class TestMediumRisk:
    def test_medium_risk_inside_72_hours_sends_an_automated_reminder(self):
        action, _, priority = recommend_action(
            appt(risk_category="Medium", hours_until_appointment=48))

        assert action == "Send automated reminder"
        assert priority == "Medium"

    def test_medium_risk_outside_the_window_is_only_monitored(self):
        action, _, priority = recommend_action(
            appt(risk_category="Medium", hours_until_appointment=200))

        assert action == "Monitor appointment"
        assert priority == "Medium"

    def test_medium_risk_never_escalates_to_a_manual_call(self):
        for hours in (1, 24, 72, 100, 400):
            action, _, _ = recommend_action(
                appt(risk_category="Medium", hours_until_appointment=hours))

            assert action != "Call patient directly and confirm attendance"


class TestLowRisk:
    @pytest.mark.parametrize("hours", [1, 24, 72, 500])
    def test_low_risk_never_creates_manual_work(self, hours):
        action, _, priority = recommend_action(
            appt(risk_category="Low", hours_until_appointment=hours))

        assert action == "No manual action needed"
        assert priority == "Low"

    def test_low_risk_ignores_history_and_missing_reminders(self):
        # Staff capacity is finite: only the risk band opens the queue.
        action, _, _ = recommend_action(
            appt(risk_category="Low", hours_until_appointment=12,
                 patient_no_show_rate=0.9, sms_received=False, handicap_flag=4))

        assert action == "No manual action needed"

    def test_low_risk_action_creates_no_staff_task(self):
        action, _, _ = recommend_action(appt(risk_category="Low"))

        assert action not in ACTION_TASK_MAP


class TestContractAndRobustness:
    def test_every_recommendation_has_a_reason_and_valid_priority(self):
        cases = [
            appt(risk_category="High", hours_until_appointment=10),
            appt(risk_category="High", patient_no_show_rate=0.8),
            appt(risk_category="Medium", hours_until_appointment=10),
            appt(risk_category="Medium", hours_until_appointment=400),
            appt(risk_category="Low"),
        ]

        for case in cases:
            action, reason, priority = recommend_action(case)

            assert action and isinstance(action, str)
            assert len(reason) > 20, f"reason too thin for {action}"
            assert priority in {"Low", "Medium", "High"}

    def test_actions_needing_a_human_are_all_mapped_to_task_types(self):
        # Anything requiring staff effort must be routable to the task board,
        # otherwise the recommendation dead-ends.
        human_actions = [
            recommend_action(appt(risk_category="High", hours_until_appointment=10))[0],
            recommend_action(appt(risk_category="High", patient_no_show_rate=0.8))[0],
            recommend_action(appt(risk_category="High", hours_until_appointment=60,
                                  handicap_flag=2))[0],
            recommend_action(appt(risk_category="High", hours_until_appointment=100,
                                  sms_received=False))[0],
            recommend_action(appt(risk_category="Medium",
                                  hours_until_appointment=10))[0],
        ]

        for action in human_actions:
            assert action in ACTION_TASK_MAP
            task_type, priority = ACTION_TASK_MAP[action]
            assert task_type and priority in {"Low", "Medium", "High"}

    def test_missing_optional_fields_fall_back_safely(self):
        # Sparse rows must not raise — a KeyError here would break scoring.
        action, _, _ = recommend_action(
            {"risk_category": "High", "hours_until_appointment": 10})

        assert action == "Call patient directly and confirm attendance"

    def test_none_handicap_flag_is_treated_as_no_mobility_need(self):
        action, _, _ = recommend_action(
            appt(risk_category="High", hours_until_appointment=60,
                 handicap_flag=None))

        assert action != "Confirm transportation and attendance"
