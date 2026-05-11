"""Notion page transform routing and deterministic lineage."""

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


def test_routing_registry_includes_notion_page_document() -> None:
    table = transform_routing_table()
    assert ("notion", "notion.page") in table
    kind, _rule = table[("notion", "notion.page")]
    assert kind == CanonicalObjectKind.DOCUMENT
    reg = registration_for_pair("notion", "notion.page")
    assert reg is not None
    assert reg.oracle_fixture_id == "p03_oracle_notion_page_v1"
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 2


def test_notion_page_document_lineage_and_key() -> None:
    tenant = uuid.uuid4()
    bundle_id = "bundle.phase03.step03.logical_keys.v1"
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.page",
        external_id="7f61cf4a-81cb-4a4e-9805-2df4f1b34567",
        source_identity_key="notion:notion.page:abc",
        source_revision_key="rev-001",
        payload_body={
            "page": {
                "id": "7f61cf4a-81cb-4a4e-9805-2df4f1b34567",
                "url": "https://www.notion.so/acme/Hello-1234/",
                "parent": {"type": "database_id", "database_id": "db-123"},
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Hello"}, {"plain_text": " World"}],
                    }
                },
            }
        },
    )
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.DOCUMENT,
        rule_base="rule.registry.notion.notion.page",
    )
    assert lk["tenant_id"] == str(tenant)
    assert lk["mapping_bundle_id"] == bundle_id
    assert lk["connector"] == "notion"
    assert lk["document_provider_id"] == "7f61cf4a-81cb-4a4e-9805-2df4f1b34567"
    assert emitted["source_url"] == "https://www.notion.so/acme/Hello-1234"
    assert emitted["parent_ref"] == "database_id:db-123"
    assert emitted["title"] == "Hello World"
    assert any(s.field_path == "logical_key" for s in specs)


def test_notion_page_requires_provider_id() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="notion",
        resource_type="notion.page",
        external_id="",
        source_identity_key="notion:notion.page:abc",
        source_revision_key="rev-001",
        payload_body={"page": {"url": "https://www.notion.so/x"}},
    )
    with pytest.raises(MaterializeError, match="document_missing_provider_id"):
        _build_lineage_specs(
            raw=raw,
            bundle_id="bundle.x",
            tenant_uuid=tenant,
            kind=CanonicalObjectKind.DOCUMENT,
            rule_base="rule.registry.notion.notion.page",
        )
