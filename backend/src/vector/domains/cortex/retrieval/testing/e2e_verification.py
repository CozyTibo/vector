"""E2E operator verification helpers for retrieval substrate."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.query_execution import execute_retrieval_query_envelope_v1
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    project_retrieval_completeness_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.retrieval.retrieval_truth_validation import (
    run_retrieval_truth_validation_suite_v1,
)


def assert_retrieval_substrate_ready_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    min_coverage_percent: float = 0.0,
) -> dict[str, Any]:
    """Fail-closed checks before declaring E2E retrieval ready."""
    coverage = project_retrieval_completeness_v1(session, tenant_id=tenant_id)
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    truth = run_retrieval_truth_validation_suite_v1(session, tenant_id=tenant_id)
    cov_pct = float(coverage.get("coverage_percent") or 0.0)
    errors: list[str] = []
    if published is None:
        errors.append("no_published_index_epoch")
    if cov_pct < min_coverage_percent:
        errors.append(f"coverage_below_threshold:{cov_pct}<{min_coverage_percent}")
    if not truth.get("passed"):
        errors.append("truth_validation_failed")
    return {
        "ready": len(errors) == 0,
        "errors": errors,
        "published_index_epoch": published,
        "coverage": coverage,
        "truth_validation": truth,
    }


def assert_lawful_query_replay_stable_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    """Double-run query envelope; replay identity must match."""
    a = execute_retrieval_query_envelope_v1(session, tenant_id=tenant_id, body=envelope)
    b = execute_retrieval_query_envelope_v1(session, tenant_id=tenant_id, body=envelope)
    id_a = str(a.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    id_b = str(b.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    return {
        "passed": id_a == id_b and id_a != "",
        "retrieval_query_replay_identity": id_a,
        "legality_a": a.get("retrieval_legality_class"),
        "legality_b": b.get("retrieval_legality_class"),
        "hit_count_a": len(a.get("hits") or []),
        "hit_count_b": len(b.get("hits") or []),
    }
