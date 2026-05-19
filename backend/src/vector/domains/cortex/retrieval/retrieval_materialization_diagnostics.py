"""Persist structured retrieval materialization diagnostics."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_NO_CANDIDATES_V1,
    normalize_skip_reasons_from_stats_v1,
)
from vector.domains.cortex.retrieval.retrieval_density_metrics import (
    record_retrieval_materialization_metrics_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
    CortexRetrievalMaterializationReport,
)


def build_retrieval_materialization_report_body_v1(
    *,
    stats: dict[str, Any],
    tcre_candidates: int = 0,
    walks_candidates: int = 0,
    org_link_candidates: int = 0,
) -> dict[str, Any]:
    skip_raw = list(stats.get("skip_reasons") or [])
    normalized = normalize_skip_reasons_from_stats_v1(skip_raw)
    accepted = int(stats.get("entries_materialized") or stats.get("accepted_rows") or 0)
    skipped = len(normalized)
    entry_count = int(stats.get("entry_count") or accepted)

    empty_causes: list[str] = []
    if tcre_candidates == 0 and walks_candidates == 0 and org_link_candidates == 0:
        empty_causes.append("no_upstream_candidates")
    if entry_count == 0 and accepted == 0:
        empty_causes.append("zero_accepted_rows")
    if normalized:
        empty_causes.append("all_candidates_skipped")

    return {
        "tenant_id": stats.get("tenant_id"),
        "pipeline_run_id": stats.get("pipeline_run_id"),
        "retrieval_epoch": stats.get("index_epoch"),
        "retrieval_card_classification": stats.get("retrieval_card_classification"),
        "tcre_candidates": tcre_candidates,
        "walks_candidates": walks_candidates,
        "org_link_candidates": org_link_candidates,
        "accepted_rows": accepted,
        "rejected_rows": int(stats.get("rejected_rows") or 0),
        "skipped_rows": skipped,
        "skip_reasons": normalized,
        "legality_failures": [
            r for r in normalized if r.get("ret_skip_code", "").endswith("LEGALITY-FAILED")
        ],
        "empty_scope_causes": empty_causes,
        "build_state": stats.get("build_state"),
        "entry_count": entry_count,
        "output_index_hash": stats.get("output_index_hash"),
    }


def persist_retrieval_materialization_report_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
    stats: dict[str, Any],
    tcre_candidates: int = 0,
    walks_candidates: int = 0,
    org_link_candidates: int = 0,
) -> CortexRetrievalMaterializationReport:
    body = build_retrieval_materialization_report_body_v1(
        stats=stats,
        tcre_candidates=tcre_candidates,
        walks_candidates=walks_candidates,
        org_link_candidates=org_link_candidates,
    )
    normalized = list(body.get("skip_reasons") or [])
    if (
        body["accepted_rows"] == 0
        and tcre_candidates + walks_candidates + org_link_candidates == 0
    ):
        normalized.append(
            {
                "source": "pipeline",
                "upstream_code": "no_candidates",
                "ret_skip_code": RET_SKIP_NO_CANDIDATES_V1,
                "replay_safe": True,
            }
        )
        body["skip_reasons"] = normalized
        body["skipped_rows"] = len(normalized)

    record_retrieval_materialization_metrics_v1(
        tenant_id=tenant_id,
        accepted_rows=int(body["accepted_rows"]),
        skipped_rows=int(body["skipped_rows"]),
        entry_count=int(body.get("entry_count") or 0),
    )

    row = CortexRetrievalMaterializationReport(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        retrieval_epoch=str(body.get("retrieval_epoch") or "") or None,
        tcre_candidates=tcre_candidates,
        walks_candidates=walks_candidates,
        org_link_candidates=org_link_candidates,
        accepted_rows=int(body["accepted_rows"]),
        rejected_rows=int(body["rejected_rows"]),
        skipped_rows=int(body["skipped_rows"]),
        skip_reasons_json=normalized,
        report_json=body,
    )
    session.add(row)
    session.flush()
    return row
