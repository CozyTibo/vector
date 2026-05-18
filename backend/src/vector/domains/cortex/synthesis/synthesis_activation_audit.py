"""Persist phase 08 synthesis scope activation audits."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_synthesis_activation_audit import (
    CortexSynthesisActivationAudit,
)


def persist_synthesis_activation_audit_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
    materialize_output: Mapping[str, Any],
    scopes: list[dict[str, str]],
) -> CortexSynthesisActivationAudit:
    scopes_scheduled = int(materialize_output.get("scopes_scheduled") or len(scopes))
    jobs_completed = int(materialize_output.get("jobs_completed") or 0)
    jobs_failed = int(materialize_output.get("jobs_failed") or 0)
    scope_empty = bool(materialize_output.get("scope_empty"))
    workloads = int(materialize_output.get("workloads_applied") or 0)
    if workloads == 0 and scopes:
        workloads = len({s.get("workload") for s in scopes if s.get("workload")})

    empty_reason: str | None = None
    if scope_empty:
        if materialize_output.get("error_code") == "no_published_index_epoch":
            empty_reason = "no_published_index_epoch"
        elif scopes_scheduled == 0:
            empty_reason = str(materialize_output.get("empty_scope_reason") or "retrieval_empty")
        else:
            empty_reason = "scope_cap_or_continuity_incomplete"

    audit_body = {
        "published_index_epoch": materialize_output.get("published_index_epoch"),
        "synthesis_publication_epoch": materialize_output.get("synthesis_publication_epoch"),
        "sd_rollup": dict(materialize_output.get("sd_rollup") or {}),
        "scopes_overflow": materialize_output.get("scopes_overflow"),
        "artifact_digests": list(materialize_output.get("artifact_digests") or []),
    }

    row = CortexSynthesisActivationAudit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        scopes_generated=scopes_scheduled,
        scopes_skipped=max(0, scopes_scheduled - jobs_completed - jobs_failed),
        workloads_applied=workloads,
        synthesis_jobs_enqueued=scopes_scheduled,
        synthesis_jobs_started=scopes_scheduled,
        synthesis_jobs_completed=jobs_completed,
        empty_scope_reason=empty_reason,
        audit_json=audit_body,
    )
    session.add(row)
    session.flush()
    return row
