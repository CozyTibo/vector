"""GitHub canon mappers."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.canon.mapper_types import CanonEntityDraft, CanonMapResult
from vector.domains.cortex.canon.mappers._common import entity_key_for, label_from_payload, source_ref
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key


def _gh_user_ref(connector: str, user: dict[str, Any]) -> str | None:
    login = user.get("login")
    uid = user.get("id")
    ext = str(login or uid or "")
    if not ext:
        return None
    return derive_source_identity_key(connector=connector, resource_type="github.user", external_id=ext)


class _GitHubMapper:
    resource_type: str
    entity_type: str
    payload_key: str

    def __init__(self, resource_type: str, entity_type: str, payload_key: str) -> None:
        self.resource_type = resource_type
        self.entity_type = entity_type
        self.payload_key = payload_key

    def map_row(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        connector: str,
        resource_type: str,
        external_id: str,
        payload_body: dict[str, Any],
        raw_id: int,
        source_identity_key: str,
        source_revision_key: str,
        fetched_at_iso: str,
    ) -> CanonMapResult:
        src = source_ref(
            raw_id=raw_id,
            connector=connector,
            resource_type=resource_type,
            external_id=external_id,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            payload_body=payload_body,
            fetched_at_iso=fetched_at_iso,
        )
        key = entity_key_for(
            tenant_id=tenant_id,
            connector=connector,
            resource_type=resource_type,
            external_id=external_id,
        )
        segment = payload_body.get(self.payload_key)
        label = label_from_payload(payload_body, self.payload_key)
        attrs: dict[str, Any] = {"external_id": external_id}
        draft = CanonEntityDraft(
            entity_type=self.entity_type,
            entity_key=key,
            display_label=label,
            connector=connector,
            connection_id=connection_id,
            attrs_json=attrs,
        )
        if isinstance(segment, dict):
            if self.entity_type == "pull_request":
                attrs["number"] = segment.get("number")
                attrs["state"] = segment.get("state")
                user = segment.get("user")
                if isinstance(user, dict):
                    draft.author_ref = _gh_user_ref(connector, user)
                head = segment.get("head")
                if isinstance(head, dict):
                    repo = head.get("repo") or segment.get("base", {}).get("repo")
                    if isinstance(repo, dict):
                        fn = repo.get("full_name")
                        if isinstance(fn, str):
                            draft.repository_ref = derive_source_identity_key(
                                connector=connector,
                                resource_type="github.repository",
                                external_id=fn,
                            )
            elif self.entity_type == "work_item":
                attrs["number"] = segment.get("number")
                attrs["state"] = segment.get("state")
                creator = segment.get("user") or segment.get("creator")
                if isinstance(creator, dict):
                    draft.author_ref = _gh_user_ref(connector, creator)
                assignee = segment.get("assignee")
                if isinstance(assignee, dict):
                    draft.assignee_ref = _gh_user_ref(connector, assignee)
                repo = segment.get("repository")
                if isinstance(repo, dict):
                    fn = repo.get("full_name")
                    if isinstance(fn, str) and fn.strip():
                        draft.repository_ref = derive_source_identity_key(
                            connector=connector,
                            resource_type="github.repository",
                            external_id=fn.strip(),
                        )
            elif self.entity_type == "commit":
                attrs["sha"] = segment.get("sha")
            elif self.entity_type == "message":
                user = segment.get("user")
                if isinstance(user, dict):
                    draft.author_ref = _gh_user_ref(connector, user)
                if resource_type in (
                    "github.issue_comment",
                    "github.pull_request_review_comment",
                    "github.pull_request_review",
                ):
                    pr_ext = external_id
                    for marker in ("issue_comment", "review_comment", "review"):
                        token = f":{marker}:"
                        if token in external_id:
                            pr_ext = external_id.split(token)[0]
                            break
                    draft.work_item_ref = derive_source_identity_key(
                        connector=connector,
                        resource_type="github.pull_request",
                        external_id=pr_ext[:512],
                    )
            elif self.entity_type == "actor":
                attrs["login"] = segment.get("login")
            elif self.entity_type == "project":
                attrs["full_name"] = segment.get("full_name") or segment.get("name")
            elif self.entity_type in ("deployment", "release"):
                attrs["state"] = segment.get("state") or segment.get("status")
        return CanonMapResult(draft=draft, source=src)


GITHUB_MAPPERS: list[_GitHubMapper] = [
    _GitHubMapper("github.user", "actor", "member"),
    _GitHubMapper("github.repository", "project", "repository"),
    _GitHubMapper("github.pull_request", "pull_request", "pull_request"),
    _GitHubMapper("github.issue", "work_item", "issue"),
    _GitHubMapper("github.commit", "commit", "commit"),
    _GitHubMapper("github.pull_request_review", "message", "review"),
    _GitHubMapper("github.pull_request_review_comment", "message", "comment"),
    _GitHubMapper("github.issue_comment", "message", "comment"),
    _GitHubMapper("github.commit_comment", "message", "comment"),
    _GitHubMapper("github.review_thread", "conversation", "review_thread"),
    _GitHubMapper("github.workflow_run", "deployment", "workflow_run"),
    _GitHubMapper("github.deployment", "deployment", "deployment"),
    _GitHubMapper("github.release", "release", "release"),
    _GitHubMapper("commits", "commit", "commit"),
]
