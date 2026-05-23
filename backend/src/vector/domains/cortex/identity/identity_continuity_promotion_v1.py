"""Wave S2 — fair promotion scheduling across GitHub / Slack / Notion continuity rules."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.identity_continuity_candidates_v1 import (
    PROD_CONTINUITY_RULE_IDS,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    _promotable_candidate_filters_v1,
)
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate

IDENTITY_CONTINUITY_PROMOTION_SCHEMA_VERSION: Final[int] = 1


def _rule_schedule_rank(rule_id: str | None) -> tuple[int, str]:
    rid = (rule_id or "").strip()
    try:
        return (PROD_CONTINUITY_RULE_IDS.index(rid), rid)
    except ValueError:
        return (len(PROD_CONTINUITY_RULE_IDS), rid)


def count_promotable_link_candidates_by_rule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            CortexOrgLinkCandidate.rule_id,
            func.count().label("n"),
        )
        .where(CortexOrgLinkCandidate.tenant_id == tenant_id, *_promotable_candidate_filters_v1())
        .group_by(CortexOrgLinkCandidate.rule_id)
    ).all()
    out = [{"rule_id": str(r[0] or "(null)"), "promotable_count": int(r[1] or 0)} for r in rows]
    out.sort(key=lambda x: _rule_schedule_rank(x["rule_id"]))
    return out


def list_promotable_link_candidates_fair_by_rule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
) -> list[CortexOrgLinkCandidate]:
    """Round-robin promotable candidates across prod continuity rules (S2.1)."""
    lim = max(1, min(int(limit), 500))
    rule_ids = list(PROD_CONTINUITY_RULE_IDS)
    per_rule = max(1, lim // max(1, len(rule_ids)))
    picked: list[CortexOrgLinkCandidate] = []
    seen: set[uuid.UUID] = set()

    for rid in rule_ids:
        batch = list(
            session.scalars(
                select(CortexOrgLinkCandidate)
                .where(
                    CortexOrgLinkCandidate.tenant_id == tenant_id,
                    CortexOrgLinkCandidate.rule_id == rid,
                    *_promotable_candidate_filters_v1(),
                )
                .order_by(
                    CortexOrgLinkCandidate.created_at.asc(),
                    CortexOrgLinkCandidate.row_digest.asc(),
                )
                .limit(per_rule)
            ).all()
        )
        for cand in batch:
            if cand.id in seen:
                continue
            seen.add(cand.id)
            picked.append(cand)
            if len(picked) >= lim:
                return picked

    if len(picked) < lim:
        remainder = lim - len(picked)
        extra = list(
            session.scalars(
                select(CortexOrgLinkCandidate)
                .where(CortexOrgLinkCandidate.tenant_id == tenant_id, *_promotable_candidate_filters_v1())
                .order_by(
                    CortexOrgLinkCandidate.created_at.asc(),
                    CortexOrgLinkCandidate.row_digest.asc(),
                )
                .limit(remainder + len(seen))
            ).all()
        )
        for cand in extra:
            if cand.id in seen:
                continue
            seen.add(cand.id)
            picked.append(cand)
            if len(picked) >= lim:
                break
    picked.sort(key=lambda c: (_rule_schedule_rank(c.rule_id), c.created_at or "", str(c.row_digest or "")))
    return picked[:lim]
