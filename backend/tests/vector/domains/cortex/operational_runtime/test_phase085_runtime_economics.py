"""P085-33 — Runtime economics / queue pressure (**G-P085-ECON-01**)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_runtime_economics_gate import (
    verify_gp085_runtime_economics_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
    GP085_ECON01_GATE_ID_V1,
    OPERATIONAL_OMISSION_SD_UPSTREAM_CAP_V1,
    build_runtime_economics_knobs_v1,
    build_substrate_runtime_economics_catalog_v1,
    build_upstream_cap_omission_v1,
    evaluate_vector_queue_backpressure_v1,
    resolve_post_ingestion_debounce_countdown_v1,
    verify_gp085_econ01_static,
)


def test_gp085_econ01_static_gate() -> None:
    out = verify_gp085_econ01_static()
    assert out["passed"] is True
    assert out["id"] == GP085_ECON01_GATE_ID_V1
    assert verify_gp085_runtime_economics_gate_static()["passed"] is True


def test_economics_catalog() -> None:
    cat = build_substrate_runtime_economics_catalog_v1()
    assert cat["primary_gate_id"] == GP085_ECON01_GATE_ID_V1
    assert cat["omission_class_upstream_cap"] == OPERATIONAL_OMISSION_SD_UPSTREAM_CAP_V1


def test_knobs_include_doctrine_keys() -> None:
    knobs = build_runtime_economics_knobs_v1()
    assert knobs["CORTEX_SUBSTRATE_PIPELINE_MAX_CONCURRENT_PER_TENANT"] == 1
    assert knobs["CORTEX_SYNTHESIS_PIPELINE_MAX_SCOPES"] == 32


def test_upstream_cap_omission_shape() -> None:
    om = build_upstream_cap_omission_v1(cap_kind="test", detail="capped")
    assert om["omission_class"] == OPERATIONAL_OMISSION_SD_UPSTREAM_CAP_V1


def test_backpressure_extends_debounce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_DEBOUNCE_SECONDS", "120")
    monkeypatch.setenv("CORTEX_VECTOR_QUEUE_BACKPRESSURE_THRESHOLD", "10")
    monkeypatch.setenv("CORTEX_POST_INGESTION_BACKPRESSURE_EXTRA_DEBOUNCE_SECONDS", "180")

    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setattr(
            "vector.domains.cortex.operational_runtime.substrate_runtime_economics."
            "measure_vector_queue_depth_v1",
            lambda **_k: {"depth": 99, "queue_name": "vector"},
        )
        resolved = resolve_post_ingestion_debounce_countdown_v1()
        assert resolved["base_debounce_seconds"] == 120
        assert resolved["extra_debounce_seconds"] == 180
        assert resolved["effective_countdown_seconds"] == 300
        assert resolved["backpressure"]["backpressure_active"] is True
    finally:
        get_settings.cache_clear()


def test_backpressure_inactive_debounce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_DEBOUNCE_SECONDS", "120")
    monkeypatch.setenv("CORTEX_VECTOR_QUEUE_BACKPRESSURE_THRESHOLD", "1000")

    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setattr(
            "vector.domains.cortex.operational_runtime.substrate_runtime_economics."
            "measure_vector_queue_depth_v1",
            lambda **_k: {"depth": 2, "queue_name": "vector"},
        )
        resolved = resolve_post_ingestion_debounce_countdown_v1()
        assert resolved["effective_countdown_seconds"] == 120
        assert resolved["extra_debounce_seconds"] == 0
    finally:
        get_settings.cache_clear()


@pytest.mark.integration
def test_pipeline_concurrency_empty_tenant(db_session: Session) -> None:
    from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
        evaluate_pipeline_concurrency_v1,
    )
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085econ-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 ECON",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    out = evaluate_pipeline_concurrency_v1(db_session, tenant_id=tenant.id)
    assert out["may_start_pipeline"] is True
    assert out["running_pipeline_count"] == 0


def test_schedule_pipeline_respects_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import contextmanager

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")

    from vector.settings import get_settings

    @contextmanager
    def _fake_scope() -> MagicMock:
        yield MagicMock()

    get_settings.cache_clear()
    try:
        monkeypatch.setattr(
            "vector.domains.cortex.substrate_pipeline.orchestrator.session_scope",
            _fake_scope,
        )
        monkeypatch.setattr(
            "vector.domains.cortex.operational_runtime.substrate_runtime_economics."
            "evaluate_pipeline_concurrency_v1",
            lambda *_a, **_k: {
                "may_start_pipeline": False,
                "block_reason": "max_concurrent_pipelines_per_tenant",
            },
        )
        from vector.domains.cortex.substrate_pipeline.orchestrator import (
            schedule_substrate_pipeline_v1,
        )

        out = schedule_substrate_pipeline_v1(tenant_id=uuid.uuid4())
        assert out["scheduled"] is False
        assert out["reason"] == "max_concurrent_pipelines_per_tenant"
    finally:
        get_settings.cache_clear()
