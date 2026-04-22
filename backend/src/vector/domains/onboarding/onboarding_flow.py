"""Deterministic onboarding state machine (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vector.domains.onboarding.answer_normalize import (
    company_size_persisted_value,
    normalize_company_name,
    normalize_person_name,
    normalize_role,
    role_answer_looks_like_headcount_instead,
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
    STEP_ADMIN_ACCESS,
    STEP_CHAT_PROFILE,
    STEP_CONNECT_COMMUNICATION,
    STEP_CONNECT_ENGINEERING,
    STEP_CONNECT_PROJECT_MANAGEMENT,
    STEP_SCANNING,
    STEP_SLACK_COLLABORATORS,
    STEP_SLACK_COLLABORATORS_CONFIRM,
    STEP_SLACK_TEAM_MEMBERS,
    STEP_SLACK_TEAM_MEMBERS_CONFIRM,
    STEP_SLACK_WATCH_CHANNELS,
    STEP_SLACK_WATCH_CHANNELS_CONFIRM,
    STEP_SLACK_STAKEHOLDERS,
    STEP_THANK_YOU,
    STEP_UNSUPPORTED_MANDATORY_TOOLS,
    TOOL_CATEGORY_KEYS,
)


@dataclass(frozen=True)
class OnboardingTurnResult:
    next_step: str
    answers_updates: dict[str, Any]
    assistant_prompt_context: dict[str, Any]


_CONNECTORS_INTRO_AFTER_SIZE_INSTRUCTION = (
    "They just gave organization-wide headcount (latest user message). The UI sends this as TWO chat "
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
    "Pre-tools Q&A: the user unlocked chat to ask questions. Use the product guide AND the "
    "connectors/privacy ground-truth KB in your system prompt. Do not contradict the KB on "
    "tool-specific data posture; use the guide for big-picture product and trust. "
    "If something is not covered, say so and point to policies or their Vector contact for legal/DPA. "
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


def _connect_queue_communication_only(tools: dict[str, list[str]]) -> list[str]:
    """When picks include unsupported mandatory categories, only Slack OAuth may remain (if selected)."""
    comm = tools.get("communication") or []
    if isinstance(comm, list) and "slack" in comm:
        return ["slack"]
    return []


def _connect_queue_full_from_tools(tools: dict[str, list[str]]) -> list[str]:
    """Onboarding OAuth queue: PM (Linear) → engineering (GitHub) → communication."""
    q: list[str] = []
    pm = tools.get("pm") or []
    if "linear" in pm:
        q.append("linear")
    eng = tools.get("engineering") or []
    if "github" in eng:
        q.append("github")
    comm = tools.get("communication") or []
    if "slack" in comm:
        q.append("slack")
    elif isinstance(comm, list) and ("ms_teams" in comm or "discord" in comm):
        q.append("comm_placeholder")
    return q


def _unsupported_mandatory_sections(tools: dict[str, list[str]]) -> list[str]:
    """Categories where the user's mandatory picks are not all supported in onboarding yet."""
    out: list[str] = []
    comm = tools.get("communication") or []
    if isinstance(comm, list) and len(comm) > 0 and "slack" not in comm:
        out.append("communication")
    pm = tools.get("pm") or []
    if isinstance(pm, list) and len(pm) > 0 and "linear" not in pm:
        out.append("pm")
    eng = tools.get("engineering") or []
    if isinstance(eng, list) and len(eng) > 0 and "github" not in eng:
        out.append("engineering")
    return out


def _unsupported_mandatory_labels_for_instruction(sections: list[str]) -> str:
    mapping = {
        "communication": "Communication (Microsoft Teams / Discord)",
        "pm": "Project management (outside Linear)",
        "engineering": "Engineering (outside GitHub)",
    }
    return ", ".join(mapping.get(s, s) for s in sections)


def _queue_skip_connected(
    queue: list[str],
    *,
    slack_connected: bool,
    linear_connected: bool,
    github_connected: bool,
) -> list[str]:
    """Drop connectors from the queue when already linked (e.g. after edit tools)."""
    out: list[str] = []
    for item in queue:
        if item == "slack" and slack_connected:
            continue
        if item == "linear" and linear_connected:
            continue
        if item == "github" and github_connected:
            continue
        out.append(item)
    return out


def _first_connect_step(connect_queue: list[str]) -> str:
    if not connect_queue:
        return STEP_SCANNING
    head = connect_queue[0]
    if head == "linear":
        return STEP_CONNECT_PROJECT_MANAGEMENT
    if head == "github":
        return STEP_CONNECT_ENGINEERING
    if head in ("slack", "comm_placeholder"):
        return STEP_CONNECT_COMMUNICATION
    return STEP_SCANNING


def _next_step_after_tool_connect_queue(
    connect_queue: list[str],
    tools: dict[str, list[str]],
) -> str:
    """When the OAuth queue is empty after tool selection, skip to the right post-connect step."""
    if connect_queue:
        return _first_connect_step(connect_queue)
    comm = tools.get("communication") or []
    if isinstance(comm, list) and "slack" in comm:
        return STEP_SLACK_STAKEHOLDERS
    return STEP_SCANNING


def _oauth_connector_labels_in_order(connect_queue: list[str]) -> list[str]:
    mapping = {
        "linear": "Linear",
        "github": "GitHub",
        "slack": "Slack",
        "comm_placeholder": "Microsoft Teams or Discord",
    }
    return [mapping[x] for x in connect_queue if x in mapping]


def _tools_post_pick_instruction(*, prior: bool, oauth_labels: list[str]) -> str:
    """LLM instructions grounded in actual OAuth queue."""
    slack_line = (
        "During onboarding we connect tools in the product in this order when they are selected: "
        "Linear (project management), then GitHub (engineering), then Slack for communication. "
        "Microsoft Teams or Discord as communication uses a short in-product placeholder until OAuth is available."
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
            "(or only tools we do not connect yet). Do not promise OAuth for tools outside that list."
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


_ALLOWED_CONNECT_QUEUE_ITEM = frozenset({"linear", "github", "slack", "comm_placeholder"})


def _coalesce_connect_queue(answers: dict[str, Any], tools: dict[str, list[str]]) -> list[str]:
    """Prefer persisted ``connect_queue`` (product PATCH / OAuth advances); else rebuild from tools."""
    raw = answers.get("connect_queue")
    if isinstance(raw, list) and raw:
        out = [str(x) for x in raw if isinstance(x, str) and x in _ALLOWED_CONNECT_QUEUE_ITEM]
        if out:
            return out
    return _connect_queue_full_from_tools(tools)


def _terminal_step_after_last_connector(head: str, tools: dict[str, list[str]]) -> str:
    """Next step after popping the final item from ``connect_queue``."""
    if head == "slack":
        comm = tools.get("communication") or []
        return STEP_SLACK_STAKEHOLDERS if isinstance(comm, list) and "slack" in comm else STEP_SCANNING
    if head == "comm_placeholder":
        return STEP_SCANNING
    comm = tools.get("communication") or []
    if isinstance(comm, list) and "slack" in comm:
        return STEP_CONNECT_COMMUNICATION
    if isinstance(comm, list) and ("ms_teams" in comm or "discord" in comm):
        return STEP_CONNECT_COMMUNICATION
    return STEP_SCANNING


def _user_ack_pop_connect_queue(
    answers: dict[str, Any],
    *,
    current_step_for_ctx: str,
) -> OnboardingTurnResult:
    """User sent chat on a connector step: pop the head of the persisted queue and advance."""
    tools = _merge_tools_categories(answers, {})
    ti = _tools_interest_flat(tools)
    cq = _coalesce_connect_queue(answers, tools)
    base_updates: dict[str, Any] = {"tools_interest": ti}
    ctx_base: dict[str, Any] = {"step": current_step_for_ctx}
    if not cq:
        next_step = _next_step_after_tool_connect_queue([], tools)
        return OnboardingTurnResult(
            next_step=next_step,
            answers_updates=base_updates,
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "Connector queue is empty. They may have finished linking; nudge them to use "
                    "the on-screen controls or finish setup."
                ),
            },
        )
    head = cq[0]
    rest = cq[1:]
    updates = {
        **base_updates,
        "connect_queue": rest,
        "connect_plan": list(rest),
    }
    if not rest:
        next_step = _terminal_step_after_last_connector(head, tools)
    else:
        next_step = _first_connect_step(rest)
    rest_labs = _oauth_connector_labels_in_order(rest)
    return OnboardingTurnResult(
        next_step=next_step,
        answers_updates=updates,
        assistant_prompt_context={
            **ctx_base,
            "instruction": (
                "They sent chat while on a connector step (continue / acknowledgement). "
                + (
                    f"Still to connect in product, in order: {' → '.join(rest_labs)}."
                    if rest_labs
                    else "Nothing further is queued for OAuth in onboarding."
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
    *,
    slack_connected: bool = False,
    linear_connected: bool = False,
    github_connected: bool = False,
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

    if current_step == STEP_UNSUPPORTED_MANDATORY_TOOLS:
        return OnboardingTurnResult(
            next_step=STEP_UNSUPPORTED_MANDATORY_TOOLS,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are on the unsupported mandatory tools screen after confirming picks. "
                    "The UI explains we will email when those tools are available and offers only "
                    "Edit tools. Reply in one short sentence if needed; do not repeat the card."
                ),
            },
        )

    if current_step == STEP_ADMIN_ACCESS:
        return OnboardingTurnResult(
            next_step=STEP_ADMIN_ACCESS,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are on the final website wrap-up: thanks + optional permission to introduce "
                    "Vector in Slack to other managers. They use on-screen buttons only; no further chat steps."
                ),
            },
        )

    if current_step == STEP_SLACK_TEAM_MEMBERS:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_TEAM_MEMBERS,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are picking Slack team members (excluding managers already chosen). "
                    "Nudge them to use the on-screen roster and Continue."
                ),
            },
        )

    if current_step == STEP_SLACK_TEAM_MEMBERS_CONFIRM:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_TEAM_MEMBERS_CONFIRM,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are confirming their Slack team list before choosing channels to watch. "
                    "Nudge them to use Edit or Continue in the product UI."
                ),
            },
        )

    if current_step == STEP_SLACK_WATCH_CHANNELS:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_WATCH_CHANNELS,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are picking Slack channels for Vector to watch. "
                    "Nudge them to use the channel list and Continue."
                ),
            },
        )

    if current_step == STEP_SLACK_WATCH_CHANNELS_CONFIRM:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_WATCH_CHANNELS_CONFIRM,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are confirming Slack channels to monitor. "
                    "Nudge them to use Edit or Continue in the product UI."
                ),
            },
        )

    if current_step == STEP_SLACK_COLLABORATORS:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_COLLABORATORS,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are picking Slack collaborators (other managers) in the onboarding UI. "
                    "If they chat here by mistake, nudge them to use the on-screen search and Continue."
                ),
            },
        )

    if current_step == STEP_SLACK_COLLABORATORS_CONFIRM:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_COLLABORATORS_CONFIRM,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "They are reviewing their Slack collaborator list before the final screen. "
                    "Nudge them to use Edit or Continue in the product UI."
                ),
            },
        )

    if current_step == STEP_SLACK_STAKEHOLDERS:
        return OnboardingTurnResult(
            next_step=STEP_SLACK_STAKEHOLDERS,
            answers_updates={},
            assistant_prompt_context={
                **ctx_base,
                "instruction": (
                    "Stakeholder picking is done in the onboarding UI (mentions with @). "
                    "If they sent chat here by mistake, nudge them to use Continue on screen."
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

    if current_step == STEP_CONNECT_PROJECT_MANAGEMENT:
        if not msg and action is None:
            tools_m = _merge_tools_categories(answers, {})
            cq_idle = _coalesce_connect_queue(answers, tools_m)
            head_idle = cq_idle[0] if cq_idle else None
            ctx_pm: dict[str, Any] = {**ctx_base}
            if head_idle == "linear":
                ctx_pm["instruction"] = (
                    "Ask them to connect Linear using the in-app OAuth button, then continue once "
                    "the workspace is linked."
                )
                ctx_pm["connector"] = "linear"
            else:
                ctx_pm["instruction"] = (
                    "Guide them through the project management connector step using the in-app UI."
                )
            return OnboardingTurnResult(
                next_step=STEP_CONNECT_PROJECT_MANAGEMENT,
                answers_updates={},
                assistant_prompt_context=ctx_pm,
            )
        return _user_ack_pop_connect_queue(answers, current_step_for_ctx=STEP_CONNECT_PROJECT_MANAGEMENT)

    if current_step == STEP_CONNECT_ENGINEERING:
        if not msg and action is None:
            tools_m = _merge_tools_categories(answers, {})
            cq_idle = _coalesce_connect_queue(answers, tools_m)
            head_idle = cq_idle[0] if cq_idle else None
            ctx_gh: dict[str, Any] = {**ctx_base}
            if head_idle == "github":
                ctx_gh["instruction"] = (
                    "Ask them to connect GitHub using the in-app OAuth button, then continue once "
                    "the workspace is linked."
                )
                ctx_gh["connector"] = "github"
            else:
                ctx_gh["instruction"] = (
                    "Guide them through the engineering connector step using the in-app UI."
                )
            return OnboardingTurnResult(
                next_step=STEP_CONNECT_ENGINEERING,
                answers_updates={},
                assistant_prompt_context=ctx_gh,
            )
        return _user_ack_pop_connect_queue(answers, current_step_for_ctx=STEP_CONNECT_ENGINEERING)

    if current_step == STEP_CONNECT_COMMUNICATION:
        if not msg and action is None:
            tools_m = _merge_tools_categories(answers, {})
            cq_idle = _coalesce_connect_queue(answers, tools_m)
            head_idle = cq_idle[0] if cq_idle else None
            ctx_comm: dict[str, Any] = {**ctx_base}
            if head_idle == "comm_placeholder":
                ctx_comm["instruction"] = (
                    "Microsoft Teams and Discord are not connectable yet. "
                    "Ask them to tap Finish setup when they are ready; they can add more tools from Connectors later."
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
        return _user_ack_pop_connect_queue(answers, current_step_for_ctx=STEP_CONNECT_COMMUNICATION)

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
        return _user_ack_pop_connect_queue(answers, current_step_for_ctx=STEP_CHAT_PROFILE)

    if phase == PROFILE_PHASE_CONNECTORS_INTRO:
        if action and action.get("type") == "connectors_intro_ready":
            return OnboardingTurnResult(
                next_step=STEP_CHAT_PROFILE,
                answers_updates={"profile_phase": PROFILE_PHASE_TOOLS},
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_TOOLS,
                    "instruction": (
                        "They confirmed they are ready after the privacy/connectors conversation. "
                        "Briefly acknowledge with varied wording. The point is to understand how you "
                        "can help them and their organization, not to 'shop' for integrations. Ask "
                        "them to use the tool picker below to list the tools their team actually "
                        "uses so Vector has context (one communication tool required; other rows are "
                        "optional). Do not sound like you are reciting product categories; frame it as "
                        "context about how work runs. At most one short closing question or none."
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
            comm_sel = merged.get("communication") or []
            if not isinstance(comm_sel, list) or len(comm_sel) == 0:
                return OnboardingTurnResult(
                    next_step=STEP_CHAT_PROFILE,
                    answers_updates={},
                    assistant_prompt_context={
                        **ctx_base,
                        "profile_phase": PROFILE_PHASE_TOOLS,
                        "instruction": (
                            "They confirmed tool selection without choosing a communication tool. "
                            "Ask them to pick one of Slack, Microsoft Teams, or Discord, then confirm again."
                        ),
                    },
                )
            pm_sel = merged.get("pm") or []
            if not isinstance(pm_sel, list) or len(pm_sel) == 0:
                return OnboardingTurnResult(
                    next_step=STEP_CHAT_PROFILE,
                    answers_updates={},
                    assistant_prompt_context={
                        **ctx_base,
                        "profile_phase": PROFILE_PHASE_TOOLS,
                        "instruction": (
                            "They confirmed without picking any project management tool "
                            "(Linear, Jira, ClickUp, or Notion). Ask them to pick at least one, then confirm again."
                        ),
                    },
                )
            eng_sel = merged.get("engineering") or []
            if not isinstance(eng_sel, list) or len(eng_sel) == 0:
                return OnboardingTurnResult(
                    next_step=STEP_CHAT_PROFILE,
                    answers_updates={},
                    assistant_prompt_context={
                        **ctx_base,
                        "profile_phase": PROFILE_PHASE_TOOLS,
                        "instruction": (
                            "They confirmed without picking any engineering tool "
                            "(GitHub, GitLab, or Bitbucket). Ask them to pick at least one, then confirm again."
                        ),
                    },
                )
            prior = _had_prior_tool_selection(answers)
            unsupported = _unsupported_mandatory_sections(merged)
            if unsupported:
                cq = _connect_queue_communication_only(merged)
            else:
                cq = _connect_queue_full_from_tools(merged)
            cq = _queue_skip_connected(
                cq,
                slack_connected=slack_connected,
                linear_connected=linear_connected,
                github_connected=github_connected,
            )
            oauth_labels = _oauth_connector_labels_in_order(cq)
            instr = _tools_post_pick_instruction(prior=prior, oauth_labels=oauth_labels)
            if unsupported:
                labels = _unsupported_mandatory_labels_for_instruction(unsupported)
                instr = (
                    "They confirmed tool picks where Vector does not yet support everything they need "
                    f"in mandatory categories ({labels}). "
                    "Acknowledge briefly without sounding alarmed. The product shows a card explaining "
                    "we will email when they can finish onboarding with those tools, with Edit tools only "
                    "to revise picks. Do not promise OAuth or live ingestion for unsupported picks. "
                    "Do not read their entire tool list."
                )
            ti = _tools_interest_flat(merged)
            updates = {
                "tools": merged,
                "profile_phase": PROFILE_PHASE_DONE,
                "connect_queue": cq,
                "connect_plan": list(cq),
                "tools_interest": ti,
                "unsupported_mandatory_sections": unsupported,
            }
            next_step = (
                STEP_UNSUPPORTED_MANDATORY_TOOLS
                if unsupported
                else _next_step_after_tool_connect_queue(cq, merged)
            )
            return OnboardingTurnResult(
                next_step=next_step,
                answers_updates=updates,
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_DONE,
                    "instruction": instr,
                    "tools": merged,
                    "tools_selection_revision": prior,
                    "connect_queue_next": cq,
                    "oauth_connector_labels_in_order": oauth_labels,
                    "unsupported_mandatory_sections": unsupported,
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
        if role_answer_looks_like_headcount_instead(msg):
            return OnboardingTurnResult(
                next_step=STEP_CHAT_PROFILE,
                answers_updates={},
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_ROLE,
                    "instruction": (
                        "They sent something that looks like a headcount, but you asked for their job role. "
                        "Briefly clarify you need a professional title (Founder, Engineer, PM, Ops…), "
                        "not org or team size. Re-ask warmly in one or two short sentences."
                    ),
                },
            )
        updates["profile"] = {**profile, "role": normalize_role(msg)}
        new_phase = _next_profile_phase(PROFILE_PHASE_ROLE)
    elif phase == PROFILE_PHASE_SIZE:
        stored_size = company_size_persisted_value(msg)
        if stored_size is None:
            return OnboardingTurnResult(
                next_step=STEP_CHAT_PROFILE,
                answers_updates={},
                assistant_prompt_context={
                    **ctx_base,
                    "profile_phase": PROFILE_PHASE_SIZE,
                    "instruction": (
                        "Ask again for an approximate headcount for the whole company or organization, "
                        "not just their team or direct reports. A whole number or ballpark is fine."
                    ),
                },
            )
        updates["company"] = {**company, "size": stored_size}
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
        company = answers.get("company")
        org_name = ""
        if isinstance(company, dict):
            raw_name = company.get("name")
            if isinstance(raw_name, str) and raw_name.strip():
                org_name = _norm_str(raw_name)
        org_clause = (
            f" You may name the org ({org_name}) so it is obvious you mean everyone there, "
            f"not only the group they manage."
            if org_name
            else (
                " Name the company if you already know it so it is obvious you mean the whole "
                "organization, not only the group they manage."
            )
        )
        return (
            "Ask how many people work at the company or organization in total (rough headcount is "
            "fine: one number like 12 or 86 is enough)."
            + org_clause
            + " Be explicit that you want company-wide or org-wide scale, not their team, squad, "
            "department headcount, or number of direct reports (managers often answer with "
            "team size unless you steer them). "
            "Do not lead with a list of ranges like 1-5 / 5-15 unless they ask how we bucket it. "
            "Keep the tone conversational; avoid opening with 'Got it, [first name].'"
        )
    if phase == PROFILE_PHASE_TOOLS:
        return (
            "The user is on the tool picker step. If they seem lost, nudge them to list the tools "
            "their organization actually uses so you can understand how to help, not to pick "
            "products from a catalog. They must pick at least one communication tool, one project "
            "management tool, and one engineering tool before confirming; video calls, calendars, "
            "and documentation tools are optional."
        )
    if phase == PROFILE_PHASE_DONE:
        return "Profile is complete; transition messaging is handled elsewhere."
    return "Continue the onboarding conversation helpfully and concisely."
