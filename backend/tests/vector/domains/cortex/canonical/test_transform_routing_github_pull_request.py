"""GitHub pull_request transform — aligned with sync_executor payload shape."""

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


def test_routing_registry_includes_github_pull_request() -> None:
    table = transform_routing_table()
    assert ("github", "github.pull_request") in table
    kind, rule = table[("github", "github.pull_request")]
    assert kind == CanonicalObjectKind.PULL_REQUEST
    assert "github.pull_request" in rule
    reg = registration_for_pair("github", "github.pull_request")
    assert reg is not None
    assert reg.oracle_fixture_id == "p03_oracle_github_pull_request_v1"
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 2


def test_pull_request_lineage_and_logical_key() -> None:
    tenant = uuid.uuid4()
    bundle_id = "bundle.phase03.step03.logical_keys.v1"
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.pull_request",
        external_id="acme/widget#7",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "pull_request": {
                "number": 7,
                "title": "Add feature",
                "base": {"repo": {"id": 88424, "full_name": "acme/widget"}},
            }
        },
    )
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.PULL_REQUEST,
        rule_base="rule.registry.github.github.pull_request",
    )
    assert lk["tenant_id"] == str(tenant)
    assert lk["mapping_bundle_id"] == bundle_id
    assert lk["connector"] == "github"
    assert lk["repository_provider_id"] == "88424"
    assert lk["pull_request_discriminant"] == "7"
    assert emitted.get("title") == "Add feature"
    assert any(s.field_path == "logical_key" for s in specs)


def test_pull_request_requires_repo_identity() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.pull_request",
        external_id="x",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={"pull_request": {"number": 1, "base": {"repo": {}}}},
    )
    with pytest.raises(MaterializeError, match="pull_request_missing_repository_provider_id"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.PULL_REQUEST,
            rule_base="rule.x",
        )
