"""Linear canon mappers."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.canon.mapper_types import CanonEntityDraft, CanonMapResult
from vector.domains.cortex.canon.mappers._common import entity_key_for, label_from_payload, source_ref
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key


def _linear_user_ref(connector: str, user: dict[str, Any]) -> str | None:
    uid = user.get("id")
    if not isinstance(uid, str) or not uid:
        return None
    return derive_source_identity_key(connector=connector, resource_type="linear.user", external_id=uid)


def _linear_ref(connector: str, resource_type: str, id_val: object) -> str | None:
    if isinstance(id_val, str) and id_val.strip():
        return derive_source_identity_key(
            connector=connector,
            resource_type=resource_type,
            external_id=id_val.strip(),
        )
    return None


def _segment(payload_body: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        segment = payload_body.get(key)
        if isinstance(segment, dict):
            return segment
    return None


class _LinearMapper:
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
        segment = _segment(payload_body, self.payload_key) or {}
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
        if self.entity_type == "work_item":
            attrs["identifier"] = segment.get("identifier")
            state = segment.get("state")
            if isinstance(state, dict):
                attrs["state"] = state.get("name")
            elif state is not None:
                attrs["state"] = state
            creator = segment.get("creator")
            if isinstance(creator, dict):
                draft.author_ref = _linear_user_ref(connector, creator)
            assignee = segment.get("assignee")
            if isinstance(assignee, dict):
                draft.assignee_ref = _linear_user_ref(connector, assignee)
            team = segment.get("team")
            if isinstance(team, dict):
                tid = team.get("id")
                if isinstance(tid, str):
                    attrs["team_id"] = tid
                    attrs["team_key"] = team.get("key")
            cycle = segment.get("cycle")
            if isinstance(cycle, dict) and isinstance(cycle.get("id"), str):
                attrs["cycle_id"] = cycle["id"]
            project = segment.get("project")
            if isinstance(project, dict) and isinstance(project.get("id"), str):
                attrs["project_id"] = project["id"]
            labels = segment.get("labels")
            label_nodes = labels.get("nodes") if isinstance(labels, dict) else None
            if isinstance(label_nodes, list):
                attrs["label_ids"] = [
                    n.get("id") for n in label_nodes if isinstance(n, dict) and isinstance(n.get("id"), str)
                ]
        elif self.entity_type == "message":
            user = segment.get("user")
            if isinstance(user, dict):
                draft.author_ref = _linear_user_ref(connector, user)
            issue_id = payload_body.get("issue_id")
            if isinstance(issue_id, str):
                draft.work_item_ref = _linear_ref(connector, "linear.issue", issue_id)
            issue = segment.get("issue")
            if isinstance(issue, dict) and isinstance(issue.get("id"), str):
                draft.work_item_ref = _linear_ref(connector, "linear.issue", issue["id"])
        elif self.entity_type == "actor":
            attrs["name"] = segment.get("name")
            attrs["email"] = segment.get("email")
        elif self.entity_type == "project":
            attrs["name"] = segment.get("name")
            attrs["slug"] = segment.get("slug")
            attrs["state"] = segment.get("state")
            team = segment.get("team")
            if isinstance(team, dict) and isinstance(team.get("id"), str):
                attrs["team_id"] = team["id"]
        elif self.entity_type == "team":
            attrs["name"] = segment.get("name")
            attrs["key"] = segment.get("key")
            attrs["description"] = segment.get("description")
            attrs["private"] = segment.get("private")
        elif self.entity_type == "cycle":
            attrs["name"] = segment.get("name")
            attrs["number"] = segment.get("number")
            attrs["starts_at"] = segment.get("startsAt")
            attrs["ends_at"] = segment.get("endsAt")
            attrs["completed_at"] = segment.get("completedAt")
            attrs["progress"] = segment.get("progress")
            team = segment.get("team")
            if isinstance(team, dict) and isinstance(team.get("id"), str):
                attrs["team_id"] = team["id"]
        elif self.entity_type == "label":
            attrs["name"] = segment.get("name")
            attrs["color"] = segment.get("color")
            team = segment.get("team")
            if isinstance(team, dict) and isinstance(team.get("id"), str):
                attrs["team_id"] = team["id"]
        elif self.entity_type == "initiative":
            attrs["name"] = segment.get("name")
            attrs["description"] = segment.get("description")
        elif self.entity_type == "issue_relation":
            rel_type = segment.get("type")
            if rel_type is not None:
                attrs["relation_type"] = rel_type
            issue = segment.get("issue")
            related = segment.get("relatedIssue")
            if isinstance(issue, dict):
                iid = issue.get("id")
                if isinstance(iid, str):
                    attrs["issue_id"] = iid
                    draft.work_item_ref = _linear_ref(connector, "linear.issue", iid)
                ident = issue.get("identifier")
                if isinstance(ident, str):
                    attrs["issue_identifier"] = ident
            if isinstance(related, dict):
                rid = related.get("id")
                if isinstance(rid, str):
                    attrs["related_issue_id"] = rid
                ident = related.get("identifier")
                if isinstance(ident, str):
                    attrs["related_issue_identifier"] = ident
            left = attrs.get("issue_identifier") or attrs.get("issue_id") or "?"
            right = attrs.get("related_issue_identifier") or attrs.get("related_issue_id") or "?"
            rel_name = str(rel_type or "related")
            draft.display_label = f"{rel_name}: {left} → {right}"[:512]
        return CanonMapResult(draft=draft, source=src)


LINEAR_MAPPERS: list[_LinearMapper] = [
    _LinearMapper("linear.user", "actor", "user"),
    _LinearMapper("linear.team", "team", "team"),
    _LinearMapper("linear.issue", "work_item", "issue"),
    _LinearMapper("linear.comment", "message", "comment"),
    _LinearMapper("linear.comment_thread", "conversation", "comment_thread"),
    _LinearMapper("linear.project", "project", "project"),
    _LinearMapper("linear.cycle", "cycle", "cycle"),
    _LinearMapper("linear.issue_label", "label", "issue_label"),
    _LinearMapper("linear.initiative", "initiative", "initiative"),
    _LinearMapper("linear.issue_relation", "issue_relation", "issue_relation"),
]
