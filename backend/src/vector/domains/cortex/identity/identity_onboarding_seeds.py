"""Read-only onboarding continuity seeds (not authoritative identity merges)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.identity_primitive_projection import _norm_email
from vector.infrastructure.db.repositories.onboarding import get_onboarding_for_tenant


def _emails_from_slack_member_list(raw: Any) -> list[str]:
    if not isinstance(raw, dict):
        return []
    members = raw.get("members")
    if not isinstance(members, list):
        return []
    out: list[str] = []
    for item in members:
        if not isinstance(item, dict):
            continue
        for key in ("email", "work_email"):
            em = _norm_email(item.get(key))
            if em:
                out.append(em)
        uid = item.get("slack_user_id")
        if isinstance(uid, str) and uid.strip():
            out.append(f"slack:{uid.strip()}")
    return out


def load_onboarding_continuity_seeds_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Extract deterministic continuity hints from tenant onboarding answers (seed-only)."""
    row = get_onboarding_for_tenant(session, tenant_id)
    if row is None or not isinstance(row.answers_json, dict):
        return {
            "onboarding_present": False,
            "email_seeds": [],
            "slack_user_id_seeds": [],
            "seed_count": 0,
        }

    answers = dict(row.answers_json)
    emails: set[str] = set()
    slack_ids: set[str] = set()

    for key in ("slack_stakeholders", "slack_collaborators", "slack_team_members"):
        block = answers.get(key)
        if not isinstance(block, dict):
            continue
        for em in _emails_from_slack_member_list(block):
            if em.startswith("slack:"):
                slack_ids.add(em.split(":", 1)[1])
            else:
                emails.add(em)
        ids = block.get("slack_user_ids")
        if isinstance(ids, list):
            for uid in ids:
                if isinstance(uid, str) and uid.strip().startswith("U"):
                    slack_ids.add(uid.strip())

    domain_hint = answers.get("company_email_domain") or answers.get("email_domain")
    domain = str(domain_hint).strip().lower() if isinstance(domain_hint, str) else None

    return {
        "onboarding_present": True,
        "email_seeds": sorted(emails),
        "slack_user_id_seeds": sorted(slack_ids),
        "company_email_domain_hint": domain,
        "seed_count": len(emails) + len(slack_ids),
        "note": (
            "Seeds are continuity hints only; authoritative linkage still requires "
            "deterministic evidence on raw anchors."
        ),
    }
