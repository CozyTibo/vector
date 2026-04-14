"""Deterministic cleanup for manager-onboarding Slack copy (model output is not enough)."""

from __future__ import annotations

import re

# Doc-style hints the model should not emit; strip if it slips through.
_DOC_PAREN = re.compile(
    r"\(\s*(?:or\s+say\s+skip|or\s+type\s+skip|if\s+applicable|if\s+none|whenever\s+you\s*'?re\s+ready)\s*\)",
    re.IGNORECASE,
)

# Leading robotic acknowledgements (strip when a fuller sentence follows).
_ACK_PREFIXES = [
    r"(?is)^got it\b[.!:,;\s\u2014\u2013\-]*",
    r"(?is)^understood\b[.!:,;\s\u2014\u2013\-]*",
    r"(?is)^thanks for that\b[.!:,;\s\u2014\u2013\-]*",
    r"(?is)^thank you\b[.!:,;\s\u2014\u2013\-]*",
    r"(?is)^thanks\b[.!:,;\s\u2014\u2013\-]*",
    r"(?is)^makes sense\b[.!:,;\s\u2014\u2013\-]*",
]

_MIN_REST_LEN = 12


def normalize_manager_onboarding_outbound(text: str) -> str:
    """
    - Strip documentation-style parentheticals and stacked robotic openers (Got it, Thanks, …)
      when the rest of the message carries the real content.
    - Replace em dash (U+2014) and en dash (U+2013) with normal punctuation.
    """
    if not text or not isinstance(text, str):
        return text
    t = _DOC_PAREN.sub("", text)
    t = _strip_leading_ack_chains(t)
    t = t.replace("\u2014", ", ").replace("\u2013", " - ")
    t = re.sub(r",\s*,+", ", ", t)
    t = _collapse_horizontal_space_preserve_newlines(t)
    return t.strip()


def _collapse_horizontal_space_preserve_newlines(t: str) -> str:
    """Collapse runs of spaces/tabs per line; keep newlines so example lists stay readable."""
    lines = t.split("\n")
    collapsed = [re.sub(r"[ \t]{2,}", " ", line.strip()) for line in lines]
    out = "\n".join(collapsed)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _strip_leading_ack_chains(text: str) -> str:
    """Remove one or more leading stock acknowledgements when substantive content follows."""
    t = text.strip()
    for _ in range(6):
        changed = False
        for pat in _ACK_PREFIXES:
            m = re.match(pat, t)
            if not m:
                continue
            rest = t[m.end() :].lstrip()
            if len(rest) < _MIN_REST_LEN:
                break
            t = rest
            changed = True
            break
        if not changed:
            break
    return t
