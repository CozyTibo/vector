"""Execution-surface routing and lineage coverage smoke tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.transform_routing_registry import (
    TRANSFORM_ROUTING_REGISTRY_VERSION,
    transform_routing_table,
)
from vector.domains.cortex.canonical.transform_runtime import _build_lineage_specs


def test_routing_registry_includes_execution_surface_pairs() -> None:
    table = transform_routing_table()
    assert TRANSFORM_ROUTING_REGISTRY_VERSION >= 10
    assert table[("github", "github.workflow_run")][0] == CanonicalObjectKind.WORKFLOW_RUN
    assert table[("github", "github.deployment")][0] == CanonicalObjectKind.DEPLOYMENT
    assert table[("github", "github.deployment_status")][0] == CanonicalObjectKind.TIMELINE_MUTATION
    assert table[("calls", "calls.transcript")][0] == CanonicalObjectKind.TRANSCRIPT
    assert table[("calls", "calls.participant")][0] == CanonicalObjectKind.PERSON
    assert table[("slack", "slack.file")][0] == CanonicalObjectKind.DOCUMENT
    assert table[("linear", "linear.activity_history")][0] == CanonicalObjectKind.CANONICAL_EVENT


def test_workflow_run_logical_key_and_identity_lineage() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.workflow_run",
        external_id="acme/widget:workflow_run:55",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "workflow_run": {
                "id": 55,
                "status": "completed",
                "conclusion": "success",
                "head_sha": "sha55",
                "head_branch": "main",
                "actor": {"id": 9001},
                "repository": {"id": 88424},
            }
        },
    )
    lk, emitted, _specs = _build_lineage_specs(
        raw=raw,
        bundle_id="bundle.phase03.step03.logical_keys.v1",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.WORKFLOW_RUN,
        rule_base="rule.registry.github.github.workflow_run",
    )
    assert lk["repository_provider_id"] == "88424"
    assert lk["workflow_run_provider_id"] == "55"
    assert emitted["status"] == "completed"
    assert emitted["head_sha"] == "sha55"


def test_workflow_run_repository_inferred_from_external_id_when_payload_omits_repo() -> None:
    """Older ingested rows may lack ``repository`` on workflow_run; external_id matches sync_executor shape."""
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.workflow_run",
        external_id="acme/widget:workflow_run:55",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "workflow_run": {
                "id": 55,
                "status": "completed",
                "conclusion": "success",
                "head_sha": "sha55",
                "head_branch": "main",
            }
        },
    )
    lk, _emitted, _specs = _build_lineage_specs(
        raw=raw,
        bundle_id="bundle.phase03.step03.logical_keys.v1",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.WORKFLOW_RUN,
        rule_base="rule.registry.github.github.workflow_run",
    )
    assert lk["repository_provider_id"] == "acme/widget"
    assert lk["workflow_run_provider_id"] == "55"


def test_deployment_and_transcript_keys_are_deterministic() -> None:
    tenant = uuid.uuid4()
    dep = SimpleNamespace(
        connector="github",
        resource_type="github.deployment",
        external_id="88424:deployment:71",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "deployment": {
                "id": 71,
                "environment": "production",
                "sha": "abc",
                "repository": {"id": 88424},
            }
        },
    )
    dep_lk, dep_emitted, _ = _build_lineage_specs(
        raw=dep,
        bundle_id="bundle.phase03.step03.logical_keys.v1",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.DEPLOYMENT,
        rule_base="rule.registry.github.github.deployment",
    )
    assert dep_lk["repository_provider_id"] == "88424"
    assert dep_lk["deployment_provider_id"] == "71"
    assert dep_emitted["environment"] == "production"

    tr = SimpleNamespace(
        connector="calls",
        resource_type="calls.transcript",
        external_id="mtg-1:transcript:main",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={"transcript_record": {"meeting_id": "mtg-1", "transcript_id": "main", "segment_count": 42}},
    )
    tr_lk, tr_emitted, _ = _build_lineage_specs(
        raw=tr,
        bundle_id="bundle.phase03.step03.logical_keys.v1",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.TRANSCRIPT,
        rule_base="rule.registry.calls.calls.transcript",
    )
    assert tr_lk["meeting_provider_id"] == "mtg-1"
    assert tr_lk["transcript_provider_id"] == "main"
    assert tr_emitted["segment_count"] == 42


def test_mock_github_workflow_run_payload_includes_repository() -> None:
    """Regression: workflow_run materialization requires ``repository`` (matches GitHub REST + transform_runtime)."""
    from mock_connectors.github_mock import dataset_generator as gh_gen

    gh = {
        "repos": [{"full_name": "acme/vector", "id": 42, "name": "vector"}],
        "commits": [
            {
                "_repo": "acme/vector",
                "sha": "deadbeefcafe",
                "commit": {
                    "author": {"date": "2026-01-01T00:00:00Z"},
                    "committer": {"date": "2026-01-01T00:00:01Z"},
                },
            }
        ],
    }
    rows, _ = gh_gen.workflow_runs_for_repo_with_total(gh, "acme", "vector", page=1, per_page=10)
    assert rows
    repo = rows[0].get("repository")
    assert isinstance(repo, dict)
    assert repo.get("id") == 42
    assert repo.get("full_name") == "acme/vector"
