"""S4.3 — minimal useful synthesis definition (Fizzer v1 / execution continuity brief)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_empty_claims_gate_v1 import (
    count_verifiable_claims_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

SYNTHESIS_USEFUL_ARTIFACT_SCHEMA_VERSION: Final[int] = 1
WAVE_S4_STEP_20: Final[str] = "wave_s4_synthesis_useful_artifact"
FIZZER_TENANT_ID_V1: Final[str] = "c08ef32b-f89a-40f6-9566-e19b5329436f"

# Product-facing v1 workload name (maps to continuity_assessment pipeline class).
FIZZER_V1_PRODUCT_WORKLOAD_V1: Final[str] = "execution_continuity_brief"
FIZZER_V1_PIPELINE_WORKLOAD_V1: Final[str] = "continuity_assessment"

SD_LAWFUL_EMPTY_NO_EXECUTION_INDEX_V1: Final[str] = "SD-LAWFUL-EMPTY-NO-EXECUTION-INDEX"

EXECUTION_INDEX_KINDS_V1: Final[frozenset[str]] = frozenset(
    {"materialization", "causal_chain", "walk", "causal_edge"}
)
EXECUTION_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "materialization",
        "causal_chain",
        "walk",
        "causal_edge",
        "tcre_chain",
        "execution_brief",
        "continuity_assessment",
        "execution_continuity_brief",
    }
)
USEFUL_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_brief",
        "island_brief",
        "execution_understanding",
        "execution_narrative",
        "operational_synthesis",
        "continuity_assessment",
        "execution_continuity_brief",
        "degradation_brief",
    }
)


def fizzer_v1_pipeline_workloads_v1() -> list[str]:
    """Single pipeline workload for v1 useful synthesis (S4.3)."""
    return [FIZZER_V1_PIPELINE_WORKLOAD_V1]


def _normalize_index_kind_v1(raw: str | None) -> str:
    kind = str(raw or "").strip().lower()
    if kind in {"tcre_chain", "causal_edge"}:
        return "causal_chain"
    return kind


def _claim_has_execution_evidence_ref_v1(claim: Mapping[str, Any]) -> bool:
    citations = claim.get("synthesis_citations") or claim.get("citations") or []
    if isinstance(citations, list):
        for cite in citations:
            if not isinstance(cite, Mapping):
                continue
            sak = _normalize_index_kind_v1(str(cite.get("source_artifact_kind") or ""))
            if sak in EXECUTION_ARTIFACT_KINDS_V1:
                return True
            prov = cite.get("provenance")
            if isinstance(prov, Mapping):
                pk = _normalize_index_kind_v1(str(prov.get("artifact_kind") or prov.get("index_kind") or ""))
                if pk in EXECUTION_INDEX_KINDS_V1:
                    return True
    refs = claim.get("evidence_refs") or claim.get("evidence_ref_ids") or []
    if isinstance(refs, list):
        for ref in refs:
            if not isinstance(ref, Mapping):
                continue
            rk = _normalize_index_kind_v1(
                str(ref.get("index_kind") or ref.get("artifact_kind") or ref.get("source_artifact_kind") or "")
            )
            if rk in EXECUTION_INDEX_KINDS_V1 | EXECUTION_ARTIFACT_KINDS_V1:
                return True
    return False


def count_useful_execution_claims_v1(body: Mapping[str, Any] | None) -> int:
    if not isinstance(body, Mapping):
        return 0
    claims = body.get("claims") or []
    if not isinstance(claims, list):
        return 0
    n = 0
    for row in claims:
        if not isinstance(row, Mapping):
            continue
        if count_verifiable_claims_v1({"claims": [row]}) < 1:
            continue
        if _claim_has_execution_evidence_ref_v1(row):
            n += 1
    return n


def artifact_is_useful_v1(
    *,
    body_json: Mapping[str, Any] | None,
    artifact_kind: str | None = None,
) -> bool:
    body = body_json if isinstance(body_json, Mapping) else {}
    kind = str(artifact_kind or body.get("artifact_kind") or "").strip()
    if kind not in USEFUL_ARTIFACT_KINDS_V1 and kind != FIZZER_V1_PRODUCT_WORKLOAD_V1:
        return False
    return count_useful_execution_claims_v1(body) >= 1


def count_execution_index_entries_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str | None = None,
) -> int:
    stmt = select(func.count()).select_from(CortexRetrievalIndexEntry).where(
        CortexRetrievalIndexEntry.tenant_id == tenant_id,
        CortexRetrievalIndexEntry.index_epoch == published_index_epoch,
        CortexRetrievalIndexEntry.index_kind.in_(sorted(EXECUTION_INDEX_KINDS_V1)),
    )
    if island_scope_id:
        from vector.domains.cortex.retrieval.retrieval_component_materialization import (
            P1_C_ISLAND_SCOPE_KEY_V1,
        )

        rows = session.scalars(
            select(CortexRetrievalIndexEntry).where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == published_index_epoch,
                CortexRetrievalIndexEntry.index_kind.in_(sorted(EXECUTION_INDEX_KINDS_V1)),
            )
        ).all()
        return sum(
            1
            for row in rows
            if str((row.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "") == island_scope_id
        )
    return int(session.scalar(stmt) or 0)


def is_lawful_empty_island_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str,
) -> bool:
    """Lawful empty only when island has zero execution-shaped retrieval index entries."""
    return count_execution_index_entries_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published_index_epoch,
        island_scope_id=island_scope_id,
    ) == 0


def audit_artifacts_usefulness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_ids: Sequence[uuid.UUID],
) -> dict[str, Any]:
    from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

    useful = 0
    rows_out: list[dict[str, Any]] = []
    for aid in artifact_ids:
        row = session.get(CortexSynthesisArtifact, aid)
        if row is None or row.tenant_id != tenant_id:
            continue
        body = dict(row.body_json or {})
        if artifact_is_useful_v1(body_json=body, artifact_kind=str(row.artifact_kind or "")):
            useful += 1
            rows_out.append(
                {
                    "artifact_id": str(row.id),
                    "artifact_kind": row.artifact_kind,
                    "useful_execution_claim_count": count_useful_execution_claims_v1(body),
                }
            )
    return {
        "useful_count": useful,
        "checked": len(artifact_ids),
        "useful_artifacts": rows_out[:16],
    }


def snapshot_published_useful_artifacts_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """Count published artifacts with ≥1 execution-grounded claim in lookback window."""
    if session is None:
        raise ValueError("session_required")
    since = datetime.now(tz=UTC) - timedelta(days=max(1, lookback_days))
    tid = str(tenant_id)
    rows = session.execute(
        text(
            """
            SELECT id, artifact_kind, body_json, created_at
            FROM cortex_synthesis_artifacts
            WHERE tenant_id = :tenant
              AND published IS TRUE
              AND created_at >= :since
            ORDER BY created_at DESC
            LIMIT 200
            """
        ),
        {"tenant": tid, "since": since},
    ).mappings().all()
    useful: list[dict[str, Any]] = []
    for row in rows:
        body = row["body_json"] if isinstance(row["body_json"], dict) else {}
        kind = str(row["artifact_kind"] or body.get("artifact_kind") or "")
        exec_claims = count_useful_execution_claims_v1(body)
        if exec_claims < 1:
            continue
        if kind not in USEFUL_ARTIFACT_KINDS_V1 and kind != FIZZER_V1_PRODUCT_WORKLOAD_V1:
            continue
        useful.append(
            {
                "artifact_id": str(row["id"]),
                "artifact_kind": kind,
                "useful_execution_claim_count": exec_claims,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        )
    primary = useful[0] if useful else None
    return {
        "schema_version": SYNTHESIS_USEFUL_ARTIFACT_SCHEMA_VERSION,
        "tenant_id": tid,
        "lookback_days": lookback_days,
        "product_workload": FIZZER_V1_PRODUCT_WORKLOAD_V1,
        "pipeline_workload": FIZZER_V1_PIPELINE_WORKLOAD_V1,
        "published_useful_count": len(useful),
        "primary_useful_artifact": primary,
        "useful_artifacts": useful[:10],
        "acceptance_met": len(useful) >= 1,
    }
