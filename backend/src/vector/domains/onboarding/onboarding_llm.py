"""Thin OpenAI adapter — phrasing only; does not decide onboarding steps."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from vector.domains.onboarding.constants import (
    PROFILE_PHASE_NAME,
    PROFILE_PHASE_ORG,
    PROFILE_PHASES_ORDER,
    STEP_CHAT_PROFILE,
)
from vector.settings import Settings, get_settings

# Logged server-side; client may show richer static copy. No LLM on bootstrap (instant response).
BOOTSTRAP_OPENING_REPLY_TEXT = (
    "Hey! I'm Vector, your execution manager. "
    "I'll ask a few quick questions to set things up. "
    "What should I call you?"
)


def _effective_profile_phase(answers_json: dict[str, Any]) -> str:
    """Match `onboarding_flow._default_profile_phase` when `profile_phase` is unset."""
    raw = answers_json.get("profile_phase")
    if isinstance(raw, str) and raw in PROFILE_PHASES_ORDER:
        return raw
    return PROFILE_PHASE_NAME


def _is_bootstrap_opening_turn(
    last_user_message: str | None,
    answers_json: dict[str, Any],
    step: str,
) -> bool:
    """First chat POST with empty body: phrasing is fixed; OpenAI must not run (latency)."""
    if last_user_message is not None and str(last_user_message).strip():
        return False
    if step != STEP_CHAT_PROFILE:
        return False
    return _effective_profile_phase(answers_json) == PROFILE_PHASE_NAME


def extract_onboarding_known_facts(answers_json: dict[str, Any]) -> dict[str, Any]:
    """Flat facts already collected — LLM must not ask for these again."""
    profile = answers_json.get("profile")
    company = answers_json.get("company")
    out: dict[str, Any] = {
        "user_name": None,
        "role": None,
        "company_name": None,
        "website": None,
        "company_size": None,
    }
    if isinstance(profile, dict):
        n = profile.get("name")
        if isinstance(n, str) and n.strip():
            out["user_name"] = n.strip()
        r = profile.get("role")
        if isinstance(r, str) and r.strip():
            out["role"] = r.strip()
    if isinstance(company, dict):
        cn = company.get("name")
        if isinstance(cn, str) and cn.strip():
            out["company_name"] = cn.strip()
        w = company.get("website")
        if isinstance(w, str) and w.strip():
            out["website"] = w.strip()
        s = company.get("size")
        if isinstance(s, str) and s.strip():
            out["company_size"] = s.strip()
    return out


def _facts_summary_lines(facts: dict[str, Any]) -> list[str]:
    labels = {
        "user_name": "Name",
        "role": "Role",
        "company_name": "Company",
        "website": "Website",
        "company_size": "Company size",
    }
    lines: list[str] = []
    for key, label in labels.items():
        v = facts.get(key)
        if v is not None and str(v).strip():
            lines.append(f"- {label}: {v}")
    return lines


def _fallback_reply(
    step: str,
    answers_json: dict[str, Any],
    last_user_message: str | None,
    assistant_prompt_context: dict[str, Any],
) -> str:
    """When OpenAI is unavailable — short, in-character lines only."""
    instruction = assistant_prompt_context.get("instruction")
    facts = extract_onboarding_known_facts(answers_json)
    name = facts.get("user_name")
    phase_ctx = assistant_prompt_context.get("profile_phase")
    phase_ans = answers_json.get("profile_phase")
    phase = phase_ctx if isinstance(phase_ctx, str) else phase_ans

    if isinstance(instruction, str) and instruction.strip():
        base = instruction.strip()
        # Org phase right after name: speak to the user, not the instruction text.
        if (
            phase == PROFILE_PHASE_ORG
            and isinstance(name, str)
            and name.strip()
        ):
            n = str(name).strip()
            return (
                f"Nice to meet you, {n}! "
                "I'll ask a few quick questions so Vector fits how your team actually works. "
                "What's your organization or company called?"
            )
        # Do not prepend "Got it, {name}." (overused); instruction text is enough for dev fallback.
        return base
    phase = answers_json.get("profile_phase")
    return (
        f"Quick check-in: we're on {step}"
        + (f" ({phase})" if isinstance(phase, str) else "")
        + ". "
        + (last_user_message or "Say what works for you.")
    )


SYSTEM_PROMPT = """You are Vector.

Identity (never break character):
- Vector is an execution manager that works with engineering teams.
- You help leaders understand what is happening across their engineering execution signals \
(work in motion, not dashboards).
- You are a coworker in the conversation, not a generic chatbot.
- Never describe yourself as an AI, an artificial intelligence, a chatbot, a language model, \
or an "assistant helping with onboarding".
- Never say you are here to "guide onboarding" in a meta way. Stay in the product voice.

Tone:
- Concise, calm, professional, slightly friendly.
- No corporate filler, no hype, no exclamation spam.
- Sound like a capable teammate at work, not support copy.
- Write like a Slack DM with someone you work with: direct, natural, a little casual. You can \
start with "Yeah," "Makes sense," "Cool," or jump straight into the point. Nuance is good \
(e.g. "Not fully yet, but..." when it fits). Avoid sounding like a form or a script.
- Do NOT start every message the same way. In particular, do not habitually open with \
"Got it, [first name]." or "Got it." plus their name. If you acknowledge, vary it ("Sounds \
good," "Nice," a short clause, or no opener at all) and do not put their first name at the \
start of every reply. Using their name once in a while mid-reply is fine; repeating \
"Got it, Name" back-to-back reads robotic.
- Never use the em dash character (Unicode U+2014, looks like a long dash) in your replies. \
Use commas, periods, or " - " with spaces if you need a break. Em dashes read as generic AI copy.
- Emojis are optional: you may use one occasionally to feel warmer and more human (e.g. after \
good news or a light moment). Keep them sparse (often zero; rarely more than one per message), \
workplace-appropriate, and never replace substance with emoji walls or use them every line.

Output rules:
1. Reply in 1 to 3 short sentences unless the instruction explicitly needs a touch more \
(still stay tight). If the instruction asks for a warm bridge plus a process line plus a \
question (e.g. after learning their name), you may use up to 4 short sentences. Still no \
padding.
2. Ask at most ONE clear question in your reply (or none if the instruction is only \
acknowledgment / next step).
3. Use the known_facts JSON: never ask for information that is already present (non-null \
fields). Weave context in naturally; do not read the list back to them.
4. Brief acknowledgments are fine, but vary them. Do not lean on one template. Banned as a \
default crutch: starting consecutive questions with "Got it, [name]."
5. Banned phrases and patterns. Do not use these or close variants:
   - "Thanks for your message"
   - "Thank you for sharing"
   - "To continue"
   - "I'm an AI"
   - "I'm here to help you with onboarding" (meta)
   - "As an AI assistant"
6. When the instruction says the user changed tools again, do NOT chain the same opener as the \
last message (avoid habitually starting with "Noticed you", "Looks like you've", or "I see you've"). \
Rotate structure: sometimes no acknowledgment, sometimes a single word, sometimes a new angle.

You do NOT control onboarding steps. The product sends you an instruction describing what \
the next message must accomplish, including which OAuth products (if any) are actually in scope. \
Your job is only natural phrasing that matches Vector's voice and the instruction. Never name a \
connector (e.g. Linear, GitHub) unless the instruction or deterministic context says it applies."""


def generate_onboarding_reply(
    *,
    step: str,
    answers_json: dict[str, Any],
    last_user_message: str | None,
    assistant_prompt_context: dict[str, Any],
    settings: Settings | None = None,
) -> str:
    """Return assistant message text; never changes onboarding step."""
    if _is_bootstrap_opening_turn(last_user_message, answers_json, step):
        return BOOTSTRAP_OPENING_REPLY_TEXT

    cfg = settings or get_settings()
    if not cfg.openai_api_key.strip():
        return _fallback_reply(step, answers_json, last_user_message, assistant_prompt_context)

    facts = extract_onboarding_known_facts(answers_json)
    instruction = assistant_prompt_context.get("instruction")
    if not isinstance(instruction, str):
        instruction = ""

    profile_phase = answers_json.get("profile_phase")
    phase_s = profile_phase if isinstance(profile_phase, str) else ""

    facts_block = json.dumps(facts, ensure_ascii=False, indent=2)
    context_extra = {
        k: v
        for k, v in assistant_prompt_context.items()
        if k not in ("instruction",) and v is not None
    }
    context_json = json.dumps(context_extra, ensure_ascii=False, default=str)[:4000]

    facts_lines = _facts_summary_lines(facts)
    facts_human = (
        "\n".join(facts_lines) if facts_lines else "(none yet: nothing is locked in as known.)"
    )

    default_instr = "(Use a short natural line consistent with Vector.)"
    instr = instruction.strip() if instruction else default_instr
    last_msg = json.dumps(last_user_message, ensure_ascii=False)
    tail = (
        "Write Vector's next chat message only. No markdown headings. "
        "No bullet lists unless the instruction requires listing options (e.g. size buckets). "
        "One question at most. "
        "Sound like the reference: a smooth coworker DM, not a form. "
        "Do not open with 'Got it, [first name].' if you already used that pattern recently."
    )

    revision_extra = ""
    if assistant_prompt_context.get("tools_selection_revision"):
        revision_extra = """

## Anti-repeat (this turn)
The user changed tool picks again; your previous reply may have sounded similar.
- Use a different opener than "Noticed", "Looks like", or "I see you've".
- Prefer 1–2 short sentences. Do not restate the tool list.
- Do not end with the same generic priority question as before; change the question or use none.
"""

    user_content = f"""## Known context — do NOT ask again for any field that is non-null below
{facts_block}

Readable summary:
{facts_human}

## Onboarding state (for alignment only; you do not change steps)
- onboarding_step: {step}
- profile_phase: {phase_s or "(n/a)"}

## What this message must accomplish (from product logic — follow this)
{instr}
{revision_extra}
## Extra deterministic context (tools, connectors, etc.)
{context_json}

## User's latest message (may be empty on first turn)
{last_msg}

{tail}"""

    temp = 0.7 if assistant_prompt_context.get("tools_selection_revision") else 0.58

    client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.chat.completions.create(
        model=cfg.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=temp,
        max_tokens=220,
    )
    choice = resp.choices[0].message.content
    text = (choice or "").strip()
    if not text:
        return _fallback_reply(step, answers_json, last_user_message, assistant_prompt_context)
    return text
