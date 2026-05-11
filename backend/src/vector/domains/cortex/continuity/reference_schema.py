"""Normalized cross-tool reference schema (Phase 3.5).

References are **not** identities: they are deterministic handles derived from provider-visible fields.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, TypedDict


REFERENCE_CONTRACT_VERSION: int = 1


class ReferenceFamily(StrEnum):
    """Stable family ids for normalized references (versioned separately from ontology kinds)."""

    GIT_REPOSITORY = "git.repository"
    GIT_COMMIT = "git.commit"
    GIT_BRANCH = "git.branch"
    GIT_TAG = "git.tag"
    GITHUB_PULL_REQUEST = "github.pull_request"
    GITHUB_ISSUE = "github.issue"
    GITHUB_WORKFLOW_RUN = "github.workflow_run"
    GITHUB_DEPLOYMENT = "github.deployment"
    GITHUB_CHECK_RUN = "github.check_run"
    LINEAR_ISSUE = "linear.issue"
    LINEAR_PROJECT = "linear.project"
    NOTION_PAGE = "notion.page"
    NOTION_DATABASE = "notion.database"
    SLACK_CONVERSATION = "slack.conversation"
    SLACK_MESSAGE = "slack.message"
    SLACK_THREAD = "slack.thread"
    URL_HTTP = "url.http"
    EMAIL_ADDRESS = "email.address"
    OPAQUE_EXTERNAL = "opaque.external"


NormalizationStatus = Literal["ok", "unknown", "invalid", "partial"]


class NormalizedReference(TypedDict, total=False):
    """JSON-serializable normalized reference envelope."""

    reference_contract_version: int
    family: str
    status: NormalizationStatus
    """ok = fully normalized; partial = shortened or lossy but explicit; unknown = no signal; invalid = contradicted input."""
    canonical_form: str
    """Single deterministic string for sorting/join keys when status is ok or partial."""
    components: dict[str, Any]
    """Structured fields (e.g. owner, repo, number) for Phase 04 join logic."""
    source_paths: list[str]
    """Dot paths or column names in raw payload used to derive this reference (provenance hints)."""


def empty_reference(
    *,
    family: str,
    status: NormalizationStatus = "unknown",
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": family,
        "status": status,
        "canonical_form": "",
        "components": {},
        "source_paths": list(source_paths or []),
    }
