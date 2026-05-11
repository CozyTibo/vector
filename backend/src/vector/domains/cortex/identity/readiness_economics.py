"""Phase 04 Step 21 — identity readiness economics probes (P04-21).

Normative: ``phase-04-readiness-audit.md`` (thresholds + cost hints).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.org_ambiguity import count_open_org_ambiguity_records
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance

IDENTITY_READINESS_ECONOMICS_SCHEMA_VERSION: Final[int] = 1
IDENTITY_READINESS_ECONOMICS_CONTRACT: Final[str] = "identity_readiness_economics_v1"

_BYTES_PER_ORG_ENTITY: Final[int] = 480
_BYTES_PER_ORG_LINK: Final[int] = 320
_BYTES_PER_CANDIDATE: Final[int] = 220

_WARN_ORG_ENTITIES: Final[int] = 10_000
_CRIT_ORG_ENTITIES: Final[int] = 50_000
_WARN_CANDIDATES: Final[int] = 100_000
_CRIT_CANDIDATES: Final[int] = 500_000
_WARN_AUTH_LINKS: Final[int] = 25_000
_CRIT_AUTH_LINKS: Final[int] = 150_000
_WARN_OPEN_AMBIG: Final[int] = 500
_CRIT_OPEN_AMBIG: Final[int] = 5_000
_WARN_PENDING_MERGES: Final[int] = 200
_CRIT_PENDING_MERGES: Final[int] = 2_000
_WARN_PRIMITIVES: Final[int] = 50_000
_CRIT_PRIMITIVES: Final[int] = 250_000
_WARN_REPLAY_JOBS: Final[int] = 5_000
_CRIT_REPLAY_JOBS: Final[int] = 50_000


def _authoritative_valid_now_clause(*, now: datetime) -> Any:
    return and_(
        CortexOrgLink.link_authority == "authoritative",
        CortexOrgLink.revoked_at.is_(None),
        or_(CortexOrgLink.valid_from.is_(None), CortexOrgLink.valid_from <= now),
        or_(CortexOrgLink.valid_to.is_(None), CortexOrgLink.valid_to > now),
    )


def _count_pending_merge_proposals(session: Session, *, tenant_id: uuid.UUID, scan_limit: int = 2_000) -> int:
    lim = max(1, min(scan_limit, 10_000))
    rows = list(
        session.scalars(
            select(CortexOrgMerge)
            .where(CortexOrgMerge.tenant_id == tenant_id)
            .order_by(CortexOrgMerge.created_at.desc())
            .limit(lim)
        ).all()
    )
    n = 0
    for r in rows:
        meta = dict(r.metadata_json or {})
        if meta.get("merge_queue_status") == "pending" or meta.get("proposal_status") == "pending":
            n += 1
    return n


def _replay_status_histogram(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    rows = session.execute(
        select(CortexOrgLinkReplayJob.status, func.count())
        .where(CortexOrgLinkReplayJob.tenant_id == tenant_id)
        .group_by(CortexOrgLinkReplayJob.status)
    ).all()
    return {str(st): int(c) for st, c in rows}


def build_identity_readiness_economics(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Bounded per-tenant economics snapshot (**identity_readiness_economics_v1**)."""
    now = datetime.now(tz=UTC)
    computed_iso = now.isoformat()

    org_entities_active = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
            )
        )
        or 0
    )

    org_links_authoritative_valid_now = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(CortexOrgLink.tenant_id == tenant_id, _authoritative_valid_now_clause(now=now))
        )
        or 0
    )

    org_link_candidates = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate).where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        )
        or 0
    )

    org_link_candidate_batches = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidateBatch)
            .where(CortexOrgLinkCandidateBatch.tenant_id == tenant_id)
        )
        or 0
    )

    open_org_ambiguities = count_open_org_ambiguity_records(session, tenant_id=tenant_id)
    pending_merge_proposals = _count_pending_merge_proposals(session, tenant_id=tenant_id)

    org_primitive_instances = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgPrimitiveInstance).where(CortexOrgPrimitiveInstance.tenant_id == tenant_id)
        )
        or 0
    )

    org_link_replay_jobs_by_status = _replay_status_histogram(session, tenant_id=tenant_id)
    org_link_replay_jobs_total = int(sum(org_link_replay_jobs_by_status.values()))

    storage_estimate_bytes = (
        org_entities_active * _BYTES_PER_ORG_ENTITY
        + org_link_candidates * _BYTES_PER_CANDIDATE
        + org_links_authoritative_valid_now * _BYTES_PER_ORG_LINK
    )

    candidate_regen_relative_units = org_link_candidates + org_link_candidate_batches * 50
    authoritative_replay_relative_units = org_links_authoritative_valid_now * 2

    thresholds = {
        "org_entities_active": {"warn": _WARN_ORG_ENTITIES, "critical": _CRIT_ORG_ENTITIES},
        "org_link_candidates": {"warn": _WARN_CANDIDATES, "critical": _CRIT_CANDIDATES},
        "org_links_authoritative_valid_now": {"warn": _WARN_AUTH_LINKS, "critical": _CRIT_AUTH_LINKS},
        "open_org_ambiguities": {"warn": _WARN_OPEN_AMBIG, "critical": _CRIT_OPEN_AMBIG},
        "pending_merge_proposals": {"warn": _WARN_PENDING_MERGES, "critical": _CRIT_PENDING_MERGES},
        "org_primitive_instances": {"warn": _WARN_PRIMITIVES, "critical": _CRIT_PRIMITIVES},
        "org_link_replay_jobs_total": {"warn": _WARN_REPLAY_JOBS, "critical": _CRIT_REPLAY_JOBS},
    }

    counts: dict[str, Any] = {
        "org_entities_active": org_entities_active,
        "org_links_authoritative_valid_now": org_links_authoritative_valid_now,
        "org_link_candidates": org_link_candidates,
        "org_link_candidate_batches": org_link_candidate_batches,
        "open_org_ambiguities": open_org_ambiguities,
        "pending_merge_proposals": pending_merge_proposals,
        "org_primitive_instances": org_primitive_instances,
        "org_link_replay_jobs_total": org_link_replay_jobs_total,
        "org_link_replay_jobs_by_status": dict(sorted(org_link_replay_jobs_by_status.items())),
    }

    warnings: list[dict[str, Any]] = []

    def _check(key: str, value: int, *, w: int, c: int) -> None:
        if value >= c:
            warnings.append(
                {
                    "level": "critical",
                    "code": f"{key}_critical",
                    "message": f"{key}={value} exceeds critical threshold {c}",
                    "metric": key,
                    "value": value,
                }
            )
        elif value >= w:
            warnings.append(
                {
                    "level": "warn",
                    "code": f"{key}_warn",
                    "message": f"{key}={value} exceeds warn threshold {w}",
                    "metric": key,
                    "value": value,
                }
            )

    _check("org_entities_active", org_entities_active, w=_WARN_ORG_ENTITIES, c=_CRIT_ORG_ENTITIES)
    _check("org_link_candidates", org_link_candidates, w=_WARN_CANDIDATES, c=_CRIT_CANDIDATES)
    _check(
        "org_links_authoritative_valid_now",
        org_links_authoritative_valid_now,
        w=_WARN_AUTH_LINKS,
        c=_CRIT_AUTH_LINKS,
    )
    _check("open_org_ambiguities", open_org_ambiguities, w=_WARN_OPEN_AMBIG, c=_CRIT_OPEN_AMBIG)
    _check(
        "pending_merge_proposals",
        pending_merge_proposals,
        w=_WARN_PENDING_MERGES,
        c=_CRIT_PENDING_MERGES,
    )
    _check(
        "org_primitive_instances",
        org_primitive_instances,
        w=_WARN_PRIMITIVES,
        c=_CRIT_PRIMITIVES,
    )
    _check(
        "org_link_replay_jobs_total",
        org_link_replay_jobs_total,
        w=_WARN_REPLAY_JOBS,
        c=_CRIT_REPLAY_JOBS,
    )

    has_critical = any(w["level"] == "critical" for w in warnings)
    has_warn = any(w["level"] == "warn" for w in warnings)
    if has_critical:
        overall_posture = "critical"
    elif has_warn:
        overall_posture = "warn"
    else:
        overall_posture = "ok"

    return {
        "identity_readiness_economics_schema_version": IDENTITY_READINESS_ECONOMICS_SCHEMA_VERSION,
        "schema_version": IDENTITY_READINESS_ECONOMICS_CONTRACT,
        "tenant_id": str(tenant_id),
        "computed_at": computed_iso,
        "counts": counts,
        "thresholds": thresholds,
        "storage_estimate_bytes": storage_estimate_bytes,
        "storage_row_byte_assumptions": {
            "org_entity": _BYTES_PER_ORG_ENTITY,
            "org_link_authoritative": _BYTES_PER_ORG_LINK,
            "org_link_candidate": _BYTES_PER_CANDIDATE,
        },
        "regen_replay_cost_hints": {
            "candidate_regen_relative_units": candidate_regen_relative_units,
            "authoritative_replay_relative_units": authoritative_replay_relative_units,
        },
        "warnings": warnings,
        "overall_posture": overall_posture,
    }


def verify_gp04_eco01_identity_readiness_economics(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-ECO-01 — economics / explosion posture (warn_only; critical marks passed=false)."""
    eco = build_identity_readiness_economics(session, tenant_id=tenant_id)
    posture = str(eco.get("overall_posture") or "ok")
    critical = posture == "critical"
    return {
        "id": "G-P04-ECO-01",
        "name": "identity_readiness_economics_budgets",
        "passed": not critical,
        "severity": "warn_only",
        "detail": {
            "tenant_id": str(tenant_id),
            "overall_posture": posture,
            "counts": eco.get("counts"),
            "storage_estimate_bytes": eco.get("storage_estimate_bytes"),
            "warnings": eco.get("warnings"),
        },
    }
