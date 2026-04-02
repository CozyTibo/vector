"""Deterministic onboarding state machine (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vector.domains.onboarding.answer_normalize import (
    normalize_company_name,
    normalize_company_size,
    normalize_person_name,
    normalize_role,
)
from vector.domains.onboarding.connectors_privacy_kb import (
    CONNECTORS_PRIVACY_KNOWLEDGE_BASE,
)
from vector.domains.onboarding.constants import (
    PROFILE_PHASE_CONNECTORS_INTRO,
    PROFILE_PHASE_DONE,
    PROFILE_PHASE_NAME,
    PROFILE_PHASE_ORG,
    PROFILE_PHASE_ROLE,
    PROFILE_PHASE_SIZE,
    PROFILE_PHASE_TOOLS,
    PROFILE_PHASE_WEBSITE,
    PROFILE_PHASES_ORDER,
    STEP_CHAT_PROFILE,
    STEP_CONNECT_COMMUNICATION,
    STEP_CONNECT_GITHUB,
    STEP_CONNECT_LINEAR,
    STEP_SCANNING,
    STEP_THANK_YOU,
    TOOL_CATEGORY_KEYS,
)


@dataclass(frozen=True)
class OnboardingTurnResult:
    next_step: str
    answers_updates: dict[str, Any]
    assistant_prompt_context: dict[str, Any]


_CONNECTORS_INTRO_AFTER_SIZE_INSTRUCTION = (
    "They just gave company headcount (latest user message). The UI sends this as TWO chat "
    "bubbles (see format rules in your prompt tail).\n\n"
    "Voice: casual Slack DM from a teammate you like working with. Warm, a little human, not "
    "corporate and not a compliance readout. Do NOT open bubble 2 with stiff lines like "
    "\"don't worry\" or \"rest assured.\" Do not sound like you're defending a policy.\n\n"
    "Bubble 1 (one sentence only): acknowledge the number naturally.\n\n"
    "Bubble 2 MUST begin with ONE short bridge sentence that signals a topic shift from the "
    "headcount reply (e.g. okay, quick thing before we pick tools / now let's talk about how this "
    "works). Then a blank line, then the rest. Do NOT open bubble 2 by jumping straight into "
    "\"I need signals\" or \"I'm here to help by pulling\" with no transition.\n\n"
    "After the bridge: first person (I). Ease into why integrations help you help them: light "
    "signals from tools they already use, sensitive topic so keep it humble and plain language. "
    "Reassure without lecturing: not storing or reading sensitive stuff, lightweight activity "
    "metadata, no tool-by-tool essay.\n\n"
    "Then in the same bubble, after optional single blank line: chill close. Connecting is about "
    "a minute when they're ready, or they can ask you anything first. Mention the "
    "**I'm ready to choose tools** tag in the chat once.\n\n"
    "Hard rules: under 85 words across BOTH bubbles. No bullet lists. No em dash (U+2014). "
    "No hyphen jammed between two words as fake punctuation (e.g. worry-I)."
)

_CONNECTORS_INTRO_QA_INSTRUCTION = (
    "Connectors/privacy Q&A. Answer ONLY from the ground-truth KB in your system prompt. "
    "If not covered, say so and point to policies or their Vector contact for legal/DPA. "
    "Tone: same casual Slack-coworker energy as the rest of onboarding, not formal support. "
    "Two to four short sentences, under 100 words, airy spacing: use a blank line between two thoughts if "
    "it helps scan. No em dash (U+2014). Remind once they can use the **I'm ready to choose tools** "
    "tag to continue. At most one follow-up question."
)

_CONNECTORS_INTRO_IDLE_INSTRUCTION = (
    "Connectors/privacy step (idle refresh). Two or three short sentences max, optional blank "
    "line between ideas. Nudge: signals not sensitive dumps. **I'm ready to choose tools** tag when "
    "they want the picker."
)


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
    if isinstance(raw, str):
        if raw == PROFILE_PHASE_WEBSITE:
            return PROFILE_PHASE_SIZE
        if raw in PROFILE_PHASES_ORDER:
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
    """Order: communication (Slack, or Teams/Discord placeholder) → Linear → GitHub."""
    q: list[str] = []
    comm = tools.get("communication") or []
    pm = tools.get("pm") or []
    eng = tools.get("engineering") or []
    if "slack" in comm:
        q.append("slack")
    elif "ms_teams" in comm or "discord" in comm:
        q.append("comm_placeholder")
    if "linear" in pm:
        q.append("linear")
    if "github" in eng:
        q.append("github")
    return q


def _first_connect_step(connect_queue: list[str]) -> str:
    if not connect_queue:
        return STEP_SCANNING
    head = connect_queue[0]
    if head in ("slack", "comm_placeholder"):
        return STEP_CONNECT_COMMUNICATION
    if head == "linear":
        return STEP_CONNECT_LINEAR
    if head == "github":
        return STEP_CONNECT_GITHUB
    return STEP_SCANNING


def _oauth_connector_labels_in_order(connect_queue: list[str]) -> list[str]:
    mapping = {
        "slack": "Slack",
        "comm_placeholder": "Microsoft Teams or Discord",
        "linear": "Linear",
        "github": "GitHub",
    }
    return [mapping[x] for x in connect_queue if x in mapping]


def _tools_post_pick_instruction(*, prior: bool, oauth_labels: list[str]) -> str:
    """LLM instructions grounded in actual OAuth queue."""
    slack_line = (
        "Connectors run in order: communication tools first (Slack when selected), "
        "then project tools (Linear when selected), then engineering (GitHub when selected)."
    )
    if oauth_labels:
        only_oauth = (
            "Ground truth for OAuth installs: only these, in order: "
            + " → ".join(oauth_labels)
            + ". Do not name a tool unless it appears in that list."
        )
    else:
        only_oauth = (
            "Ground truth: no OAuth connectors are queued from their picks "
            "(or only tools we do not connect yet). Do not promise GitHub, Linear, or Slack OAuth."
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


def _communication_transition_result(answers: dict[str, Any]) -> OnboardingTurnResult:
    """Skip past communication step or jump to the next queued connector (legacy Confirm)."""
    tools = _merge_tools_categories(answers, {})
    cq = _connect_queue_from_tools(tools)
    ti = _tools_interest_flat(tools)
    base_updates: dict[str, Any] = {
        "connect_queue": cq,
        "connect_plan": list(cq),
        "tools_interest": ti,
    }
    ctx_base: dict[str, Any] = {"step": STEP_CONNECT_COMMUNICATION}
    if not cq:
        return OnboardingTurnResult(
            next_step=STEP_SCANNING,
            answers_updates=base_updates,
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "No supported OAuth connectors matched their picks. "
                    "They can connect integrations later from settings; offer to proceed."
                ),
            },
        )
    head = cq[0]
    if head not in ("slack", "comm_placeholder"):
        next_step = _first_connect_step(cq)
        labs = _oauth_connector_labels_in_order(cq)
        return OnboardingTurnResult(
            next_step=next_step,
            answers_updates=base_updates,
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "Guide them to use the in-app install buttons. Ground truth order: "
                    + " → ".join(labs)
                    + "."
                ),
                "connect_queue": cq,
                "oauth_connector_labels_in_order": labs,
            },
        )
    rest = cq[1:]
    updates = {**base_updates, "connect_queue": rest, "connect_plan": list(rest)}
    next_step = _first_connect_step(rest)
    rest_labs = _oauth_connector_labels_in_order(rest)
    return OnboardingTurnResult(
        next_step=next_step,
        answers_updates=updates,
        assistant_prompt_context={
            **ctx_base,
            "instruction": (
                "They continued past the first communication step. "
                + (
                    f"Still to connect: {' → '.join(rest_labs)}."
                    if rest_labs
                    else "Nothing further in the queue for OAuth."
                )
            ),
            "connect_queue": rest,
            "oauth_connector_labels_in_order": rest_labs,
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

    if current_step == STEP_CONNECT_COMMUNICATION:
        if not msg and action is None:
            tools_m = _merge_tools_categories(answers, {})
            cq_idle = _connect_queue_from_tools(tools_m)
            head_idle = cq_idle[0] if cq_idle else None
            ctx_comm: dict[str, Any] = {**ctx_base}
            if head_idle == "comm_placeholder":
                ctx_comm["instruction"] = (
                    "Microsoft Teams and Discord are not connectable yet. "
                    "Ask them to tap Continue to move on to the next integration."
                )
                ctx_comm["connector"] = "comm_placeholder"
            elif head_idle == "slack":
                ctx_comm["instruction"] = (
                    "Ask them to install the Vector Slack app using the in-app button, "
                    "then continue once the workspace is connected."
                )
            else:
                ctx_comm["instruction"] = (
                    "Guide them through the communication connector step using the in-app UI."
                )
            return OnboardingTurnResult(
                next_step=STEP_CONNECT_COMMUNICATION,
                answers_updates={},
                assistant_prompt_context=ctx_comm,
            )
        return _communication_transition_result(answers)

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
        return _communication_transition_result(answers)

    if phase == PROFILE_PHASE_CONNECTORS_INTRO:
        if action and action.get("type") == "connectors_intro_ready":
            return OnboardingTurnResult(
                next_step=STEP_CHAT_PROFILE,
                answers_updates={"profile_phase": PROFILE_PHASE_TOOLS},
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_TOOLS,
                    "instruction": (
                        "They confirmed they are ready to pick tools after the privacy/connectors "
                        "conversation. Briefly acknowledge with varied wording. Direct them to "
                        "the tool picker below (communication, engineering, PM, docs). No filler; "
                        "at most one short closing question or none."
                    ),
                },
            )
        if not msg:
            return OnboardingTurnResult(
                next_step=STEP_CHAT_PROFILE,
                answers_updates={},
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_CONNECTORS_INTRO,
                    "instruction": _CONNECTORS_INTRO_IDLE_INSTRUCTION,
                    "connectors_privacy_kb": CONNECTORS_PRIVACY_KNOWLEDGE_BASE,
                    "connectors_intro_kind": "idle",
                },
            )
        return OnboardingTurnResult(
            next_step=STEP_CHAT_PROFILE,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "profile_phase": PROFILE_PHASE_CONNECTORS_INTRO,
                "instruction": _CONNECTORS_INTRO_QA_INSTRUCTION,
                "connectors_privacy_kb": CONNECTORS_PRIVACY_KNOWLEDGE_BASE,
                "connectors_intro_kind": "qa",
            },
        )

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
                next_step=_first_connect_step(cq),
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

    merged_ans = {**answers, **merged_updates}
    if new_phase == PROFILE_PHASE_CONNECTORS_INTRO:
        instr = _CONNECTORS_INTRO_AFTER_SIZE_INSTRUCTION
        privacy_ctx: dict[str, Any] = {
            **ctx_base,
            "profile_phase": new_phase,
            "instruction": instr,
            "pending_user_message": msg,
            "connectors_privacy_kb": CONNECTORS_PRIVACY_KNOWLEDGE_BASE,
            "connectors_intro_kind": "after_size",
        }
    else:
        privacy_ctx = {
            **ctx_base,
            "profile_phase": new_phase,
            "instruction": _instruction_for_phase(new_phase, merged_ans),
            "pending_user_message": msg,
        }

    return OnboardingTurnResult(
        next_step=STEP_CHAT_PROFILE,
        answers_updates=merged_updates,
        assistant_prompt_context=privacy_ctx,
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
