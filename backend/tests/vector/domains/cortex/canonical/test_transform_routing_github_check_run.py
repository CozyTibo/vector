"""GitHub check_run transform as first-class EXECUTION_CHECK."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.transform_routing_registry import (
    TRANSFORM_ROUTING_REGISTRY_VERSION,
    registration_for_pair,
    transform_routing_table,
)
from vector.domains.cortex.canonical.transform_runtime import (
    MaterializeError,
    _build_lineage_specs,
)


def _raw_check_run_payload(*, status: str = "completed", workflow_name: str = "ci") -> SimpleNamespace:
    return SimpleNamespace(
        connector="github",
        resource_type="github.check_run",
        external_id="acme/widget:sha-123:check:981",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "pull_request_number": 17,
            "head_sha": "sha-123",
            "check_run": {
                "id": 981,
                "name": workflow_name,
                "status": status,
                "conclusion": "success" if status == "completed" else None,
                "started_at": "2026-05-09T08:00:00Z",
                "completed_at": "2026-05-09T08:00:03Z" if status == "completed" else None,
                "app": {"id": 44},
                "check_suite": {"id": 551},
                "details_url": "https://github.com/acme/widget/actions/runs/551",
                "html_url": "https://github.com/acme/widget/runs/981",
            },
        },
    )


def test_routing_registry_includes_github_check_run() -> None:
    table = transform_routing_table()
    assert ("github", "github.check_run") in table
    kind, rule = table[("github", "github.check_run")]
    assert kind == CanonicalObjectKind.EXECUTION_CHECK
    assert "github.check_run" in rule
    reg = registration_for_pair("github", "github.check_run")
    assert reg is not None
    assert reg.oracle_fixture_id is None
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 7


def test_check_run_lineage_and_logical_key_deterministic() -> None:
    tenant = uuid.uuid4()
    bundle_id = "bundle.phase03.step03.logical_keys.v1"
    raw = _raw_check_run_payload()
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.EXECUTION_CHECK,
        rule_base="rule.registry.github.github.check_run",
    )
    assert lk == {
        "tenant_id": str(tenant),
        "mapping_bundle_id": bundle_id,
        "connector": "github",
        "repository_provider_id": "acme/widget",
        "check_run_provider_id": "981",
    }
    assert emitted["status"] == "completed"
    assert emitted["conclusion"] == "success"
    assert emitted["duration_ms"] == 3000
    assert emitted["commit_sha"] == "sha-123"
    assert emitted["workflow_run_ref"] == "551"
    assert emitted["pull_request_refs"] == ["17"]
    assert any(s.field_path == "logical_key" for s in specs)


def test_check_run_logical_key_survives_workflow_name_changes() -> None:
    tenant = uuid.uuid4()
    raw_a = _raw_check_run_payload(workflow_name="ci-main")
    raw_b = _raw_check_run_payload(workflow_name="ci-renamed")
    lk_a, _, _ = _build_lineage_specs(
        raw=raw_a,
        bundle_id="bundle.x",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.EXECUTION_CHECK,
        rule_base="rule.registry.github.github.check_run",
    )
    lk_b, _, _ = _build_lineage_specs(
        raw=raw_b,
        bundle_id="bundle.x",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.EXECUTION_CHECK,
        rule_base="rule.registry.github.github.check_run",
    )
    assert lk_a == lk_b


def test_check_run_missing_repository_fails() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.check_run",
        external_id="check:981",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={"check_run": {"id": 981, "status": "queued"}},
    )
    with pytest.raises(MaterializeError, match="execution_check_missing_repository_provider_id"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.EXECUTION_CHECK,
            rule_base="rule.registry.github.github.check_run",
        )


def test_check_run_malformed_payload_fails() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.check_run",
        external_id="acme/widget:sha:check:1",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={"check_run": "bad-shape"},
    )
    with pytest.raises(MaterializeError, match="execution_check_payload_not_object"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.EXECUTION_CHECK,
            rule_base="rule.registry.github.github.check_run",
        )


def test_check_run_conclusion_status_pairing_enforced() -> None:
    tenant = uuid.uuid4()
    raw = _raw_check_run_payload(status="in_progress")
    raw.payload_body["check_run"]["conclusion"] = "success"
    with pytest.raises(MaterializeError, match="execution_check_conclusion_without_completed_status"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.EXECUTION_CHECK,
            rule_base="rule.registry.github.github.check_run",
        )
