"""Identity substrate truth laws — collapse detection and execution gating (no separate repair runtime)."""

from __future__ import annotations

import uuid
from typing import Any, Final, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.identity_continuity_candidates_v1 import PROD_CONTINUITY_RULE_IDS
from vector.domains.cortex.identity.org_entities import OrgEntityKind
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

IDENTITY_SUBSTRATE_HEALTH_SCHEMA_VERSION: Final[int] = 1

# Substrate expects org handles when canonical anchors exist at non-trivial volume.
MIN_ANCHORS_FOR_SUBSTRATE_EXPECTATION_V1: Final[int] = 50
MIN_ACTIVE_HUMAN_ACTORS_HEALTHY_V1: Final[int] = 1
# Cross-tool continuity requires multiple promotion rules in the authoritative graph.
MIN_AUTHORITATIVE_PROMOTION_RULES_DEGRADED_V1: Final[int] = 2
MIN_AUTHORITATIVE_PROMOTION_RULES_HEALTHY_V1: Final[int] = 3

IdentitySubstrateHealthStatusV1 = Literal["healthy", "degraded", "broken"]


def count_identity_anchors_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(CortexCanonicalIdentityAnchor).where(
                CortexCanonicalIdentityAnchor.tenant_id == tenant_id
            )
        )
        or 0
    )


def count_active_human_actors_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.entity_kind == OrgEntityKind.HUMAN_ACTOR.value,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
            )
        )
        or 0
    )


def count_distinct_authoritative_promotion_rules_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    rows = session.execute(
        select(CortexOrgLink.rule_id)
        .where(
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.link_authority == "authoritative",
            CortexOrgLink.revoked_at.is_(None),
            CortexOrgLink.rule_id.is_not(None),
        )
        .distinct()
    ).all()
    return len({str(r[0]).strip() for r in rows if r[0]})


def count_authoritative_links_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.revoked_at.is_(None),
            )
        )
        or 0
    )


def evaluate_identity_substrate_health_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Truthful identity substrate posture for convergence and phase receipts."""
    anchors = count_identity_anchors_v1(session, tenant_id=tenant_id)
    human_actors = count_active_human_actors_v1(session, tenant_id=tenant_id)
    promotion_rules = count_distinct_authoritative_promotion_rules_v1(session, tenant_id=tenant_id)
    auth_links = count_authoritative_links_v1(session, tenant_id=tenant_id)

    reasons: list[str] = []
    status: IdentitySubstrateHealthStatusV1 = "healthy"

    if anchors >= MIN_ANCHORS_FOR_SUBSTRATE_EXPECTATION_V1 and human_actors < MIN_ACTIVE_HUMAN_ACTORS_HEALTHY_V1:
        status = "broken"
        reasons.append("anchors_without_human_actors")
    elif (
        human_actors >= MIN_ACTIVE_HUMAN_ACTORS_HEALTHY_V1
        and anchors >= MIN_ANCHORS_FOR_SUBSTRATE_EXPECTATION_V1
        and promotion_rules < MIN_AUTHORITATIVE_PROMOTION_RULES_DEGRADED_V1
    ):
        status = "degraded"
        reasons.append("promotion_rule_diversity_below_minimum")
    elif (
        human_actors >= MIN_ACTIVE_HUMAN_ACTORS_HEALTHY_V1
        and promotion_rules < MIN_AUTHORITATIVE_PROMOTION_RULES_HEALTHY_V1
        and auth_links > 0
    ):
        status = "degraded"
        reasons.append("cross_tool_continuity_below_target")

    return {
        "schema_version": IDENTITY_SUBSTRATE_HEALTH_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "status": status,
        "reasons": reasons,
        "metrics": {
            "identity_anchors": anchors,
            "active_human_actors": human_actors,
            "authoritative_links": auth_links,
            "distinct_authoritative_promotion_rules": promotion_rules,
            "prod_continuity_rule_ids": list(PROD_CONTINUITY_RULE_IDS),
        },
        "thresholds": {
            "min_anchors_for_expectation": MIN_ANCHORS_FOR_SUBSTRATE_EXPECTATION_V1,
            "min_active_human_actors": MIN_ACTIVE_HUMAN_ACTORS_HEALTHY_V1,
            "min_promotion_rules_degraded": MIN_AUTHORITATIVE_PROMOTION_RULES_DEGRADED_V1,
            "min_promotion_rules_healthy": MIN_AUTHORITATIVE_PROMOTION_RULES_HEALTHY_V1,
        },
    }


def identity_substrate_repair_owed_v1(health: dict[str, Any]) -> bool:
    """True when phase 03 must keep repairing before downstream phases are meaningful."""
    return str(health.get("status") or "") in ("broken", "degraded")


def execution_downstream_blocked_by_identity_v1(health: dict[str, Any]) -> bool:
    """Retrieval/synthesis must not advance on collapsed identity substrate."""
    return str(health.get("status") or "") == "broken"


def phase_03_forbids_completed_empty_v1(health: dict[str, Any]) -> bool:
    """Never fake-green COMPLETED_EMPTY while substrate is broken or degraded."""
    return identity_substrate_repair_owed_v1(health)
