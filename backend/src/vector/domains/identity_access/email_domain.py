"""Email / domain parsing (pure)."""

from __future__ import annotations


def email_domain_from_address(email: str) -> str:
    """Return the domain part after @, lowercased."""
    parts = email.strip().lower().rsplit("@", maxsplit=1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = "invalid email"
        raise ValueError(msg)
    return parts[1]
