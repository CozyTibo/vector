"""Phase 04 Step 5 — governed promotion from candidate → authoritative link."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.link_ledger import append_authoritative_org_link
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_promotion_policy import CortexOrgLinkPromotionPolicy

AUTHORITATIVE_WRITER_SCHEMA_VERSION: Final[int] = 1
AUTHORITATIVE_WRITER_ENGINE_BUILD_REF: Final[str] = "phase04-step5-authoritative-writer-v1"


class PromotionInvariantError(ValueError):
    """Raised when promotion would violate **G-P04-CAND-01**."""


def create_promotion_policy(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    policy_ref: str,
    engine_build_ref: str | None = None,
) -> CortexOrgLinkPromotionPolicy:
    """Create an auditable promotion policy row (operator / fixture)."""
    pr = policy_ref.strip()
    if not pr:
        msg = "policy_ref required"
        raise ValueError(msg)
    row = CortexOrgLinkPromotionPolicy(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        policy_ref=pr,
        engine_build_ref=engine_build_ref or AUTHORITATIVE_WRITER_ENGINE_BUILD_REF,
    )
    db.add(row)
    db.flush()
    return row


def promote_candidate_to_authoritative_link(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    candidate_id: uuid.UUID,
    promotion_policy_id: uuid.UUID,
    confidence_class: str = "phase03_confidence_stub",
    metadata_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
) -> CortexOrgLink:
    """Promote one candidate row into ``cortex_org_links`` with mandatory policy id (**G-P04-CAND-01**)."""
    cand = db.get(CortexOrgLinkCandidate, candidate_id)
    if cand is None or cand.tenant_id != tenant_id:
        msg = "candidate_not_found"
        raise PromotionInvariantError(msg)
    pol = db.get(CortexOrgLinkPromotionPolicy, promotion_policy_id)
    if pol is None or pol.tenant_id != tenant_id:
        msg = "promotion_policy_not_found_for_tenant"
        raise PromotionInvariantError(msg)

    return append_authoritative_org_link(
        db,
        tenant_id=tenant_id,
        link_type=cand.link_type,
        source_entity_id=cand.source_entity_id,
        target_entity_id=cand.target_entity_id,
        evidence_raw_record_ids=list(cand.evidence_raw_record_ids or [])
        if isinstance(cand.evidence_raw_record_ids, list)
        else [],
        rule_id=cand.rule_id,
        confidence_class=confidence_class,
        metadata_json=metadata_json,
        engine_build_ref=engine_build_ref,
        promoted_from_candidate_id=cand.id,
        promotion_policy_id=pol.id,
    )
