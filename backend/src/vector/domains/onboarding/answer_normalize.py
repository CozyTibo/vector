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


def _infer_role_from_keywords(key: str) -> str | None:
    """
    Map common multi-word phrases and shorthands (key is lowercased, whitespace-normalized).
    More specific phrases first.
    """
    if not key:
        return None
    phrases: tuple[tuple[str, str], ...] = (
        ("machine learning engineer", "Machine Learning Engineer"),
        ("product marketing manager", "Product Marketing Manager"),
        ("engineering manager", "Engineering Manager"),
        ("program manager", "Program Manager"),
        ("project manager", "Project Manager"),
        ("product manager", "Product Manager"),
        ("technical lead", "Technical Lead"),
        ("tech lead", "Technical Lead"),
        ("team lead", "Team Lead"),
        ("head of engineering", "Head of Engineering"),
        ("head of product", "Head of Product"),
        ("head of design", "Head of Design"),
        ("data scientist", "Data Scientist"),
        ("machine learning", "Machine Learning Engineer"),
        ("customer success", "Customer Success"),
        ("account executive", "Account Executive"),
        ("sales manager", "Sales Manager"),
        ("software engineer", "Software Engineer"),
        ("senior engineer", "Senior Engineer"),
        ("staff engineer", "Staff Engineer"),
        ("principal engineer", "Principal Engineer"),
        ("product designer", "Product Designer"),
        ("ux designer", "UX Designer"),
        ("data analyst", "Data Analyst"),
        ("qa engineer", "QA Engineer"),
        ("security engineer", "Security Engineer"),
        ("data engineer", "Data Engineer"),
        ("founding engineer", "Founding Engineer"),
        ("vp engineering", "VP Engineering"),
        ("vp product", "VP Product"),
        ("vp sales", "VP Sales"),
        ("vp marketing", "VP Marketing"),
        ("people manager", "People"),
        ("hr manager", "HR"),
    )
    for phrase, label in phrases:
        if phrase in key:
            return label
    singles: dict[str, str] = {
        "manager": "Manager",
        "mgr": "Manager",
        "director": "Director",
        "pm": "Product Manager",
        "em": "Engineering Manager",
        "tl": "Technical Lead",
        "swe": "Software Engineer",
        "ds": "Data Scientist",
        "csm": "Customer Success",
        "ae": "Account Executive",
    }
    if key in singles:
        return singles[key]
    return None


def _ambiguous_head_of_free_text(key: str) -> bool:
    """True when user said 'head of …' but not one of our known Head of * roles (avoid fuzzy wrong bucket)."""
    if "head of" not in key:
        return False
    for sub in ("engineering", "product", "design"):
        if sub in key:
            return False
    return True


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
    "manager": "Manager",
    "managers": "Manager",
    "mgmt": "Manager",
    "director": "Director",
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


def _extract_company_name_core(raw: str) -> str:
    """Strip conversational wrappers so we persist the name, not the full sentence."""
    t = _norm_ws(raw)
    if not t:
        return t
    t = re.sub(
        r"^(?:sure|yes|yeah|yep|ok|okay|absolutely|definitely)[.!?,]?\s+",
        "",
        t,
        flags=re.I,
    )
    t = _norm_ws(t)
    # More specific patterns first (capture group = company name only).
    patterns: tuple[str, ...] = (
        r"^(?:it'?s|it is)\s+called\s+(.+)$",
        r"^(?:we'?re|we are)\s+called\s+(.+)$",
        r"^(?:the\s+)?(?:company|organization|organisation|org|firm)\s+is\s+called\s+(.+)$",
        r"^(?:the\s+)?(?:company|organization|organisation|org|firm)\s+name\s+is\s+(.+)$",
        r"^(?:company\s+)?name\s+is\s+(.+)$",
        r"^(?:the\s+)?(?:company|organization|organisation|org|firm)\s+is\s+(.+)$",
        r"^(?:we'?re|we are)\s+(.+)$",
        r"^(?:it'?s|it is)\s+(.+)$",
    )
    for pat in patterns:
        m = re.match(pat, t, re.I)
        if m:
            inner = _norm_ws(m.group(1)).rstrip(".,!?;:")
            if inner:
                return inner
    return t


def normalize_company_name(raw: str) -> str:
    """Trim conversational noise, then title-case for display."""
    core = _extract_company_name_core(raw)
    if not core:
        return core
    return string.capwords(core)


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

    inferred = _infer_role_from_keywords(key)
    if inferred:
        return inferred

    if _ambiguous_head_of_free_text(key):
        return PROFILE_ROLE_OTHER

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


def role_answer_looks_like_headcount_instead(raw: str) -> bool:
    """
    True when the reply is almost certainly a headcount or size bucket, not a job title
    (e.g. \"345\" or \"1,200\" on the role step).
    """
    s = _norm_ws(raw)
    if not s:
        return False
    if re.search(r"[a-zA-Z]", s):
        return False
    flat_digits = re.sub(r"[\s,]", "", s)
    if flat_digits.isdigit():
        return True
    return normalize_company_size(s) is not None


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


def _is_explicit_company_size_band_label(raw: str) -> bool:
    """True when the user picked a named band (e.g. 5-15, 50+), not a prose headcount."""
    s = _norm_ws(raw)
    if not s:
        return False
    t = s
    for ch in ("—", "–", "−"):
        t = t.replace(ch, "-")
    key_compact = re.sub(r"\s+", "", t.lower().replace("to", "-"))
    for syn in _SIZE_SYNONYMS:
        if re.sub(r"\s+", "", syn.lower().replace("to", "-")) == key_compact:
            return True
    return s in ALLOWED_COMPANY_SIZES


def company_size_persisted_value(raw: str) -> str | None:
    """
    Value stored in answers_json.company.size after validation.

    When the reply is a clear numeric headcount (or prose containing one), store that integer
    as a string (e.g. \"2345\"). When the user chose a named size band, store the band label.
    """
    s = _norm_ws(raw)
    if not s:
        return None
    bucket = normalize_company_size(raw)
    if bucket is None:
        return None
    if _is_explicit_company_size_band_label(raw):
        return bucket
    n = _parse_headcount_number(s)
    if n is not None:
        return str(n)
    return bucket


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
