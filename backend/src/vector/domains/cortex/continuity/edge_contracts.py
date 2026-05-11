"""Graph-ready continuity edge contracts (Phase 3.5) — schema only, no graph database.

Edges are **evidence-bound**: every edge record is expected to cite raw and/or canonical provenance in Phase 04+.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, TypedDict

CONTINUITY_EDGE_CONTRACT_VERSION: int = 1


class ContinuityEdgeKind(StrEnum):
    """Normalized cross-tool edge labels (deterministic join semantics, not ML)."""

    PR_LINKS_ISSUE = "pr_links_issue"
    ISSUE_IN_PROJECT = "issue_in_project"
    DEPLOYMENT_FOR_WORKFLOW = "deployment_for_workflow"
    WORKFLOW_IN_REPOSITORY = "workflow_in_repository"
    REVIEW_BY_ACTOR = "review_by_actor"
    MESSAGE_IN_THREAD = "message_in_thread"
    THREAD_ESCALATES_TO = "thread_escalates_to"
    COMMIT_DEPLOYED_BY = "commit_deployed_by"
    ACTOR_OWNS = "actor_owns"
    ISSUE_BLOCKS_ISSUE = "issue_blocks_issue"
    DEPLOYMENT_DURING_INCIDENT = "deployment_during_incident"
    CHECK_RUN_ON_COMMIT = "check_run_on_commit"
    WORKFLOW_RUN_ON_REPOSITORY = "workflow_run_on_repository"


EdgeConfidenceClass = Literal["E0", "E1", "E2"]


class ContinuityEdgeEndpoint(TypedDict, total=False):
    """Endpoint is either a normalized reference or a bundle-scoped canonical pointer (future persistence)."""

    normalized_reference: dict[str, Any]
    """``NormalizedReference`` JSON."""
    canonical_pointer: dict[str, Any]
    """``{bundle_id, canonical_object_kind, logical_key_hash}`` when materialization-backed."""
    raw_record_id: int
    """Primary raw evidence row when edge is raw-anchored only."""


class ContinuityEdgeContract(TypedDict, total=False):
    """Deterministic edge envelope for future graph projection."""

    continuity_edge_contract_version: int
    edge_kind: str
    directed: bool
    source: ContinuityEdgeEndpoint
    target: ContinuityEdgeEndpoint
    confidence_class: EdgeConfidenceClass
    evidence_rule_id: str
    """Stable id for the deterministic rule that emitted this edge (lineage-style)."""
    temporal_anchor_iso: str | None
    """Optional occurred/observed instant for ordering (UTC ISO)."""
    bundle_id: str
    """Bundle scope for canonical endpoints; may be empty when raw-only."""
    tenant_id: str


def allowed_endpoint_pairs(kind: ContinuityEdgeKind) -> tuple[str, str]:
    """Return (source_reference_family_glob, target_reference_family_glob) hints for validation."""
    # Glob here means loose family prefix expectations for static checks.
    hints: dict[ContinuityEdgeKind, tuple[str, str]] = {
        ContinuityEdgeKind.PR_LINKS_ISSUE: ("github.pull_request", "github.issue"),
        ContinuityEdgeKind.ISSUE_IN_PROJECT: ("github.issue|linear.issue", "linear.project|github.project"),
        ContinuityEdgeKind.DEPLOYMENT_FOR_WORKFLOW: ("github.deployment", "github.workflow_run"),
        ContinuityEdgeKind.WORKFLOW_IN_REPOSITORY: ("github.workflow_run", "git.repository"),
        ContinuityEdgeKind.REVIEW_BY_ACTOR: ("github.pull_request_review|github.review", "email.address|opaque.external"),
        ContinuityEdgeKind.MESSAGE_IN_THREAD: ("slack.message", "slack.thread"),
        ContinuityEdgeKind.THREAD_ESCALATES_TO: ("slack.thread", "slack.thread|slack.message"),
        ContinuityEdgeKind.COMMIT_DEPLOYED_BY: ("git.commit", "github.deployment"),
        ContinuityEdgeKind.ACTOR_OWNS: ("opaque.external|email.address", "git.repository|linear.issue"),
        ContinuityEdgeKind.ISSUE_BLOCKS_ISSUE: ("github.issue|linear.issue", "github.issue|linear.issue"),
        ContinuityEdgeKind.DEPLOYMENT_DURING_INCIDENT: ("github.deployment", "opaque.external"),
        ContinuityEdgeKind.CHECK_RUN_ON_COMMIT: ("github.check_run", "git.commit"),
        ContinuityEdgeKind.WORKFLOW_RUN_ON_REPOSITORY: ("github.workflow_run", "git.repository"),
    }
    return hints.get(kind, ("*", "*"))


def build_edge_contract(
    *,
    kind: ContinuityEdgeKind,
    source: ContinuityEdgeEndpoint,
    target: ContinuityEdgeEndpoint,
    confidence_class: EdgeConfidenceClass,
    evidence_rule_id: str,
    bundle_id: str,
    tenant_id: str,
    directed: bool = True,
    temporal_anchor_iso: str | None = None,
) -> ContinuityEdgeContract:
    return {
        "continuity_edge_contract_version": CONTINUITY_EDGE_CONTRACT_VERSION,
        "edge_kind": kind.value,
        "directed": directed,
        "source": source,
        "target": target,
        "confidence_class": confidence_class,
        "evidence_rule_id": evidence_rule_id,
        "temporal_anchor_iso": temporal_anchor_iso,
        "bundle_id": bundle_id,
        "tenant_id": tenant_id,
    }
