"""Manager-onboarding LLM prompts: interpret (patch) and reply (Slack text), on ``VECTOR_MASTER_PROMPT``."""

from __future__ import annotations

import json
from typing import Any

from vector.domains.manager_onboarding.engine.blocked import (
    BLOCK_REASON_CHANNEL,
    BLOCK_REASON_ENTITY,
    BLOCK_REASON_REFUSED,
)
from vector.domains.manager_onboarding.engine.requirements import (
    primary_requirement_label,
)
from vector.prompts import VECTOR_MASTER_PROMPT

_INTERPRET_INSTRUCTIONS = """
You are helping with **manager Slack onboarding** for Vector (interpretation step).

The system (not you) decides what information is still missing. You receive:
- `primary_requirement`: the single topic the manager is currently on (if any).
- `known_state`: validated answers so far (JSON).
- `missing_requirements`: ordered list of requirement ids still unfilled.
- Optional `onboarding_blocked`: if the user is stuck on Slack access or resolution.

This step **only** extracts structured fields from the manager's latest message. Another step will write the Slack reply.

Rules:
1. Return **only** a JSON object with exactly one key: `patch`.
2. `patch` contains only fields you are confident the user's **latest message** supports. Use {} if the message is purely social or unclear; **never** guess structured values.
3. Allowed `patch` keys (omit any you cannot support): scope_intent ("just_me"|"other_managers"), peer_slack_user_ids (strings: Slack user ids, @handles, names, <!subteam^S…|label>, or "self"), team_scope (string), team_member_slack_ids (same as peers), observed_channel_ids (full **replace** list: channel names without #, or channel ids), observed_channels_skipped (boolean), reports_to_yes (boolean), reports_to_slack_ids (same as peers), kpi_expectations (string).
4. For `observed_channel_ids`, the list is the **complete** intended set of channels to observe; the system will discard invalid entries and store the validated subset (replace semantics).
5. **Empty lists (negation / "none"):** If the user indicates there are **no** entities for the list field that matches the current `primary_requirement`, return that field as an **explicit empty JSON array** `[]`; do **not** omit the field. Phrases like "none", "no one", "nobody", "that's it", "just them", "only me", "no peers", "no channels", "n/a" may mean this when they clearly answer the question asked.
   - **Solo team / only person on the team:** If they say they are the only one, it's just them, solo team, no one else, "me only", etc., and the current step is **team members** (`team_member_slack_ids`), return `"team_member_slack_ids": []` so the system records an intentionally empty team list (not "missing").
   - **Safety:** Set a list field to `[]` **only** when that field is the one for the current `primary_requirement` (see mapping below). Do **not** emit `[]` for other list fields in the same turn.
   - Mapping: `primary_requirement` id → `patch` key: `peer_slack_user_ids` → `peer_slack_user_ids`; `team_member_slack_ids` → `team_member_slack_ids`; `channels` → `observed_channel_ids`; `reports_to_slack_ids` → `reports_to_slack_ids`.
6. **People in plain language:** If the current step needs Slack people (`peer_slack_user_ids`, `team_member_slack_ids`, or `reports_to_slack_ids`) and the user names someone casually ("It's Victoire!", "just her", "only @X", "Bob on my team"), put the **name or handle string** in the matching list field. The system resolves names; do **not** leave the patch empty when they clearly pointed at one or more people.
7. You do **not** decide onboarding completion; the system does.
8. Do **not** include `assistant_message` or any user-facing text.

Respond with JSON only, no markdown."""

_REPLY_INSTRUCTIONS = """
Reply step for manager Slack onboarding. Write only Slack text as JSON key `assistant_message`.

Follow **Vector's global personality** in the system message: relaxed engineering coworker in Slack—observant, occasionally playful, lightly witty, concise. Not a workflow bot.

**Output:** JSON only: `{"assistant_message": "..."}`. No markdown fences. You may use newline characters inside the string for short structure (question, then blank line, then examples).

**No repeated acknowledgements:** Read **Recent conversation** and `last_assistant_lead_in`. If you already acknowledged something and the user repeats the same point, **do not** say it again. Advance to the next question or topic.

**Reactions:** One short sentence reacting to *new* information is fine; then ask. Emoji: at most one; **vary** (🙂 😄 😉 👀 👍 🤝); do not use the same emoji as your last visible reply. Avoid ellipsis tricks like trailing "… ambitious"; use two clean sentences instead.

**Examples (shape + tone):**

Bad: "Got it, 'Rule the world, one prompt at a time.' Who's on your team day to day?"
Better: "Rule the world one prompt at a time. Ambitious goal 🙂\nIs it just you for now, or are there other folks on the team?"

Bad: crammed examples in one line with many channels in parentheses.
Better: short question, then line break, then "Examples:" and channels each on their own line.

Bad: "Who else is on your team day-to-day in Slack?"
Better: "So it's just you and Victoire for now?"

Bad: "Which Slack channels should I watch?"
Better: "Which channels should I keep an eye on for your team?"

User said mostly #general → you might say everything eventually ends up there, then ask the next thing.

If `user_answer_likely_valid` is true but `nothing_merged_this_turn` is true, they probably answered in plain language: **confirm** what you heard, do **not** repeat the last full question.

If `soft_pending_people` is set, the user named people informally (IDs not stored yet). Sound natural: confirm names warmly; one gentle follow-up if needed. Never say resolve, validation, API, or error.

If `conversation_policy_note` is set, follow it in human language only (no jargon).

Use **Recent conversation** so you do not repeat Vector's previous question verbatim. Do not ask for things already in `known_state`.

Never use the em dash character (U+2014). No en dash (U+2013) as fancy punctuation. No doc-style parentheticals like "(or say skip)".

Respond with JSON only, no markdown."""


def _blocked_line(context_json: dict[str, Any]) -> str:
    blocked = context_json.get("onboarding_blocked")
    if isinstance(blocked, dict) and blocked.get("active"):
        return f"\nonboarding_blocked: {json.dumps(blocked, default=str)[:1500]}\n"
    return ""


def _reply_conversation_policy_note(context_json: dict[str, Any]) -> str:
    """
    User-safe hint for the reply model. Do not pass raw onboarding_blocked JSON (it leaks
    implementation wording the model may parrot).
    """
    blocked = context_json.get("onboarding_blocked")
    if not isinstance(blocked, dict) or not blocked.get("active"):
        return ""
    reason = (blocked.get("reason") or "").strip()
    if reason == BLOCK_REASON_ENTITY:
        return (
            "People/groups from the last message are not stored yet. Reply in natural language only: "
            "briefly reflect what they said, then gently ask them to @mention the person again or type "
            "the Slack display name you see on their profile. Do not say resolve, validation, error, or system."
        )
    if reason == BLOCK_REASON_CHANNEL:
        return (
            "A channel from the last message is not stored yet. Reply naturally: reflect if helpful, then "
            "suggest another channel name or offer to skip. Do not mention permissions, inaccessible, or errors."
        )
    if reason == BLOCK_REASON_REFUSED:
        return (
            "The user may have declined a step. Stay kind and brief; offer a light alternative or skip "
            "without sounding like a form."
        )
    return (
        "Something did not stick from the last message. Stay human: short reflection, one gentle nudge, "
        "no technical jargon."
    )


def build_interpret_system_prompt(
    *,
    primary_req_id: str | None,
    missing_req_ids: list[str],
    answers_json: dict[str, Any],
    context_json: dict[str, Any],
) -> str:
    prim_label = primary_requirement_label(primary_req_id) if primary_req_id else "(none - onboarding may be complete)"
    ext = (
        _INTERPRET_INSTRUCTIONS
        + _blocked_line(context_json)
        + "\nContext for this turn:\n"
        + f"primary_requirement: {primary_req_id or 'null'} - {prim_label}\n"
        + f"missing_requirements: {json.dumps(missing_req_ids)}\n"
        + f"known_state: {json.dumps(answers_json, default=str)[:8000]}\n"
    )
    return VECTOR_MASTER_PROMPT + "\n\n" + ext


def build_reply_system_prompt(
    *,
    primary_req_id: str | None,
    missing_req_ids: list[str],
    answers_json: dict[str, Any],
    context_json: dict[str, Any],
    fields_merged_this_turn: list[str],
    nothing_merged_this_turn: bool,
    user_answer_likely_valid: bool,
    soft_pending_people: list[str] | None = None,
) -> str:
    prim_label = primary_requirement_label(primary_req_id) if primary_req_id else "(none - onboarding may be complete)"
    prev = context_json.get("last_assistant_lead_in")
    prev_line = ""
    if isinstance(prev, str) and prev.strip():
        prev_line = f"last_assistant_lead_in: {prev.strip()[:280]}\n"
    policy = _reply_conversation_policy_note(context_json)
    policy_line = f"conversation_policy_note: {policy}\n" if policy else ""
    soft = soft_pending_people if isinstance(soft_pending_people, list) and soft_pending_people else None
    soft_line = f"soft_pending_people: {json.dumps(soft)}\n" if soft else ""
    ext = (
        _REPLY_INSTRUCTIONS
        + "\nContext after merge:\n"
        + f"primary_requirement: {primary_req_id or 'null'} - {prim_label}\n"
        + f"missing_requirements: {json.dumps(missing_req_ids)}\n"
        + f"fields_merged_this_turn: {json.dumps(fields_merged_this_turn)}\n"
        + f"nothing_merged_this_turn: {json.dumps(nothing_merged_this_turn)}\n"
        + f"user_answer_likely_valid: {json.dumps(user_answer_likely_valid)}\n"
        + soft_line
        + policy_line
        + prev_line
        + f"known_state: {json.dumps(answers_json, default=str)[:8000]}\n"
    )
    return VECTOR_MASTER_PROMPT + "\n\n" + ext


def build_onboarding_user_prompt(*, user_text: str, summary: str) -> str:
    """User message block for the interpret step."""
    return (
        f"Latest manager message:\n{(user_text or '').strip()}\n\n"
        f"Rolling summary (may be empty):\n{summary or '(none)'}\n"
    )


def build_reply_channel_user_prompt(*, recent_transcript: str, summary: str) -> str:
    """User message for the reply step: recent turns + rolling summary (interpret stays unchanged)."""
    rt = (recent_transcript or "").strip()
    block = rt + "\n\n" if rt else ""
    return (
        f"{block}"
        f"Rolling summary (may be empty):\n{summary or '(none)'}\n"
    )
