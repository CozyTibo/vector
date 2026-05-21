"""Universal deterministic phase receipt contract (TRUE P0 sign-off)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)

SUBSTRATE_PHASE_RECEIPT_SCHEMA_VERSION: Final[int] = 1
SUBSTRATE_RECEIPT_DETERMINISTIC_VERSION: Final[str] = "substrate_receipt_v1"

PHASE_OUTCOME_COMPLETED: Final[str] = "COMPLETED"
PHASE_OUTCOME_COMPLETED_EMPTY: Final[str] = "COMPLETED_EMPTY"
PHASE_OUTCOME_BLOCKED: Final[str] = "BLOCKED"
PHASE_OUTCOME_WAITING_ASYNC: Final[str] = "WAITING_ASYNC"
PHASE_OUTCOME_FAILED: Final[str] = "FAILED"
PHASE_OUTCOME_SKIPPED_BY_POLICY: Final[str] = "SKIPPED_BY_POLICY"

PHASE_OUTCOMES_TERMINAL: Final[frozenset[str]] = frozenset(
    {
        PHASE_OUTCOME_COMPLETED,
        PHASE_OUTCOME_COMPLETED_EMPTY,
        PHASE_OUTCOME_BLOCKED,
        PHASE_OUTCOME_FAILED,
        PHASE_OUTCOME_SKIPPED_BY_POLICY,
    }
)


@dataclass(frozen=True)
class SubstratePhaseReceiptV1:
    schema_version: int
    phase_id: str
    tenant_id: str
    pipeline_run_id: str
    outcome: str
    receipt_hash: str
    processed_count: int
    blocked_reason: str | None
    input_epoch: str | None
    output_epoch: str | None
    started_at: str
    completed_at: str
    deterministic_version: str
    detail: dict[str, Any]

    def to_output_envelope(self) -> dict[str, Any]:
        """Merge into phase ``output_json`` (authoritative debugging surface)."""
        return {
            "substrate_phase_receipt": {
                "schema_version": self.schema_version,
                "phase_id": self.phase_id,
                "tenant_id": self.tenant_id,
                "pipeline_run_id": self.pipeline_run_id,
                "outcome": self.outcome,
                "receipt_hash": self.receipt_hash,
                "processed_count": self.processed_count,
                "blocked_reason": self.blocked_reason,
                "input_epoch": self.input_epoch,
                "output_epoch": self.output_epoch,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "deterministic_version": self.deterministic_version,
                "detail": dict(self.detail),
            },
            "receipt_hash": self.receipt_hash,
            "outcome": self.outcome,
            "processed_count": self.processed_count,
            "blocked_reason": self.blocked_reason,
            "input_epoch": self.input_epoch,
            "output_epoch": self.output_epoch,
        }


def utc_now_iso_v1() -> str:
    return datetime.now(tz=UTC).isoformat()


def compute_substrate_phase_receipt_hash_v1(
    *,
    phase_id: str,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    outcome: str,
    processed_count: int,
    blocked_reason: str | None,
    input_epoch: str | None,
    output_epoch: str | None,
    detail: dict[str, Any],
) -> str:
    body = {
        "schema_version": SUBSTRATE_PHASE_RECEIPT_SCHEMA_VERSION,
        "deterministic_version": SUBSTRATE_RECEIPT_DETERMINISTIC_VERSION,
        "phase_id": phase_id,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id),
        "outcome": outcome,
        "processed_count": int(processed_count),
        "blocked_reason": blocked_reason,
        "input_epoch": input_epoch,
        "output_epoch": output_epoch,
        "detail": detail,
    }
    return hash_reasoning_canonical_json_sha256_v1(body)


def extract_phase_receipt_detail_v1(phase_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Bounded phase-specific subset for hashing (no timestamps / celery ids)."""
    if phase_id == PHASE_02_CANONICAL:
        summary = raw.get("canonical_summary")
        sm = summary if isinstance(summary, dict) else {}
        return {
            "bundle_id": raw.get("bundle_id"),
            "canonical_outcome": raw.get("canonical_outcome") or sm.get("canonical_outcome"),
            "total_succeeded": sm.get("total_succeeded"),
            "total_failed_rows": sm.get("total_failed_rows"),
            "deferral_counts": sm.get("deferral_counts"),
        }
    if phase_id == PHASE_03_IDENTITY:
        audit = raw.get("identity_substrate_audit")
        aud = audit if isinstance(audit, dict) else {}
        return {
            "bundle_id": aud.get("bundle_id"),
            "candidate_set_sha256": aud.get("candidate_set_sha256"),
            "counts_after": aud.get("counts_after"),
        }
    if phase_id == PHASE_04_GRAPH:
        return {
            "graph_projection_stable_hash_sha256": raw.get("graph_projection_stable_hash_sha256"),
            "node_count": raw.get("node_count"),
            "edge_count": raw.get("edge_count"),
        }
    if phase_id == PHASE_05_TRAVERSAL:
        return {
            "primary_octs_walk_id": raw.get("primary_octs_walk_id"),
            "walks_persisted": raw.get("walks_persisted"),
            "starts_selected": raw.get("starts_selected"),
        }
    if phase_id == PHASE_06_TCRE:
        return {
            "job_id": raw.get("job_id"),
            "async": raw.get("async"),
            "status": raw.get("status"),
        }
    if phase_id == PHASE_07_RETRIEVAL:
        return {
            "published_index_epoch": raw.get("published_index_epoch") or raw.get("index_epoch"),
            "entries_materialized": raw.get("entries_materialized") or raw.get("entry_count"),
            "build_state": raw.get("build_state"),
            "retrieval_outcome": raw.get("retrieval_outcome"),
        }
    if phase_id == PHASE_08_SYNTHESIS:
        return {
            "jobs_enqueued": raw.get("jobs_enqueued"),
            "jobs_completed": raw.get("jobs_completed"),
            "jobs_failed": raw.get("jobs_failed"),
            "activation_reason": raw.get("activation_reason"),
        }
    return {k: raw[k] for k in sorted(raw.keys())[:12] if k != "substrate_phase_receipt"}


def infer_processed_count_v1(phase_id: str, raw: dict[str, Any]) -> int:
    if phase_id == PHASE_02_CANONICAL:
        summary = raw.get("canonical_summary")
        if isinstance(summary, dict):
            return int(summary.get("total_succeeded") or 0)
        return 0
    if phase_id == PHASE_03_IDENTITY:
        after = raw.get("counts_after")
        if isinstance(after, dict):
            return int(after.get("org_link_edges") or after.get("edges") or 0)
        return 0
    if phase_id == PHASE_04_GRAPH:
        return int(raw.get("node_count") or 0) + int(raw.get("edge_count") or 0)
    if phase_id == PHASE_05_TRAVERSAL:
        return int(raw.get("walks_persisted") or 0)
    if phase_id == PHASE_06_TCRE:
        return 1 if raw.get("job_id") else 0
    if phase_id == PHASE_07_RETRIEVAL:
        return int(raw.get("entries_materialized") or raw.get("entry_count") or 0)
    if phase_id == PHASE_08_SYNTHESIS:
        return int(raw.get("jobs_completed") or raw.get("jobs_enqueued") or 0)
    return 0


def infer_input_output_epochs_v1(
    phase_id: str,
    raw: dict[str, Any],
    *,
    input_epoch: str | None = None,
) -> tuple[str | None, str | None]:
    inp = input_epoch
    out_ep: str | None = None
    if phase_id == PHASE_07_RETRIEVAL or phase_id == PHASE_08_SYNTHESIS:
        out_ep = raw.get("published_index_epoch") or raw.get("index_epoch") or raw.get(
            "synthesis_publication_epoch"
        )
        if isinstance(out_ep, str):
            out_ep = out_ep.strip() or None
        else:
            out_ep = None
    if phase_id == PHASE_04_GRAPH:
        gh = raw.get("graph_projection_stable_hash_sha256")
        out_ep = str(gh) if gh else None
    return inp, out_ep


def build_substrate_phase_receipt_v1(
    *,
    phase_id: str,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    outcome: str,
    raw_output: dict[str, Any],
    started_at: str,
    completed_at: str | None = None,
    blocked_reason: str | None = None,
    input_epoch: str | None = None,
    processed_count: int | None = None,
) -> SubstratePhaseReceiptV1:
    detail = extract_phase_receipt_detail_v1(phase_id, raw_output)
    proc = (
        int(processed_count)
        if processed_count is not None
        else infer_processed_count_v1(phase_id, raw_output)
    )
    inp, out_ep = infer_input_output_epochs_v1(phase_id, raw_output, input_epoch=input_epoch)
    completed = completed_at or utc_now_iso_v1()
    digest = compute_substrate_phase_receipt_hash_v1(
        phase_id=phase_id,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        outcome=outcome,
        processed_count=proc,
        blocked_reason=blocked_reason,
        input_epoch=inp,
        output_epoch=out_ep,
        detail=detail,
    )
    return SubstratePhaseReceiptV1(
        schema_version=SUBSTRATE_PHASE_RECEIPT_SCHEMA_VERSION,
        phase_id=phase_id,
        tenant_id=str(tenant_id),
        pipeline_run_id=str(pipeline_run_id),
        outcome=outcome,
        receipt_hash=digest,
        processed_count=proc,
        blocked_reason=blocked_reason,
        input_epoch=inp,
        output_epoch=out_ep,
        started_at=started_at,
        completed_at=completed,
        deterministic_version=SUBSTRATE_RECEIPT_DETERMINISTIC_VERSION,
        detail=detail,
    )


def merge_receipt_into_output(
    raw_output: dict[str, Any],
    receipt: SubstratePhaseReceiptV1,
) -> dict[str, Any]:
    return {**dict(raw_output), **receipt.to_output_envelope()}


def read_phase_receipt_from_output(output: dict[str, Any] | None) -> dict[str, Any] | None:
    if not output:
        return None
    rec = output.get("substrate_phase_receipt")
    return rec if isinstance(rec, dict) else None
