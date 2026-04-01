"""Deterministic onboarding state machine (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vector.domains.onboarding.answer_normalize import (
    normalize_company_name,
    normalize_company_size,
    normalize_person_name,
    normalize_role,
    normalize_website,
)
from vector.domains.onboarding.constants import (
    PROFILE_PHASE_DONE,
    PROFILE_PHASE_NAME,
    PROFILE_PHASE_ORG,
    PROFILE_PHASE_ROLE,
    PROFILE_PHASE_SIZE,
    PROFILE_PHASE_TOOLS,
    PROFILE_PHASE_WEBSITE,
    PROFILE_PHASES_ORDER,
    STEP_CHAT_PROFILE,
    STEP_CONNECT_GITHUB,
    STEP_CONNECT_LINEAR,
    STEP_CONNECT_SLACK,
    STEP_SCANNING,
    STEP_THANK_YOU,
    TOOL_CATEGORY_KEYS,
)


@dataclass(frozen=True)
class OnboardingTurnResult:
    next_step: str
    answers_updates: dict[str, Any]
    assistant_prompt_context: dict[str, Any]


def _norm_str(value: str) -> str:
    return " ".join(value.split()).strip()


def _next_profile_phase(phase: str) -> str:
    try:
        idx = PROFILE_PHASES_ORDER.index(phase)
    except ValueError:
        return PROFILE_PHASE_NAME
    if idx + 1 < len(PROFILE_PHASES_ORDER):
        return PROFILE_PHASES_ORDER[idx + 1]
    return PROFILE_PHASE_DONE


def _default_profile_phase(answers: dict[str, Any]) -> str:
    raw = answers.get("profile_phase")
    if isinstance(raw, str) and raw in PROFILE_PHASES_ORDER:
        return raw
    return PROFILE_PHASE_NAME


def _merge_tools_categories(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    base = existing.get("tools")
    if isinstance(base, dict):
        for k, v in base.items():
            if k in TOOL_CATEGORY_KEYS and isinstance(v, list):
                out[k] = [str(x) for x in v if isinstance(x, str)]
    for k, v in incoming.items():
        if k not in TOOL_CATEGORY_KEYS:
            continue
        if not isinstance(v, list):
            continue
        out[k] = sorted({str(x) for x in v if isinstance(x, str)})
    return out


def _connect_queue_from_tools(tools: dict[str, list[str]]) -> list[str]:
    """Order: GitHub (engineering) then Linear (pm) when selected."""
    q: list[str] = []
    eng = tools.get("engineering") or []
    pm = tools.get("pm") or []
    if "github" in eng and "github" not in q:
        q.append("github")
    if "linear" in pm and "linear" not in q:
        q.append("linear")
    return q


def _oauth_connector_labels_in_order(connect_queue: list[str]) -> list[str]:
    labels: list[str] = []
    for x in connect_queue:
        if x == "github":
            labels.append("GitHub")
        elif x == "linear":
            labels.append("Linear")
    return labels


def _tools_post_pick_instruction(*, prior: bool, oauth_labels: list[str]) -> str:
    """LLM instructions grounded in actual OAuth queue (avoid naming Linear if not selected)."""
    slack_line = (
        "Slack is planned in-product (separate from OAuth). The next screen frames Slack first."
    )
    if oauth_labels:
        only_oauth = (
            "Ground truth for OAuth installs: only these, in order: "
            + " → ".join(oauth_labels)
            + ". Never mention Linear unless it appears in that list. "
            "Never mention GitHub unless it appears in that list."
        )
    else:
        only_oauth = (
            "Ground truth: no GitHub or Linear OAuth is queued from their picks. "
            "Do not say we will connect GitHub or Linear."
        )
    if prior:
        return (
            "They revised their tool picks again. "
            "Anti-repeat: do NOT mirror your previous message's shape or vocabulary. "
            "Do NOT open with 'Noticed', 'Looks like you've', or 'I see you've'. "
            "Prefer no recap, or under 8 words, then next steps only. "
            "Do not repeat the same closing question (e.g. 'anything to prioritize'). "
            f"{slack_line} {only_oauth}"
        )
    return (
        "Briefly acknowledge their tool choices without listing every tool. "
        f"{slack_line} {only_oauth}"
    )


def _slack_transition_result(answers: dict[str, Any]) -> OnboardingTurnResult:
    """After profile tools are saved, move into connector guidance."""
    tools = _merge_tools_categories(answers, {})
    cq = _connect_queue_from_tools(tools)
    ti = _tools_interest_flat(tools)
    updates: dict[str, Any] = {
        "connect_queue": cq,
        "connect_plan": list(cq),
        "tools_interest": ti,
    }
    ctx_base: dict[str, Any] = {"step": STEP_CONNECT_SLACK}
    if not cq:
        return OnboardingTurnResult(
            next_step=STEP_SCANNING,
            answers_updates=updates,
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "No GitHub or Linear was selected. Explain they can connect integrations later "
                    "from settings; offer to proceed while Vector prepares the workspace."
                ),
            },
        )
    first = cq[0]
    next_s = STEP_CONNECT_GITHUB if first == "github" else STEP_CONNECT_LINEAR
    labs = _oauth_connector_labels_in_order(cq)
    oauth_txt = (
        f"Only these OAuth connectors apply on the upcoming screens, in order: {' then '.join(labs)}. "
        "Do not name Linear or GitHub unless it appears in that list."
    )
    return OnboardingTurnResult(
        next_step=next_s,
        answers_updates=updates,
        assistant_prompt_context={
            **ctx_base,
            "instruction": (
                f"Slack is planned for this workspace. {oauth_txt} "
                "Guide them to use the in-app buttons on the next screens."
            ),
            "connect_queue": cq,
            "oauth_connector_labels_in_order": labs,
        },
    )


def _had_prior_tool_selection(answers: dict[str, Any]) -> bool:
    """True if answers already stored a non-empty tools map (e.g. user is re-submitting after edit)."""
    raw = answers.get("tools")
    if not isinstance(raw, dict):
        return False
    for key in TOOL_CATEGORY_KEYS:
        v = raw.get(key)
        if isinstance(v, list) and len(v) > 0:
            return True
    return False


def _tools_interest_flat(tools: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for _k, ids in sorted(tools.items()):
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
    return out


def handle_turn(
    current_step: str,
    user_message: str | None,
    structured_action: dict[str, Any] | None,
    answers_json: dict[str, Any],
) -> OnboardingTurnResult:
    """Pure deterministic transition for one chat turn."""
    msg = _norm_str(user_message or "")
    action = structured_action if isinstance(structured_action, dict) else None
    answers = dict(answers_json or {})

    ctx_base: dict[str, Any] = {"step": current_step}

    if current_step == STEP_THANK_YOU:
        return OnboardingTurnResult(
            next_step=STEP_THANK_YOU,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "Onboarding is complete. Briefly congratulate the user and invite them to "
                    "explore Vector."
                ),
            },
        )

    if current_step == STEP_SCANNING:
        return OnboardingTurnResult(
            next_step=STEP_SCANNING,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "The workspace is syncing in the background. Reassure the user and say they "
                    "can continue once ingestion finishes."
                ),
            },
        )

    if current_step == STEP_CONNECT_SLACK:
        if not msg and action is None:
            return OnboardingTurnResult(
                next_step=STEP_CONNECT_SLACK,
                answers_updates={},
                assistant_prompt_context={
                    **ctx_base,
                    "instruction": (
                        "Slack integration is coming soon. Ask the user to continue when ready to "
                        "connect GitHub and Linear."
                    ),
                },
            )
        return _slack_transition_result(answers)

    if current_step in (STEP_CONNECT_GITHUB, STEP_CONNECT_LINEAR):
        return OnboardingTurnResult(
            next_step=current_step,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "Encourage the user to use the in-app install buttons to connect OAuth. "
                    "Do not claim the connection is done until they finish in the browser."
                ),
                "connector": "github" if current_step == STEP_CONNECT_GITHUB else "linear",
            },
        )

    if current_step != STEP_CHAT_PROFILE:
        return OnboardingTurnResult(
            next_step=current_step,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": "Give a short helpful reply; step handling is unchanged.",
            },
        )

    phase = _default_profile_phase(answers)

    if phase == PROFILE_PHASE_DONE:
        return _slack_transition_result(answers)

    # Tools phase: only structured selection advances the FSM.
    if phase == PROFILE_PHASE_TOOLS:
        if action and action.get("type") == "tools_selected":
            raw_tools = action.get("tools")
            if not isinstance(raw_tools, dict):
                return OnboardingTurnResult(
                    next_step=STEP_CHAT_PROFILE,
                    answers_updates={},
                    assistant_prompt_context={
                        **ctx_base,
                        "profile_phase": PROFILE_PHASE_TOOLS,
                        "instruction": (
                            "Ask the user to pick their tools using the onboarding tool picker UI "
                            "(structured selection)."
                        ),
                    },
                )
            merged = _merge_tools_categories(answers, raw_tools)
            prior = _had_prior_tool_selection(answers)
            cq = _connect_queue_from_tools(merged)
            oauth_labels = _oauth_connector_labels_in_order(cq)
            instr = _tools_post_pick_instruction(prior=prior, oauth_labels=oauth_labels)
            updates = {
                "tools": merged,
                "profile_phase": PROFILE_PHASE_DONE,
            }
            return OnboardingTurnResult(
                next_step=STEP_CONNECT_SLACK,
                answers_updates=updates,
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_DONE,
                    "instruction": instr,
                    "tools": merged,
                    "tools_selection_revision": prior,
                    "connect_queue_next": cq,
                    "oauth_connector_labels_in_order": oauth_labels,
                },
            )
        return OnboardingTurnResult(
            next_step=STEP_CHAT_PROFILE,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "profile_phase": PROFILE_PHASE_TOOLS,
                "instruction": (
                    "Ask the user to select tools using the structured tool picker (not free text)."
                ),
            },
        )

    if not msg:
        return OnboardingTurnResult(
            next_step=STEP_CHAT_PROFILE,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "profile_phase": phase,
                "instruction": _instruction_for_phase(phase, answers),
            },
        )

    profile = answers.get("profile")
    if not isinstance(profile, dict):
        profile = {}
    company = answers.get("company")
    if not isinstance(company, dict):
        company = {}

    updates: dict[str, Any] = {}
    new_phase = phase

    if phase == PROFILE_PHASE_NAME:
        updates["profile"] = {**profile, "name": normalize_person_name(msg)}
        new_phase = _next_profile_phase(PROFILE_PHASE_NAME)
    elif phase == PROFILE_PHASE_ORG:
        updates["company"] = {**company, "name": normalize_company_name(msg)}
        new_phase = _next_profile_phase(PROFILE_PHASE_ORG)
    elif phase == PROFILE_PHASE_ROLE:
        updates["profile"] = {**profile, "role": normalize_role(msg)}
        new_phase = _next_profile_phase(PROFILE_PHASE_ROLE)
    elif phase == PROFILE_PHASE_WEBSITE:
        updates["company"] = {**company, "website": normalize_website(msg)}
        new_phase = _next_profile_phase(PROFILE_PHASE_WEBSITE)
    elif phase == PROFILE_PHASE_SIZE:
        key = normalize_company_size(msg)
        if key is None:
            return OnboardingTurnResult(
                next_step=STEP_CHAT_PROFILE,
                answers_updates={},
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_SIZE,
                    "instruction": (
                        "Ask again for an approximate headcount (a whole number is fine). "
                        "If they are vague, nudge them toward a ballpark number."
                    ),
                },
            )
        updates["company"] = {**company, "size": key}
        new_phase = _next_profile_phase(PROFILE_PHASE_SIZE)

    merged_updates: dict[str, Any] = {"profile_phase": new_phase}
    for k, v in updates.items():
        merged_updates[k] = v

    return OnboardingTurnResult(
        next_step=STEP_CHAT_PROFILE,
        answers_updates=merged_updates,
        assistant_prompt_context={
            **ctx_base,
            "profile_phase": new_phase,
            "instruction": _instruction_for_phase(new_phase, {**answers, **merged_updates}),
            "pending_user_message": msg,
        },
    )


def _instruction_for_phase(phase: str, answers: dict[str, Any]) -> str:
    if phase == PROFILE_PHASE_NAME:
        return (
            "Briefly introduce yourself as Vector (execution manager) in one short line so they "
            "know who is messaging them, then ask what they'd like you to call them."
        )
    if phase == PROFILE_PHASE_ORG:
        profile = answers.get("profile")
        first = ""
        if isinstance(profile, dict):
            raw = profile.get("name")
            if isinstance(raw, str) and raw.strip():
                first = _norm_str(raw)
        if first:
            return (
                f"You know their name is {first}. Open with a warm, varied one-liner (examples: "
                f"glad to meet them, or a short friendly line; do not default to "
                f"'Nice to meet you, {first}!' every time). One short sentence that this is a "
                f"quick setup for their workspace. Then ask for their organization or "
                f"company name. Do not start with "
                f"'Got it, {first}.'"
            )
        return (
            "Ask for their organization or company name in a natural DM tone. "
            "Do not open with 'Got it' plus a name."
        )
    if phase == PROFILE_PHASE_ROLE:
        return (
            "Ask what role best describes them at that company (e.g. Founder, Engineer, PM). "
            "Sound like a Slack DM: you may reference the company name naturally. "
            "Do not open with 'Got it, [first name].' or repeat that pattern if you used it before."
        )
    if phase == PROFILE_PHASE_WEBSITE:
        return (
            "Ask for the company website or domain in one natural sentence. "
            "Vary how you open; do not start with 'Got it, [first name].'"
        )
    if phase == PROFILE_PHASE_SIZE:
        return (
            "Ask approximately how many people work at the company (rough headcount is fine: "
            "a number like 12 or 86 is enough). Do not lead with a list of ranges like 1-5 / "
            "5-15 unless they ask how we bucket it. "
            "Keep the tone conversational; avoid opening with 'Got it, [first name].'"
        )
    if phase == PROFILE_PHASE_TOOLS:
        return (
            "Direct the user to the tool picker to select communication, engineering, PM, and docs "
            "tools."
        )
    if phase == PROFILE_PHASE_DONE:
        return "Profile is complete; transition messaging is handled elsewhere."
    return "Continue the onboarding conversation helpfully and concisely."
