"""P085-21 — materialization reports + RET-SKIP (**G-P085-RET-01**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_materialization_diagnostics import (
    build_retrieval_materialization_report_body_v1,
    persist_retrieval_materialization_report_v1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_LEGALITY_FAILED_V1,
    RET_SKIP_NO_CANDIDATES_V1,
)
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
    CortexRetrievalMaterializationReport,
)


def test_build_report_body_normalizes_skips() -> None:
    body = build_retrieval_materialization_report_body_v1(
        stats={
            "tenant_id": str(uuid.uuid4()),
            "entries_materialized": 2,
            "skip_reasons": [{"source": "tcre_job", "code": "legality_failed"}],
        },
        tcre_candidates=1,
        walks_candidates=0,
        org_link_candidates=0,
    )
    skips = list(body["skip_reasons"])
    assert skips
    assert skips[0]["ret_skip_code"] == RET_SKIP_LEGALITY_FAILED_V1
    assert "upstream_code" in skips[0]
    assert "replay_safe" in skips[0]


def test_build_report_no_candidates_empty_scope() -> None:
    body = build_retrieval_materialization_report_body_v1(
        stats={"entries_materialized": 0, "skip_reasons": []},
        tcre_candidates=0,
        walks_candidates=0,
        org_link_candidates=0,
    )
    assert "no_upstream_candidates" in body["empty_scope_causes"]


@pytest.mark.integration
def test_persist_materialization_report_row(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085retrep-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 Ret Rep",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    row = persist_retrieval_materialization_report_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=None,
        stats={
            "tenant_id": str(tenant.id),
            "index_epoch": "epoch-test",
            "entries_materialized": 0,
            "skip_reasons": [],
            "entry_count": 0,
        },
        tcre_candidates=0,
        walks_candidates=0,
        org_link_candidates=0,
    )
    db_session.flush()
    assert isinstance(row, CortexRetrievalMaterializationReport)
    assert row.skipped_rows >= 1
    skip_codes = {s.get("ret_skip_code") for s in row.skip_reasons_json}
    assert RET_SKIP_NO_CANDIDATES_V1 in skip_codes
