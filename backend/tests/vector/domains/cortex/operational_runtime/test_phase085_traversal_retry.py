"""P085-15 — Traversal retry + frontier healing (**G-P085-WALK-02**)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.cesp_traversal_retry_gate import (
    verify_gp085_traversal_retry_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_retry import (
    CELERY_TRAVERSAL_RETRY_TASK_NAME_V1,
    FAILURE_FRONTIER_COLLAPSE_V1,
    FAILURE_TRANSIENT_STORE_V1,
    FAILURE_WALK_INCOMPLETE_V1,
    GP085_WALK02_GATE_ID_V1,
    RETRY_ACTION_EXPLAIN_ONLY_V1,
    RETRY_ACTION_EXPONENTIAL_BACKOFF_V1,
    RETRY_ACTION_FRONTIER_HEAL_V1,
    RETRY_POLICY_BY_FAILURE_V1,
    _healed_walk_policy_v1,
    apply_walk_failure_policy_v1,
    build_substrate_traversal_retry_catalog_v1,
    build_walk_failure_explanation_v1,
    classify_walk_failure_v1,
    compute_retry_backoff_seconds_v1,
    get_traversal_retry_backoff_base_seconds_v1,
    run_traversal_retry_and_heal_pass_v1,
    schedule_traversal_retry_and_heal_pass_v1,
    should_retry_transient_failure_v1,
    verify_gp085_walk02_static,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_WALK_INCOMPLETE_V1,
)
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1


def _walk_record(
    *,
    status: str = "completed",
    termination_reason: str = "budget_exhausted",
    hops: int = 0,
    start_node_ids: list[str] | None = None,
) -> WalkApiRecordV1:
    wid = uuid.uuid4()
    tid = uuid.uuid4()
    hb: dict[str, Any] = {"termination_reason": termination_reason, "hop_receipts": [{}] * hops}
    payload = {
        "walk_result": {"hash_body": hb},
        "telemetry": {"hops_emitted": hops},
    }
    return WalkApiRecordV1(
        walk_id=wid,
        tenant_id=tid,
        status=status,  # type: ignore[arg-type]
        request_body={
            "start_node_ids": start_node_ids or ["node-a"],
            "walk_policy": {"max_hops": 4, "max_frontier": 8, "max_edges_visited": 16},
            "walk_execution_strategy": "ONLINE_OBSERVED",
        },
        walk_payload=payload,
        idempotency_key="test-idem",
    )


def test_traversal_retry_catalog() -> None:
    cat = build_substrate_traversal_retry_catalog_v1()
    assert cat["primary_gate_id"] == GP085_WALK02_GATE_ID_V1
    assert cat["pass_entrypoint"] == "run_traversal_retry_and_heal_pass_v1"
    assert RETRY_POLICY_BY_FAILURE_V1[FAILURE_WALK_INCOMPLETE_V1] == RETRY_ACTION_EXPLAIN_ONLY_V1


def test_verify_gp085_walk02_static_passes() -> None:
    assert verify_gp085_walk02_static()["passed"] is True
    assert verify_gp085_traversal_retry_gate_static()["passed"] is True


def test_celery_registers_traversal_retry_task() -> None:
    from app.tasks import cortex_substrate_traversal_retry  # noqa: F401

    assert CELERY_TRAVERSAL_RETRY_TASK_NAME_V1 in celery_app.tasks


def test_backoff_and_retry_limits() -> None:
    base = get_traversal_retry_backoff_base_seconds_v1()
    assert compute_retry_backoff_seconds_v1(1) == base
    assert compute_retry_backoff_seconds_v1(3) == base * 4
    assert should_retry_transient_failure_v1(attempt=1) is True
    assert should_retry_transient_failure_v1(attempt=3) is True
    assert should_retry_transient_failure_v1(attempt=4) is False


def test_classify_walk_failures() -> None:
    failed = _walk_record(status="failed")
    assert classify_walk_failure_v1(failed) == (FAILURE_TRANSIENT_STORE_V1, "walk_status_failed")

    incomplete = _walk_record(termination_reason="policy_rejected", hops=1)
    assert classify_walk_failure_v1(incomplete) == (
        FAILURE_WALK_INCOMPLETE_V1,
        "policy_rejected",
    )

    collapse = _walk_record(termination_reason="empty_frontier", hops=0)
    assert classify_walk_failure_v1(collapse) == (
        FAILURE_FRONTIER_COLLAPSE_V1,
        "empty_frontier_zero_hops",
    )

    ok = _walk_record(termination_reason="frontier_exhausted", hops=3)
    assert classify_walk_failure_v1(ok) == (None, "")


def test_walk_incomplete_explanation_only() -> None:
    rec = _walk_record(termination_reason="dangling_evidence", hops=2)
    session = MagicMock()
    out = apply_walk_failure_policy_v1(session, tenant_id=rec.tenant_id, record=rec)
    assert out["action"] == RETRY_ACTION_EXPLAIN_ONLY_V1
    assert out["explanation"]["ret_skip_code"] == RET_SKIP_WALK_INCOMPLETE_V1
    assert out["explanation"]["explained"] is True
    session.flush.assert_not_called()


def test_healed_walk_policy_multiplies_caps() -> None:
    healed = _healed_walk_policy_v1(
        {"max_hops": 4, "max_frontier": 8, "max_edges_visited": 16}
    )
    mult = 2  # default settings
    assert healed["max_hops"] == 4 * mult
    assert healed["max_frontier"] == 8 * mult
    assert healed["max_edges_visited"] == 16 * mult


def test_build_walk_failure_explanation_shape() -> None:
    wid = uuid.uuid4()
    exp = build_walk_failure_explanation_v1(
        walk_id=wid,
        failure_class=FAILURE_WALK_INCOMPLETE_V1,
        reason_code="policy_rejected",
        retry_action=RETRY_ACTION_EXPLAIN_ONLY_V1,
        ret_skip_code=RET_SKIP_WALK_INCOMPLETE_V1,
    )
    assert exp["gate_id"] == GP085_WALK02_GATE_ID_V1
    assert exp["walk_id"] == str(wid)


def test_schedule_traversal_retry_enqueues_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()

    class _FakeAsync:
        id = "retry-heal-task"

    monkeypatch.setattr(
        "app.tasks.cortex_substrate_traversal_retry.run_traversal_retry_and_heal_pass_task.apply_async",
        lambda **kwargs: _FakeAsync(),  # noqa: ARG005
    )
    out = schedule_traversal_retry_and_heal_pass_v1(tenant_id=tid)
    assert out["scheduled"] is True
    assert out["celery_task_id"] == "retry-heal-task"


@pytest.mark.integration
def test_run_traversal_retry_pass_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085retry-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Retry",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    out = run_traversal_retry_and_heal_pass_v1(db_session, tenant_id=row.id)
    assert out["gate_id"] == GP085_WALK02_GATE_ID_V1
    assert out["records_scanned"] == 0
