"""Short deterministic outbound strings when the LLM is unavailable or onboarding completes."""

from __future__ import annotations

import re
from typing import Any


# Leading tokens we skip so "El Tibo" greets as "Tibo", not "El".
_INTRO_GREETING_LEADING_TOKENS = frozenset(
    {"el", "la", "los", "las", "le", "les", "da", "de", "del", "von", "van"},
)


def _sanitize_intro_greeting_name(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    tokens = [t.strip(".,!?\"'") for t in s.split() if t.strip()]
    if not tokens:
        return None
    pick = tokens[0]
    if len(tokens) >= 2 and pick.lower() in _INTRO_GREETING_LEADING_TOKENS:
        pick = tokens[1]
    first = pick.strip(".,!?\"'")
    if not first or not re.match(r"^[\w'.-]+$", first, re.UNICODE):
        return None
    return first[:32]


def _clip(s: str, max_len: int) -> str:
    t = s.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3].rstrip() + "..."


def intro_dm_text(*, context: dict[str, Any] | None = None) -> str:
    """
    First Slack DM: continuation from web onboarding when context exists.

    Context keys (from session ``context_json``, set by ``_ensure_intro_context_from_onboarding``):

    - ``intro_greeting_name``: display name from profile; first substantive token for "Hey {name}."
    - ``intro_company_name``: company name from onboarding
    - ``intro_role``: role string from profile (optional)
    - ``intro_web_handoff``: truthy when we have web onboarding data to reference
    """
    ctx = dict(context or {})
    name = _sanitize_intro_greeting_name(ctx.get("intro_greeting_name"))
    company = (ctx.get("intro_company_name") or "").strip()
    role = (ctx.get("intro_role") or "").strip()
    web = bool(ctx.get("intro_web_handoff"))

    if name:
        hey = f"Hey {name}."
    else:
        hey = "Hey."

    if web:
        line2 = "Continuing in Slack from what we already covered on the site."
        if company and role:
            line3 = (
                f"I'm Vector. From signup I have {_clip(company, 80)} on file, and your role as {_clip(role, 100)}. "
                "A few questions here will connect that to how your team actually works in Slack."
            )
        elif company:
            line3 = (
                f"I'm Vector. From signup I have {_clip(company, 100)} on file. "
                "A few questions here will connect that to how your team works in Slack."
            )
        elif role:
            line3 = (
                f"I'm Vector. From signup I have your role as {_clip(role, 120)}. "
                "A few questions here will connect that to how your team works in Slack."
            )
        else:
            line3 = (
                "I'm Vector. A few quick questions here will connect what we did on the site "
                "to how your team runs in Slack."
            )
    else:
        line2 = "Good to have you here in Slack."
        line3 = "I'm Vector. I'd like a quick sense of how your team works so I can be helpful."

    end = "Just answer however you normally would."
    return "\n\n".join([hey, line2, line3, end])


# Backward compatibility for imports/tests.
INTRO_DM_TEXT = intro_dm_text(context=None)

OUTBOUND_COMPLETION_TEXT = (
    "Perfect, that's enough for me to start. We can refine things later if needed."
)

FALLBACK_LLM_ERROR = (
    "I hit a snag processing that. Could you say it again in a quick line?"
)
