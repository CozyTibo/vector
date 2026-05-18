"""Phase 08 P08-14 — ``SynthesisIntelligenceArtifactV1`` materialization (**G-P08-SCHEMA-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-data-contracts.md`` §Artifacts.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.anti_goals import (
    validate_synthesis_authoritative_artifact_algebra_v1,
)
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    assert_synthesis_artifact_under_byte_cap_v1,
    synthesis_policy_pack_caps_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    SYNTHESIS_WORKLOAD_CLASS_METADATA_V1,
    normalize_synthesis_workload_class_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SYNTHESIS_LEGALITY_AUTHORITATIVE_USABLE_V1,
)
from vector.domains.cortex.synthesis.synthesis_bindings import (
    SynthesisBindingsError,
    build_synthesis_binding_bundle_v1,
    build_synthesis_binding_panel_v1,
    enforce_synthesis_binding_copy_law_v1,
)
from vector.domains.cortex.synthesis.synthesis_degradation import (
    apply_synthesis_degradation_to_artifact_v1,
)
from vector.domains.cortex.synthesis.synthesis_lineage import (
    SynthesisLineageError,
    apply_synthesis_lineage_to_artifact_v1,
    build_synthesis_lineage_panel_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    build_retrieval_receipt_embed_v1,
    primary_retrieval_query_replay_identity_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE08_SYNTHESIS_ARTIFACT_MATERIALIZATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_ART01_GATE_ID_V1: Final[str] = "G-P08-ART-01"

SYNTHESIS_ARTIFACT_MATERIALIZATION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-data-contracts.md"
)

SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_VERSION_V1: Final[int] = 1

SYNTHESIS_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_understanding",
        "operational_synthesis",
        "execution_narrative",
        "management_intelligence",
        "continuity_assessment",
        "degradation_brief",
    },
)

_SYNTHESIS_PUBLISH_BARRIER_LEGALITY_V1: Final[frozenset[str]] = frozenset(
    {"synthesis_replay_safe", "synthesis_degraded"},
)

_ARTIFACT_REQUIRED_TOP_LEVEL_V1: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "artifact_id",
        "artifact_kind",
        "artifact_digest",
        "synthesis_legality_class",
        "synthesis_job_replay_identity",
        "retrieval_query_replay_identity",
        "synthesis_policy_pack_digest",
        "synthesis_publication_epoch",
        "evidence_scope_summary",
        "claims",
        "synthesis_citation_envelope",
        "synthesis_omission_rows",
        "synthesis_degradation_rollup",
        "synthesis_legality_posture",
        "lineage_chain_digest",
        "llm_trace_refs",
        "retrieval_receipt_embed",
        "non_authoritative",
    },
)


def _sha256_digest_v1(body: Mapping[str, Any]) -> str:
    digest = hash_reasoning_canonical_json_sha256_v1(body)
    if digest.startswith("sha256:"):
        return digest
    return f"sha256:{digest}"


class SynthesisArtifactMaterializationError(ValueError):
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


def synthesis_intelligence_artifact_schema_path_v1() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        candidate = (
            root
            / "DOCS"
            / "cortex"
            / "synthesis"
            / "schemas"
            / "synthesis-intelligence-artifact-v1.schema.json"
        )
        if candidate.is_file():
            return candidate
    return (
        start.parents[4]
        / "DOCS"
        / "cortex"
        / "synthesis"
        / "schemas"
        / "synthesis-intelligence-artifact-v1.schema.json"
    )


def resolve_synthesis_artifact_kind_v1(synthesis_workload_class: str) -> str:
    """Map workload class to closed ``artifact_kind`` enum."""
    norm = normalize_synthesis_workload_class_v1(synthesis_workload_class)
    meta = SYNTHESIS_WORKLOAD_CLASS_METADATA_V1.get(norm, {})
    kind = str(meta.get("primary_artifact_kind") or "").strip()
    if kind in SYNTHESIS_ARTIFACT_KINDS_V1:
        return kind
    if norm == "pipeline_default":
        return "degradation_brief"
    if norm == "replay_equivalence_synthesis":
        return "degradation_brief"
    return "degradation_brief"


def build_synthesis_artifact_lineage_chain_digest_v1(
    *,
    artifact_id: str,
    retrieval_receipt_embed: Mapping[str, Any],
) -> str:
    """Fallback digest when lineage graph is not materialized (tests without DB session)."""
    return _sha256_digest_v1(
        {
            "terminal_artifact_kind": "synthesis_intelligence",
            "terminal_artifact_ref": artifact_id,
            "retrieval_receipt_embed_digest": retrieval_receipt_embed.get(
                "retrieval_receipt_embed_digest",
            ),
            PHASE07_REPLAY_IDENTITY_FIELD_V1: retrieval_receipt_embed.get(
                PHASE07_REPLAY_IDENTITY_FIELD_V1,
            ),
        },
    )


def compute_synthesis_artifact_structural_body_v1(body: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical structural scope for ``artifact_digest`` (excludes discourse-only text)."""
    claims_out: list[dict[str, Any]] = []
    for row in body.get("claims") or []:
        if not isinstance(row, Mapping):
            continue
        claim = dict(row)
        if claim.get("discourse_only") is True:
            claim.pop("text", None)
        claims_out.append(claim)
    narrative_out: list[dict[str, Any]] = []
    for row in body.get("narrative_blocks") or []:
        if not isinstance(row, Mapping):
            continue
        block = dict(row)
        if block.get("discourse_only") is True:
            block.pop("text", None)
        narrative_out.append(block)
    structural: dict[str, Any] = {
        "schema_version": body.get("schema_version"),
        "artifact_id": body.get("artifact_id"),
        "artifact_kind": body.get("artifact_kind"),
        "synthesis_legality_class": body.get("synthesis_legality_class"),
        "synthesis_job_replay_identity": body.get("synthesis_job_replay_identity"),
        "retrieval_query_replay_identity": body.get("retrieval_query_replay_identity"),
        "synthesis_policy_pack_digest": body.get("synthesis_policy_pack_digest"),
        "evidence_scope_summary": body.get("evidence_scope_summary"),
        "claims": claims_out,
        "narrative_blocks": narrative_out,
        "synthesis_citation_envelope": body.get("synthesis_citation_envelope"),
        "synthesis_omission_rows": body.get("synthesis_omission_rows"),
        "synthesis_degradation_rollup": body.get("synthesis_degradation_rollup"),
        "synthesis_legality_posture": body.get("synthesis_legality_posture"),
        "lineage_chain_digest": body.get("lineage_chain_digest"),
        "llm_trace_refs": body.get("llm_trace_refs"),
        "retrieval_receipt_embed": body.get("retrieval_receipt_embed"),
        "non_authoritative": body.get("non_authoritative"),
        "retrieval_binding_envelope": body.get("retrieval_binding_envelope"),
        "tcre_binding_envelope": body.get("tcre_binding_envelope"),
        "degradation_propagation_chain": body.get("degradation_propagation_chain"),
    }
    return structural


def compute_synthesis_artifact_digest_v1(body: Mapping[str, Any]) -> str:
    return _sha256_digest_v1(compute_synthesis_artifact_structural_body_v1(body))


def list_synthesis_intelligence_artifact_validation_errors_v1(
    artifact: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if int(artifact.get("schema_version", 0)) != SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_VERSION_V1:
        errors.append("schema_version_mismatch")
    missing = sorted(_ARTIFACT_REQUIRED_TOP_LEVEL_V1 - set(artifact.keys()))
    if missing:
        errors.append(f"missing_required_fields:{','.join(missing)}")
    kind = str(artifact.get("artifact_kind") or "")
    if kind not in SYNTHESIS_ARTIFACT_KINDS_V1:
        errors.append(f"unknown_artifact_kind:{kind}")
    legality = str(artifact.get("synthesis_legality_class") or "")
    if legality not in SYNTHESIS_LEGALITY_AUTHORITATIVE_USABLE_V1 and legality not in {
        "synthesis_unverifiable",
        "synthesis_forbidden",
    }:
        errors.append(f"unknown_synthesis_legality_class:{legality}")
    digest = str(artifact.get("artifact_digest") or "")
    if digest and not digest.startswith("sha256:") and len(digest) != 64:
        errors.append("artifact_digest_format")
    return errors


def validate_synthesis_intelligence_artifact_v1(artifact: Mapping[str, Any]) -> None:
    errors = list_synthesis_intelligence_artifact_validation_errors_v1(artifact)
    if errors:
        raise SynthesisArtifactMaterializationError(
            "synthesis_intelligence_artifact_invalid",
            detail={"errors": errors},
        )
    computed = compute_synthesis_artifact_digest_v1(artifact)
    pinned = str(artifact.get("artifact_digest") or "")
    if pinned and pinned != computed:
        raise SynthesisArtifactMaterializationError(
            "artifact_digest_mismatch",
            detail={"expected": computed, "actual": pinned},
        )
    partition = "authoritative"
    if artifact.get("non_authoritative") is True:
        partition = "exploration"
    validate_synthesis_authoritative_artifact_algebra_v1(
        artifact,
        execution_partition=partition,
    )


def evaluate_synthesis_publish_barrier_v1(
    *,
    synthesis_legality_class: str,
    session: Session | None = None,
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Publish barrier law — legality class + optional **PROD-SYN-01** (Step 25)."""
    legality_passed = synthesis_legality_class in _SYNTHESIS_PUBLISH_BARRIER_LEGALITY_V1
    prod_syn: dict[str, Any] | None = None
    production_passed = True
    if session is not None and tenant_id is not None:
        from vector.domains.cortex.synthesis.synthesis_runtime_legality_matrix import (
            evaluate_prod_syn01_v1,
        )

        prod_syn = evaluate_prod_syn01_v1(session, tenant_id=tenant_id)
        production_passed = bool(prod_syn.get("passed"))
    passed = legality_passed and production_passed
    reason = "legality_publishable"
    if not legality_passed:
        reason = "publish_barrier_legality_blocked"
    elif not production_passed:
        reason = "publish_barrier_prod_syn01_blocked"
    return {
        "publish_barrier_passed": passed,
        "can_publish": passed,
        "synthesis_publication_epoch": None,
        "published": False,
        "reason": reason,
        "prod_syn01": prod_syn,
    }


def build_synthesis_intelligence_artifact_v1(
    *,
    session: Session | None = None,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    envelope: Mapping[str, Any],
    synthesis_legality_class: str,
    synthesis_job_replay_identity: str,
    synthesis_legality_posture: Mapping[str, Any],
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    claims: Sequence[Mapping[str, Any]],
    synthesis_citation_envelope: Mapping[str, Any],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    synthesis_degradation_rollup: Mapping[str, Any],
    llm_trace_refs: Sequence[Mapping[str, Any]],
    evidence_scope_summary: Mapping[str, Any],
    artifact_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    aid = artifact_id or uuid.uuid4()
    artifact_kind = resolve_synthesis_artifact_kind_v1(str(envelope["synthesis_workload_class"]))
    policy_digest = str(
        envelope.get("_synthesis_policy_pack_digest")
        or envelope.get("synthesis_policy_pack_digest")
        or synthesis_policy_pack_digest_v1(),
    )
    receipt_embed = build_retrieval_receipt_embed_v1(
        retrieval_ingress=retrieval_ingress,
        retrieval_subqueries=retrieval_subqueries,
    )
    primary_rqid = primary_retrieval_query_replay_identity_v1(
        retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
    )
    scope = envelope.get("retrieval_scope")
    scope_lookup = (
        str(scope.get("retrieval_lookup_id") or "").strip()
        if isinstance(scope, Mapping)
        else ""
    )
    partition = str(envelope.get("execution_partition") or "authoritative").strip().lower()
    body: dict[str, Any] = {
        "schema_version": SYNTHESIS_INTELLIGENCE_ARTIFACT_SCHEMA_VERSION_V1,
        "artifact_id": str(aid),
        "artifact_kind": artifact_kind,
        "artifact_digest": "",
        "synthesis_legality_class": synthesis_legality_class,
        "synthesis_job_replay_identity": synthesis_job_replay_identity,
        "retrieval_query_replay_identity": primary_rqid,
        **({"retrieval_lookup_id": scope_lookup} if scope_lookup else {}),
        "synthesis_policy_pack_digest": policy_digest,
        "synthesis_publication_epoch": None,
        "evidence_scope_summary": dict(evidence_scope_summary),
        "claims": [dict(c) for c in claims if isinstance(c, Mapping)],
        "synthesis_citation_envelope": dict(synthesis_citation_envelope),
        "synthesis_omission_rows": [
            dict(r) for r in synthesis_omission_rows if isinstance(r, Mapping)
        ],
        "synthesis_degradation_rollup": dict(synthesis_degradation_rollup),
        "synthesis_legality_posture": dict(synthesis_legality_posture),
        "lineage_chain_digest": "",
        "llm_trace_refs": [dict(t) for t in llm_trace_refs if isinstance(t, Mapping)],
        "retrieval_receipt_embed": receipt_embed,
        "non_authoritative": partition == "exploration",
        "tenant_id": str(tenant_id),
    }
    retrieval_source = envelope.get("_retrieval_response_source")
    binding_bundle = build_synthesis_binding_bundle_v1(
        retrieval_ingress=retrieval_ingress,
        retrieval_subqueries=retrieval_subqueries,
        synthesis_omission_rows=list(synthesis_omission_rows),
        retrieval_response_source=(
            retrieval_source if isinstance(retrieval_source, Mapping) else None
        ),
    )
    body["retrieval_binding_envelope"] = binding_bundle["retrieval_binding_envelope"]
    body["tcre_binding_envelope"] = binding_bundle["tcre_binding_envelope"]
    body["degradation_propagation_chain"] = binding_bundle["degradation_propagation_chain"]
    enforce_synthesis_binding_copy_law_v1(
        retrieval_ingress,
        retrieval_binding_envelope=body["retrieval_binding_envelope"],
        tcre_binding_envelope=body["tcre_binding_envelope"],
    )
    apply_synthesis_degradation_to_artifact_v1(
        body,
        retrieval_ingress=retrieval_ingress,
        synthesis_legality_class=synthesis_legality_class,
        synthesis_workload_class=str(envelope.get("synthesis_workload_class") or ""),
    )
    if session is not None:
        lineage_out = apply_synthesis_lineage_to_artifact_v1(
            session,
            tenant_id=tenant_id,
            artifact_body=body,
            retrieval_ingress=retrieval_ingress,
            retrieval_subqueries=retrieval_subqueries,
            envelope=envelope,
        )
        gap_rows = list(lineage_out.get("lineage_gap_sd_rows") or [])
        if gap_rows:
            body["synthesis_omission_rows"] = list(body.get("synthesis_omission_rows") or []) + gap_rows
    else:
        body["lineage_chain_digest"] = build_synthesis_artifact_lineage_chain_digest_v1(
            artifact_id=str(aid),
            retrieval_receipt_embed=receipt_embed,
        )
    body["artifact_digest"] = compute_synthesis_artifact_digest_v1(body)
    return body


def get_synthesis_artifact_by_job_id_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> CortexSynthesisArtifact | None:
    return session.scalar(
        select(CortexSynthesisArtifact)
        .where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.job_id == job_id,
        )
        .order_by(CortexSynthesisArtifact.created_at.desc())
        .limit(1),
    )


def get_synthesis_artifact_row_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> CortexSynthesisArtifact | None:
    row = session.get(CortexSynthesisArtifact, artifact_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def persist_synthesis_artifact_row_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    body: Mapping[str, Any],
    published: bool,
    synthesis_publication_epoch: str | None,
) -> CortexSynthesisArtifact:
    digest = str(body["artifact_digest"])
    existing = session.scalar(
        select(CortexSynthesisArtifact).where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.artifact_digest == digest,
        ),
    )
    if existing is not None:
        if existing.job_id == job_id:
            return existing
        raise SynthesisArtifactMaterializationError(
            "artifact_digest_collision",
            detail={"artifact_digest": digest, "existing_job_id": str(existing.job_id)},
        )
    from vector.domains.cortex.synthesis.synthesis_artifact_pins import (
        apply_artifact_query_pins_to_row_v1,
    )

    row = CortexSynthesisArtifact(
        id=uuid.UUID(str(body["artifact_id"])),
        tenant_id=tenant_id,
        job_id=job_id,
        artifact_kind=str(body["artifact_kind"]),
        artifact_digest=digest,
        synthesis_legality_class=str(body["synthesis_legality_class"]),
        published=bool(published),
        synthesis_publication_epoch=synthesis_publication_epoch,
        body_json=dict(body),
    )
    apply_artifact_query_pins_to_row_v1(row, body=body)
    session.add(row)
    session.flush()
    return row


def build_synthesis_artifact_summary_v1(row: CortexSynthesisArtifact) -> dict[str, Any]:
    body = dict(row.body_json or {})
    return {
        "artifact_id": str(row.id),
        "artifact_kind": row.artifact_kind,
        "artifact_digest": row.artifact_digest,
        "synthesis_legality_class": row.synthesis_legality_class,
        "published": row.published,
        "synthesis_publication_epoch": row.synthesis_publication_epoch,
        "job_id": str(row.job_id),
        "claim_count": len(body.get("claims") or []),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def materialize_synthesis_artifact_for_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job: CortexSynthesisJob,
    envelope: Mapping[str, Any],
    synthesis_legality_class: str,
    synthesis_job_replay_identity: str,
    synthesis_legality_posture: Mapping[str, Any],
    retrieval_ingress: Mapping[str, Any],
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    claims: Sequence[Mapping[str, Any]],
    synthesis_citation_envelope: Mapping[str, Any],
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    synthesis_degradation_rollup: Mapping[str, Any],
    llm_trace_refs: Sequence[Mapping[str, Any]],
    evidence_scope_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist artifact (unpublished); publication epoch is Step 18."""
    existing = get_synthesis_artifact_by_job_id_v1(
        session,
        tenant_id=tenant_id,
        job_id=job.id,
    )
    if existing is not None:
        barrier = evaluate_synthesis_publish_barrier_v1(
            synthesis_legality_class=existing.synthesis_legality_class,
            session=session,
            tenant_id=tenant_id,
        )
        return {
            "artifact_id": str(existing.id),
            "artifact_digest": existing.artifact_digest,
            "published": existing.published,
            "publish_status": "materialized",
            "publish_barrier": barrier,
            "idempotent_replay": True,
            "artifact_body": dict(existing.body_json or {}),
        }

    barrier = evaluate_synthesis_publish_barrier_v1(
        synthesis_legality_class=synthesis_legality_class,
        session=session,
        tenant_id=tenant_id,
    )
    body = build_synthesis_intelligence_artifact_v1(
        session=session,
        tenant_id=tenant_id,
        job_id=job.id,
        envelope=envelope,
        synthesis_legality_class=synthesis_legality_class,
        synthesis_job_replay_identity=synthesis_job_replay_identity,
        synthesis_legality_posture=synthesis_legality_posture,
        retrieval_ingress=retrieval_ingress,
        retrieval_subqueries=retrieval_subqueries,
        claims=claims,
        synthesis_citation_envelope=synthesis_citation_envelope,
        synthesis_omission_rows=synthesis_omission_rows,
        synthesis_degradation_rollup=synthesis_degradation_rollup,
        llm_trace_refs=llm_trace_refs,
        evidence_scope_summary=evidence_scope_summary,
    )
    validate_synthesis_intelligence_artifact_v1(body)
    caps = synthesis_policy_pack_caps_v1()
    max_bytes = int(
        (envelope.get("selection_policy") or {}).get(
            "max_artifact_json_bytes",
            caps.get("max_artifact_json_bytes", 512_000),
        ),
    )
    assert_synthesis_artifact_under_byte_cap_v1(body, max_artifact_json_bytes=max_bytes)
    row = persist_synthesis_artifact_row_v1(
        session,
        tenant_id=tenant_id,
        job_id=job.id,
        body=body,
        published=bool(barrier["published"]),
        synthesis_publication_epoch=barrier.get("synthesis_publication_epoch"),
    )
    publish_status = "materialized_unpublished"
    if barrier["publish_barrier_passed"]:
        publish_status = "materialized_publish_deferred"
    return {
        "artifact_id": str(row.id),
        "artifact_digest": row.artifact_digest,
        "published": row.published,
        "publish_status": publish_status,
        "publish_barrier": barrier,
        "idempotent_replay": False,
        "artifact_body": body,
    }


def list_synthesis_artifacts_for_tenant_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    from vector.domains.cortex.synthesis.synthesis_artifact_query import (
        SynthesisArtifactListFiltersV1,
        list_synthesis_artifacts_query_v1,
    )

    out = list_synthesis_artifacts_query_v1(
        session,
        tenant_id=tenant_id,
        filters=SynthesisArtifactListFiltersV1(limit=limit),
    )
    return list(out.get("artifacts") or [])


def get_synthesis_artifact_detail_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> dict[str, Any]:
    row = get_synthesis_artifact_row_v1(session, tenant_id=tenant_id, artifact_id=artifact_id)
    if row is None:
        raise SynthesisArtifactMaterializationError(
            "synthesis_artifact_not_found",
            http_status=404,
        )
    body = dict(row.body_json or {})
    return {
        "surface_kind": "synthesis_artifact_detail",
        "phase08_synthesis_artifact_materialization_runtime_schema_version": (
            PHASE08_SYNTHESIS_ARTIFACT_MATERIALIZATION_RUNTIME_SCHEMA_VERSION
        ),
        "artifact_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "job_id": str(row.job_id),
        "artifact_kind": row.artifact_kind,
        "artifact_digest": row.artifact_digest,
        "synthesis_legality_class": row.synthesis_legality_class,
        "published": row.published,
        "synthesis_publication_epoch": row.synthesis_publication_epoch,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "synthesis_intelligence_artifact": body,
        "claim_count": len(body.get("claims") or []),
        "citation_count": (
            (body.get("synthesis_citation_envelope") or {}).get("citation_count", 0)
            if isinstance(body.get("synthesis_citation_envelope"), Mapping)
            else 0
        ),
        "binding_panel": build_synthesis_binding_panel_v1(body),
        "lineage_panel": build_synthesis_lineage_panel_v1(
            session,
            tenant_id=tenant_id,
            artifact_body=body,
        ),
    }


def build_synthesis_artifact_explorer_catalog_v1(
    session: Session | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    recent: list[dict[str, Any]] = []
    if session is not None and tenant_id is not None:
        recent = list_synthesis_artifacts_for_tenant_v1(session, tenant_id=tenant_id, limit=25)
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_artifact_explorer_v1",
        "phase08_synthesis_artifact_materialization_runtime_schema_version": (
            PHASE08_SYNTHESIS_ARTIFACT_MATERIALIZATION_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_ART01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_ARTIFACT_MATERIALIZATION_SPEC_REF_V1,
        "artifact_schema_path": str(synthesis_intelligence_artifact_schema_path_v1()),
        "artifact_kinds": sorted(SYNTHESIS_ARTIFACT_KINDS_V1),
        "publish_barrier_legality_classes": sorted(_SYNTHESIS_PUBLISH_BARRIER_LEGALITY_V1),
        "publication_epoch_deferred_step": 32,
        "recent_artifacts": recent,
        "rules": [
            {"id": "SYN-ART-01", "text": "Artifact digest excludes discourse-only claim text"},
            {"id": "SYN-ART-02", "text": "Publication epoch bump deferred until Step 18"},
        ],
    }


def verify_gp08_art01_artifact_kind_registry_static() -> dict[str, Any]:
    errors: list[str] = []
    path = synthesis_intelligence_artifact_schema_path_v1()
    if not path.is_file():
        errors.append("missing_artifact_schema_file")
    else:
        text = path.read_text(encoding="utf-8")
        for kind in SYNTHESIS_ARTIFACT_KINDS_V1:
            if kind not in text:
                errors.append(f"schema_missing_kind:{kind}")
    return {
        "id": GP08_ART01_GATE_ID_V1,
        "name": "synthesis_artifact_kind_registry",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors, "artifact_kinds": sorted(SYNTHESIS_ARTIFACT_KINDS_V1)},
    }


def verify_gp08_schema01_synthesis_intelligence_artifact_static() -> dict[str, Any]:
    """``G-P08-SCHEMA-01`` — minimal artifact round-trip + digest stability."""
    errors: list[str] = []
    tid = uuid.UUID(int=0)
    jid = uuid.uuid4()
    envelope = {
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
    }
    body = build_synthesis_intelligence_artifact_v1(
        tenant_id=tid,
        job_id=jid,
        envelope=envelope,
        synthesis_legality_class="synthesis_degraded",
        synthesis_job_replay_identity="sha256:" + "a" * 64,
        synthesis_legality_posture={},
        retrieval_ingress={"retrieval_evidence_hits": []},
        retrieval_subqueries=[],
        claims=[],
        synthesis_citation_envelope={"citation_count": 0, "citations": []},
        synthesis_omission_rows=[],
        synthesis_degradation_rollup={},
        llm_trace_refs=[],
        evidence_scope_summary={"hit_count": 0},
    )
    try:
        validate_synthesis_intelligence_artifact_v1(body)
    except Exception as exc:
        errors.append(f"validate_failed:{exc}")
    d1 = compute_synthesis_artifact_digest_v1(body)
    d2 = compute_synthesis_artifact_digest_v1(body)
    if d1 != d2:
        errors.append("digest_unstable")
    body_a = dict(body)
    body_a["claims"] = [{"claim_id": "clm-0001", "discourse_only": True, "text": "glue-a"}]
    body_b = dict(body)
    body_b["claims"] = [{"claim_id": "clm-0001", "discourse_only": True, "text": "glue-b"}]
    if compute_synthesis_artifact_digest_v1(body_a) != compute_synthesis_artifact_digest_v1(body_b):
        errors.append("discourse_text_should_not_affect_digest")
    return {
        "id": "G-P08-SCHEMA-01",
        "name": "synthesis_intelligence_artifact",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
