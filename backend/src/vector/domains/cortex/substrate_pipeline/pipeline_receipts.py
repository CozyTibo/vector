"""Pipeline execution receipts — which phase produced which retrieval evidence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)


def build_phase_execution_receipt_v1(
    *,
    phase_id: str,
    status: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    body = {"phase_id": phase_id, "status": status, "output_summary": _summarize_phase_output(phase_id, output)}
    return {
        "phase_execution_receipt_digest": hash_reasoning_canonical_json_sha256_v1(body),
        "body": body,
    }


def _summarize_phase_output(phase_id: str, output: dict[str, Any]) -> dict[str, Any]:
    if phase_id.endswith("traversal"):
        return {
            "walk_ids": output.get("walk_ids"),
            "primary_octs_walk_id": output.get("primary_octs_walk_id"),
            "walks_persisted": output.get("walks_persisted"),
            "starts_selected": output.get("starts_selected"),
            "execution_anchor_count": output.get("execution_anchor_count"),
        }
    if phase_id.endswith("tcre"):
        return {
            "job_id": output.get("job_id"),
            "status": output.get("status"),
            "async": output.get("async"),
        }
    if phase_id.endswith("retrieval"):
        return {
            "index_epoch": output.get("index_epoch"),
            "published_index_epoch": output.get("published_index_epoch") or output.get("index_epoch"),
            "build_state": output.get("build_state"),
            "entry_count": output.get("entry_count"),
            "entries_materialized": output.get("entries_materialized"),
        }
    if phase_id.endswith("synthesis"):
        return {
            "synthesis_publication_epoch": output.get("synthesis_publication_epoch"),
            "artifact_digests": output.get("artifact_digests"),
            "synthesis_job_ids": output.get("synthesis_job_ids"),
            "retrieval_epoch_pinned": output.get("retrieval_epoch_pinned"),
            "jobs_completed": output.get("jobs_completed"),
            "sd_rollup": output.get("sd_rollup"),
        }
    if phase_id.endswith("graph"):
        return {
            "graph_projection_stable_hash_sha256": output.get("graph_projection_stable_hash_sha256"),
            "node_count": output.get("node_count"),
            "edge_count": output.get("edge_count"),
        }
    return {k: output[k] for k in list(output.keys())[:12]}


def build_pipeline_execution_receipt_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator receipt: phase → retrieval evidence linkage."""
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        return {"error": "pipeline_run_not_found"}
    phases = list(
        session.scalars(
            select(CortexSubstratePhaseRun)
            .where(CortexSubstratePhaseRun.pipeline_run_id == pipeline_run_id)
            .order_by(CortexSubstratePhaseRun.phase_ordinal.asc())
        ).all()
    )
    phase_receipts = [
        build_phase_execution_receipt_v1(
            phase_id=p.phase_id,
            status=p.status,
            output=dict(p.output_json or {}),
        )
        for p in phases
    ]
    body = {
        "pipeline_run_id": str(pipeline_run_id),
        "tenant_id": str(run.tenant_id),
        "trigger_kind": run.trigger_kind,
        "status": run.status,
        "phase_receipts": phase_receipts,
    }
    return {
        "pipeline_execution_receipt_digest": hash_reasoning_canonical_json_sha256_v1(body),
        "body": body,
        "surface_kind": "runtime_backed",
    }
