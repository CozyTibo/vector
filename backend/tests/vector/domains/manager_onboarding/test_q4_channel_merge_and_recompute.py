"""Q4 channel persistence and admin recompute counter reset."""

from __future__ import annotations

from vector.domains.manager_onboarding.constants import STEP_Q4_OBSERVED_CHANNELS
from vector.domains.manager_onboarding.service import _reset_messages_counter_for_step


def test_reset_messages_counter_for_step_zeros_budget_on_same_step() -> None:
    """Admin recompute must reset the Q4 watchdog counter even when step stays Q4."""
    sess = type(
        "Row",
        (),
        {
            "context_json": {
                "counter_step": STEP_Q4_OBSERVED_CHANNELS,
                "messages_this_step": 99,
            },
        },
    )()

    _reset_messages_counter_for_step(sess, STEP_Q4_OBSERVED_CHANNELS)

    assert sess.context_json["counter_step"] == STEP_Q4_OBSERVED_CHANNELS
    assert sess.context_json["messages_this_step"] == 0
