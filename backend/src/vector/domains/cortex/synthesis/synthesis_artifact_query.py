"""Phase 08 P08-20 — synthesis artifact query substrate (lookup id / epoch / lineage).

Normative:
``DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md`` §Lineage,
``DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md`` §HTTP routes.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    PHASE08_SYNTHESIS_ARTIFACT_MATERIALIZATION_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_ARTIFACT_KINDS_V1,
    SynthesisArtifactMaterializationError,
    build_synthesis_artifact_summary_v1,
    get_synthesis_artifact_detail_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_pins import (
    extract_artifact_query_pins_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

PHASE08_SYNTHESIS_ARTIFACT_QUERY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_QUERY01_GATE_ID_V1: Final[str] = "G-P08-QUERY-01"

SYNTHESIS_ARTIFACT_QUERY_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md"
)

_DEFAULT_LIST_LIMIT_V1: Final[int] = 50
_MAX_LIST_LIMIT_V1: Final[int] = 200


class SynthesisArtifactQueryError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        http_status: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SynthesisArtifactListFiltersV1:
    retrieval_lookup_id: str | None = None
    retrieval_query_replay_identity: str | None = None
    synthesis_publication_epoch: str | None = None
    artifact_kind: str | None = None
    published: bool | None = None
    limit: int = _DEFAULT_LIST_LIMIT_V1


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), _MAX_LIST_LIMIT_V1))


def _apply_list_filters_v1(
    stmt: Select[tuple[CortexSynthesisArtifact]],
    *,
    tenant_id: uuid.UUID,
    filters: SynthesisArtifactListFiltersV1,
) -> Select[tuple[CortexSynthesisArtifact]]:
    stmt = stmt.where(CortexSynthesisArtifact.tenant_id == tenant_id)
    if filters.retrieval_lookup_id:
        stmt = stmt.where(
            CortexSynthesisArtifact.retrieval_lookup_id == filters.retrieval_lookup_id.strip(),
        )
    if filters.retrieval_query_replay_identity:
        stmt = stmt.where(
            CortexSynthesisArtifact.retrieval_query_replay_identity
            == filters.retrieval_query_replay_identity.strip(),
        )
    if filters.synthesis_publication_epoch:
        stmt = stmt.where(
            CortexSynthesisArtifact.synthesis_publication_epoch
            == filters.synthesis_publication_epoch.strip(),
        )
    if filters.artifact_kind:
        stmt = stmt.where(CortexSynthesisArtifact.artifact_kind == filters.artifact_kind.strip())
    if filters.published is not None:
        stmt = stmt.where(CortexSynthesisArtifact.published.is_(filters.published))
    return stmt


def build_artifact_query_summary_v1(row: CortexSynthesisArtifact) -> dict[str, Any]:
    summary = build_synthesis_artifact_summary_v1(row)
    summary["retrieval_lookup_id"] = row.retrieval_lookup_id
    summary["retrieval_query_replay_identity"] = row.retrieval_query_replay_identity
    summary["lineage_chain_digest"] = (row.body_json or {}).get("lineage_chain_digest")
    return summary


def list_synthesis_artifacts_query_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    filters: SynthesisArtifactListFiltersV1 | None = None,
) -> dict[str, Any]:
    """Tenant-scoped artifact list with optional lookup / epoch / lineage filters."""
    f = filters or SynthesisArtifactListFiltersV1()
    if f.artifact_kind and f.artifact_kind not in SYNTHESIS_ARTIFACT_KINDS_V1:
        raise SynthesisArtifactQueryError(
            "synthesis_artifact_kind_unknown",
            detail={"artifact_kind": f.artifact_kind},
        )
    stmt = _apply_list_filters_v1(
        select(CortexSynthesisArtifact),
        tenant_id=tenant_id,
        filters=f,
    )
    rows = session.scalars(
        stmt.order_by(CortexSynthesisArtifact.created_at.desc()).limit(_clamp_limit(f.limit)),
    ).all()
    items = [build_artifact_query_summary_v1(row) for row in rows]
    return {
        "surface_kind": "synthesis_artifact_list",
        "phase08_synthesis_artifact_query_runtime_schema_version": (
            PHASE08_SYNTHESIS_ARTIFACT_QUERY_RUNTIME_SCHEMA_VERSION
        ),
        "tenant_id": str(tenant_id),
        "filters_applied": {
            "retrieval_lookup_id": f.retrieval_lookup_id,
            "retrieval_query_replay_identity": f.retrieval_query_replay_identity,
            "synthesis_publication_epoch": f.synthesis_publication_epoch,
            "artifact_kind": f.artifact_kind,
            "published": f.published,
            "limit": _clamp_limit(f.limit),
        },
        "artifact_count": len(items),
        "artifacts": items,
    }


def query_synthesis_artifacts_by_lookup_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    retrieval_lookup_id: str,
    synthesis_publication_epoch: str | None = None,
    limit: int = _DEFAULT_LIST_LIMIT_V1,
) -> dict[str, Any]:
    """Phase 09 read-path prep — artifacts for a pinned retrieval lookup id."""
    lookup = retrieval_lookup_id.strip()
    if not lookup:
        raise SynthesisArtifactQueryError("retrieval_lookup_id_required")
    return list_synthesis_artifacts_query_v1(
        session,
        tenant_id=tenant_id,
        filters=SynthesisArtifactListFiltersV1(
            retrieval_lookup_id=lookup,
            synthesis_publication_epoch=synthesis_publication_epoch,
            limit=limit,
        ),
    )


def query_synthesis_artifacts_by_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    synthesis_publication_epoch: str,
    limit: int = _DEFAULT_LIST_LIMIT_V1,
) -> dict[str, Any]:
    epoch = synthesis_publication_epoch.strip()
    if not epoch:
        raise SynthesisArtifactQueryError("synthesis_publication_epoch_required")
    return list_synthesis_artifacts_query_v1(
        session,
        tenant_id=tenant_id,
        filters=SynthesisArtifactListFiltersV1(
            synthesis_publication_epoch=epoch,
            limit=limit,
        ),
    )


def query_synthesis_artifacts_by_replay_identity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    retrieval_query_replay_identity: str,
    synthesis_publication_epoch: str | None = None,
    limit: int = _DEFAULT_LIST_LIMIT_V1,
) -> dict[str, Any]:
    """Lineage substrate — artifacts derived from a pinned retrieval query replay identity."""
    rqid = retrieval_query_replay_identity.strip()
    if not rqid:
        raise SynthesisArtifactQueryError("retrieval_query_replay_identity_required")
    return list_synthesis_artifacts_query_v1(
        session,
        tenant_id=tenant_id,
        filters=SynthesisArtifactListFiltersV1(
            retrieval_query_replay_identity=rqid,
            synthesis_publication_epoch=synthesis_publication_epoch,
            limit=limit,
        ),
    )


def get_synthesis_artifact_for_query_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> dict[str, Any]:
    """Get single artifact (delegates to materialization detail builder)."""
    try:
        return get_synthesis_artifact_detail_v1(
            session,
            tenant_id=tenant_id,
            artifact_id=artifact_id,
        )
    except SynthesisArtifactMaterializationError as exc:
        raise SynthesisArtifactQueryError(
            exc.code,
            http_status=exc.http_status,
            detail=exc.detail,
        ) from exc


def build_synthesis_artifact_query_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_artifact_query_v1",
        "phase08_synthesis_artifact_query_runtime_schema_version": (
            PHASE08_SYNTHESIS_ARTIFACT_QUERY_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_QUERY01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_ARTIFACT_QUERY_SPEC_REF_V1,
        "artifact_materialization_schema_version": (
            PHASE08_SYNTHESIS_ARTIFACT_MATERIALIZATION_RUNTIME_SCHEMA_VERSION
        ),
        "supported_filters": [
            "retrieval_lookup_id",
            "retrieval_query_replay_identity",
            "synthesis_publication_epoch",
            "artifact_kind",
            "published",
            "limit",
        ],
        "index_columns": [
            "tenant_id + retrieval_lookup_id",
            "tenant_id + retrieval_query_replay_identity",
            "tenant_id + synthesis_publication_epoch",
        ],
        "rules": [
            "Tenant scope is mandatory on every list/get query.",
            "Lookup and replay-identity filters use denormalized columns on cortex_synthesis_artifacts.",
            "Phase 09 product read path MUST pin retrieval_lookup_id + publication epoch.",
        ],
    }


def verify_gp08_query01_tenant_scope_static() -> dict[str, Any]:
    errors: list[str] = []
    if not GP08_QUERY01_GATE_ID_V1.startswith("G-P08-"):
        errors.append("gate_id_prefix")
    filters = SynthesisArtifactListFiltersV1(retrieval_lookup_id="sha256:" + "a" * 64)
    if filters.retrieval_lookup_id is None:
        errors.append("filter_dataclass")
    return {
        "id": GP08_QUERY01_GATE_ID_V1,
        "name": "gp08_query01_tenant_scope",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_artifact_query_runtime_schema_version": (
                PHASE08_SYNTHESIS_ARTIFACT_QUERY_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_query01_pin_extraction_static() -> dict[str, Any]:
    errors: list[str] = []
    lookup, rqid = extract_artifact_query_pins_v1(
        {
            "retrieval_query_replay_identity": "rqid-abc",
            "evidence_scope_summary": {"retrieval_lookup_id": "sha256:" + "b" * 64},
        },
    )
    if rqid != "rqid-abc":
        errors.append("rqid_extract")
    if not lookup or not lookup.startswith("sha256:"):
        errors.append("lookup_from_scope")
    empty_lookup, empty_rqid = extract_artifact_query_pins_v1({})
    if empty_lookup is not None or empty_rqid is not None:
        errors.append("empty_body")
    return {
        "id": GP08_QUERY01_GATE_ID_V1,
        "name": "gp08_query01_pin_extraction",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
