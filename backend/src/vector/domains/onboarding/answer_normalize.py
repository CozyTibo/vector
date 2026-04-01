"""Normalize onboarding free-text answers (typos, casing, URLs) before persisting."""

from __future__ import annotations

import re
import string
from difflib import get_close_matches
from urllib.parse import urlparse

from vector.domains.onboarding.constants import (
    ALLOWED_COMPANY_SIZES,
    ONBOARDING_PROFILE_ROLE_CANONICAL,
    PROFILE_ROLE_OTHER,
)

# Phrase aliases (after boilerplate strip + token typo fixes).
_ROLE_ALIASES: dict[str, str] = {
    "foundr": "Founder",
    "foundre": "Founder",
    "foundor": "Founder",
    "founders": "Founder",
    "co-founder": "Co-founder",
    "cofounder": "Co-founder",
    "eng": "Engineer",
    "enginer": "Engineer",
    "enginneer": "Engineer",
    "engneer": "Engineer",
    "swe": "Software Engineer",
    "swes": "Software Engineer",
    "dev": "Engineer",
    "pm": "Product Manager",
    "product manger": "Product Manager",
    "product mngr": "Product Manager",
    "product manager": "Product Manager",
    "em": "Engineering Manager",
    "eng manager": "Engineering Manager",
    "engineering manager": "Engineering Manager",
    "designr": "Designer",
    "desginer": "Designer",
    "designer": "Designer",
    "cto": "CTO",
    "ceo": "CEO",
    "cfo": "CFO",
    "coo": "COO",
}

# Common token-level typos (letters dropped / swapped) before fuzzy match.
_ROLE_TOKEN_FIX: dict[str, str] = {
    "prodct": "product",
    "managr": "manager",
    "manger": "manager",
    "mngr": "manager",
    "enginer": "engineer",
    "enginneer": "engineer",
    "engneer": "engineer",
    "desginer": "designer",
    "designr": "designer",
    "foundr": "founder",
    "foundor": "founder",
}


def _norm_ws(value: str) -> str:
    return " ".join(value.split()).strip()


def _strip_role_boilerplate(s: str) -> str:
    """Remove leading 'I'm a …' style noise so 'I'm a PM' can match aliases."""
    t = s.strip()
    tl = t.lower()
    prefixes = (
        "i'm a ",
        "i'm an ",
        "i am a ",
        "i am an ",
        "im a ",
        "im an ",
        "i'm ",
        "i am ",
        "im ",
        "a ",
        "an ",
    )
    for p in prefixes:
        if tl.startswith(p):
            t = t[len(p) :].lstrip()
            tl = t.lower()
            break
    return _norm_ws(t)


def _fix_role_tokens(s: str) -> str:
    """Fix common misspellings per token, then rejoin (e.g. prodct managr -> product manager)."""
    parts = re.findall(r"[a-zA-Z']+", s.lower())
    if not parts:
        return s.lower()
    fixed = [_ROLE_TOKEN_FIX.get(p, p) for p in parts]
    return " ".join(fixed)


def normalize_person_name(raw: str) -> str:
    """Trim whitespace; title-case words (fixes 'tibo' -> 'Tibo')."""
    s = _norm_ws(raw)
    if not s:
        return s
    return string.capwords(s)


def normalize_company_name(raw: str) -> str:
    """Trim and sensible title casing for display (does not guess typos in brand names)."""
    s = _norm_ws(raw)
    if not s:
        return s
    return string.capwords(s)


def normalize_role(raw: str) -> str:
    """
    Map free-text role to a canonical onboarding label (see ONBOARDING_PROFILE_ROLE_CANONICAL)
    or PROFILE_ROLE_OTHER when we cannot classify confidently.
    """
    s = _norm_ws(raw)
    if not s:
        return PROFILE_ROLE_OTHER

    stripped = _strip_role_boilerplate(s)
    token_fixed = _fix_role_tokens(stripped)
    key = token_fixed.lower()

    if key in _ROLE_ALIASES:
        return _ROLE_ALIASES[key]

    lower_to_canon = {c.lower(): c for c in ONBOARDING_PROFILE_ROLE_CANONICAL}
    if key in lower_to_canon:
        return lower_to_canon[key]

    # Prefer fuzzy match on canonical labels (original + token-fixed string).
    for candidate in (stripped, token_fixed):
        if not candidate:
            continue
        m = get_close_matches(candidate, list(ONBOARDING_PROFILE_ROLE_CANONICAL), n=1, cutoff=0.82)
        if m:
            return m[0]
        m2 = get_close_matches(
            candidate.lower(),
            list(lower_to_canon.keys()),
            n=1,
            cutoff=0.82,
        )
        if m2:
            return lower_to_canon[m2[0]]

    m3 = get_close_matches(
        token_fixed,
        list(ONBOARDING_PROFILE_ROLE_CANONICAL),
        n=1,
        cutoff=0.72,
    )
    if m3:
        return m3[0]

    return PROFILE_ROLE_OTHER


def _headcount_to_bucket(n: int) -> str | None:
    """Map approximate headcount to stored size bucket."""
    if n <= 0:
        return None
    if n <= 5:
        return "1-5"
    if n <= 15:
        return "5-15"
    if n <= 50:
        return "15-50"
    return "50+"


def _parse_headcount_number(s: str) -> int | None:
    """
    Extract an integer headcount from free text (e.g. '86', 'about 120', '1,500').
    Returns None if the string looks like a bucket range label (e.g. '5-15') so synonyms apply.
    """
    t = s.strip()
    compact_no_ws = re.sub(r"\s+", "", t)
    if re.fullmatch(r"\d+[-–—]\d+", compact_no_ws):
        return None
    flat = re.sub(r",", "", t)
    compact = re.sub(r"\s+", "", flat)
    if compact.isdigit():
        return int(compact)
    nums = [int(x) for x in re.findall(r"\d+", flat)]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0]
    return max(nums)


_SIZE_SYNONYMS: dict[str, str] = {
    "1-5": "1-5",
    "1 to 5": "1-5",
    "1to5": "1-5",
    "5-15": "5-15",
    "5 to 15": "5-15",
    "5to15": "5-15",
    "15-50": "15-50",
    "15 to 50": "15-50",
    "15to50": "15-50",
    "50+": "50+",
    "50 +": "50+",
    "50plus": "50+",
    "50 plus": "50+",
    "50 or more": "50+",
}


def normalize_company_size(raw: str) -> str | None:
    """Map typos / phrasing to one of ALLOWED_COMPANY_SIZES, or None if unclear."""
    s = _norm_ws(raw)
    if not s:
        return None
    for ch in ("—", "–", "−"):
        s = s.replace(ch, "-")
    key_compact = re.sub(r"\s+", "", s.lower().replace("to", "-"))
    for syn, canonical in _SIZE_SYNONYMS.items():
        if re.sub(r"\s+", "", syn.lower().replace("to", "-")) == key_compact:
            return canonical
    if s in ALLOWED_COMPANY_SIZES:
        return s
    m = get_close_matches(s, list(ALLOWED_COMPANY_SIZES), n=1, cutoff=0.75)
    if m:
        return m[0]
    m2 = get_close_matches(s.lower(), [x.lower() for x in ALLOWED_COMPANY_SIZES], n=1, cutoff=0.75)
    if m2:
        for a in ALLOWED_COMPANY_SIZES:
            if a.lower() == m2[0]:
                return a
    n = _parse_headcount_number(s)
    if n is not None:
        return _headcount_to_bucket(n)
    return None


def normalize_website(raw: str) -> str:
    """Strip, add https if missing, lowercase host (fixes spacing / casing typos in URL)."""
    s = _norm_ws(raw)
    if not s:
        return s
    t = re.sub(r"\s+", "", s.strip().rstrip("/"))
    if not re.match(r"^https?://", t, re.I):
        t = "https://" + t
    parsed = urlparse(t)
    netloc = (parsed.netloc or "").lower()
    path = (parsed.path or "").rstrip("/")
    if not netloc:
        return s
    if not path:
        return f"https://{netloc}"
    return f"https://{netloc}{path}"
