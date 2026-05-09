"""Phase 3.5 continuity contracts — determinism and shape tests."""

from __future__ import annotations

import uuid

from vector.domains.cortex.continuity.bundle_continuity_semantics import (
    continuity_scope_for_materialization,
    continuity_scope_for_normalized_reference,
    validate_edge_bundle_alignment,
)
from vector.domains.cortex.continuity.edge_contracts import ContinuityEdgeKind, build_edge_contract
from vector.domains.cortex.continuity.execution_primitives import ExecutionPrimitiveKind, build_execution_primitive_envelope
from vector.domains.cortex.continuity.public_document import CONTINUITY_FOUNDATION_SCHEMA_VERSION, build_phase35_continuity_public_document
from vector.domains.cortex.continuity.reference_emitter import emit_github_workflow_run_references
from vector.domains.cortex.continuity.reference_normalize import (
    normalize_git_commit_sha,
    normalize_git_repository_full_name,
    normalize_github_pull_request_ref,
)
from vector.domains.cortex.continuity.temporal_continuity import normalize_provider_timestamp, partial_order_tuple


def test_normalize_repository_deterministic() -> None:
    a = normalize_git_repository_full_name("Acme/WIDGET")
    b = normalize_git_repository_full_name("Acme/WIDGET")
    assert a == b
    assert a["status"] == "ok"
    assert a["canonical_form"] == "git.repo:Acme/WIDGET"


def test_normalize_commit_full_vs_prefix() -> None:
    full = normalize_git_commit_sha("a" * 40)
    assert full["status"] == "ok"
    assert full["canonical_form"] == f"git.commit:{'a' * 40}"
    short = normalize_git_commit_sha("abcdef0")
    assert short["status"] == "partial"
    assert "prefix" in short["canonical_form"]


def test_normalize_pr_ref() -> None:
    r = normalize_github_pull_request_ref("acme/vec", 12)
    assert r["status"] == "ok"
    assert r["canonical_form"] == "github.pr:acme/vec#12"


def test_emit_workflow_run_references_includes_repo_and_run() -> None:
    payload = {
        "workflow_run": {
            "id": 55,
            "head_sha": "a" * 40,
            "repository": {"full_name": "acme/vec", "id": 1},
        }
    }
    refs = emit_github_workflow_run_references(payload)
    forms = {x["canonical_form"] for x in refs if x.get("canonical_form")}
    assert "github.workflow_run:acme/vec:55" in forms
    assert "git.repo:acme/vec" in forms
    assert f"git.commit:{'a' * 40}" in forms


def test_edge_contract_roundtrip() -> None:
    e = build_edge_contract(
        kind=ContinuityEdgeKind.WORKFLOW_RUN_ON_REPOSITORY,
        source={
            "normalized_reference": {
                "reference_contract_version": 1,
                "family": "github.workflow_run",
                "status": "ok",
                "canonical_form": "github.workflow_run:acme/vec:9",
                "components": {},
                "source_paths": [],
            }
        },
        target={
            "normalized_reference": {
                "reference_contract_version": 1,
                "family": "git.repository",
                "status": "ok",
                "canonical_form": "git.repo:acme/vec",
                "components": {},
                "source_paths": [],
            }
        },
        confidence_class="E0",
        evidence_rule_id="rule.phase35.workflow_run_on_repository.v1",
        bundle_id="bundle.phase03.stub",
        tenant_id=str(uuid.uuid4()),
    )
    assert e["edge_kind"] == ContinuityEdgeKind.WORKFLOW_RUN_ON_REPOSITORY.value


def test_primitive_key_stable() -> None:
    t = uuid.uuid4()
    a = build_execution_primitive_envelope(
        kind=ExecutionPrimitiveKind.WORK_EPISODE,
        evidence_parts={"a": 1, "b": "x"},
        evidence_raw_record_ids=[10, 11],
        bundle_id="b1",
        tenant_id=str(t),
    )
    b = build_execution_primitive_envelope(
        kind=ExecutionPrimitiveKind.WORK_EPISODE,
        evidence_parts={"b": "x", "a": 1},
        evidence_raw_record_ids=[10, 11],
        bundle_id="b1",
        tenant_id=str(t),
    )
    assert a["primitive_key"] == b["primitive_key"]


def test_bundle_scope_docs() -> None:
    assert continuity_scope_for_materialization(bundle_id="b")["scope_kind"] == "bundle_scoped"
    assert continuity_scope_for_normalized_reference()["scope_kind"] == "reference_plane"


def test_validate_cross_bundle_warning() -> None:
    w = validate_edge_bundle_alignment(
        edge_bundle_id="b1",
        source_scope={"canonical_pointer": {"bundle_id": "b1"}},
        target_scope={"canonical_pointer": {"bundle_id": "b2"}},
    )
    assert "cross_bundle" in w[0]


def test_temporal_parse_and_partial_order() -> None:
    dt, st = normalize_provider_timestamp("2026-01-02T03:04:05Z")
    assert st == "ok"
    assert dt is not None
    t = partial_order_tuple(
        occurred_at=dt,
        observed_at=dt,
        replay_sequence=1,
        source_revision_key="r",
        raw_record_id=99,
    )
    assert len(t) == 5


def test_public_document() -> None:
    doc = build_phase35_continuity_public_document()
    assert doc["continuity_foundation_schema_version"] == CONTINUITY_FOUNDATION_SCHEMA_VERSION
    assert "workflow_run_on_repository" in doc["continuity_edge_kinds"]
