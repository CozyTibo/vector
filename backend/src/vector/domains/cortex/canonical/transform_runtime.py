"""Phase 03 Steps 6–12 — deterministic transform + field lineage + confidence + identity + replay + provenance + temporal.

Normative: `DOCS/cortex/03-canonical/phase-03-transform-lineage-doctrine.md`,
`phase-03-ambiguity-confidence-doctrine.md`, `phase-03-identity-continuity-doctrine.md`,
`phase-03-replay-versioning-doctrine.md`, `phase-03-provenance-traceability-doctrine.md`,
`phase-03-temporal-timeline-doctrine.md`.
Transform routes are declared in :mod:`transform_routing_registry` (inspectable, versioned). Lineage rules remain
deterministic and bundle-governed; execution is not LLM-driven.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import and_, delete, nullslast, or_, select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.canonical.confidence_runtime import (
    materialization_confidence_rollup,
    stub_lineage_confidence,
)
from vector.domains.cortex.canonical.materialization_topology_engine import (
    build_materialization_stage_plan,
)
from vector.domains.cortex.canonical.temporal_runtime import preview_rebuild_raw_order
from vector.domains.cortex.canonical.identity_runtime import (
    DEFAULT_PHASE04_BOUNDARY,
    canonical_entity_id_for_materialization,
    upsert_identity_anchor_for_materialization,
)
from vector.domains.cortex.canonical.github_timeline_mutation_extract import (
    extract_github_timeline_mutations,
    github_timeline_mutation_revision,
    github_timeline_target_object_ref,
)
from vector.domains.cortex.canonical.logical_keys import logical_key_fields_for_kind
from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.transform_routing_registry import transform_routing_table
from vector.infrastructure.db.models.cortex_canonical_field_lineage import CortexCanonicalFieldLineage
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

TRANSFORM_RUNTIME_SCHEMA_VERSION: Final[int] = 10
ENGINE_BUILD_REF: Final[str] = "phase03-step12-temporal-ordering-v1"

ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM: Final[frozenset[str]] = frozenset({"approved", "candidate"})


class MaterializeError(Exception):
    """Deterministic failure surface for mapping resolution / bundle policy."""


def canonical_json_hash(obj: Any) -> str:
    """Stable SHA-256 over canonical JSON (sorted keys, compact separators)."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class _LineageSpec:
    field_path: str
    rule_id: str
    evidence_grade: str
    source_paths: list[str]
    value_snapshot: Any
    confidence_class: str
    confidence_metadata: dict[str, Any]


@dataclass(frozen=True)
class ResolvedMaterializationInput:
    """Oracle inputs + hashes for one raw row under a pinned bundle (no DB writes)."""

    raw: RawIngestionRecord
    bundle: CortexMappingBundle
    kind: CanonicalObjectKind
    logical_key: dict[str, Any]
    emitted_snapshot: dict[str, Any]
    specs: list[_LineageSpec]
    logical_key_hash: str
    emitted_snapshot_hash: str


def _payload_path(payload: dict[str, Any], dotted: str) -> Any:
    cur: Any = payload
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _normalize_url(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    norm = url.strip()
    if not norm:
        return None
    return norm.rstrip("/")


def _notion_title_from_page(page: dict[str, Any]) -> str | None:
    props = page.get("properties")
    if not isinstance(props, dict):
        return None
    title_prop = props.get("title")
    if isinstance(title_prop, dict):
        title_arr = title_prop.get("title")
        if isinstance(title_arr, list):
            parts: list[str] = []
            for entry in title_arr:
                if not isinstance(entry, dict):
                    continue
                plain = entry.get("plain_text")
                if isinstance(plain, str) and plain:
                    parts.append(plain)
            text = "".join(parts).strip()
            if text:
                return text
    for v in props.values():
        if not isinstance(v, dict):
            continue
        if v.get("type") != "title":
            continue
        title_arr = v.get("title")
        if not isinstance(title_arr, list):
            continue
        parts: list[str] = []
        for entry in title_arr:
            if not isinstance(entry, dict):
                continue
            plain = entry.get("plain_text")
            if isinstance(plain, str) and plain:
                parts.append(plain)
        text = "".join(parts).strip()
        if text:
            return text
    return None


def _notion_parent_ref(page: dict[str, Any]) -> str | None:
    parent = page.get("parent")
    if not isinstance(parent, dict):
        return None
    ptype = parent.get("type")
    if not isinstance(ptype, str) or not ptype.strip():
        return None
    pid = parent.get(ptype)
    if isinstance(pid, dict):
        id_val = pid.get("id")
        if isinstance(id_val, str) and id_val.strip():
            return f"{ptype}:{id_val.strip()}"
    if isinstance(pid, str) and pid.strip():
        return f"{ptype}:{pid.strip()}"
    return f"{ptype}:unknown"


def _notion_database_id_from_row(row: dict[str, Any]) -> str | None:
    parent = row.get("parent")
    if isinstance(parent, dict):
        ptype = parent.get("type")
        if ptype == "database_id":
            dbid = parent.get("database_id")
            if isinstance(dbid, str) and dbid.strip():
                return dbid.strip()
    dbid = row.get("database_id")
    if isinstance(dbid, str) and dbid.strip():
        return dbid.strip()
    return None


def _notion_row_relation_refs(row: dict[str, Any]) -> list[str]:
    props = row.get("properties")
    if not isinstance(props, dict):
        return []
    refs: set[str] = set()
    for pv in props.values():
        if not isinstance(pv, dict):
            continue
        if pv.get("type") != "relation":
            continue
        rel = pv.get("relation")
        if not isinstance(rel, list):
            continue
        for item in rel:
            if not isinstance(item, dict):
                continue
            rid = item.get("id")
            if isinstance(rid, str) and rid.strip():
                refs.add(rid.strip())
    return sorted(refs)


def _notion_row_title(row: dict[str, Any]) -> str | None:
    props = row.get("properties")
    if not isinstance(props, dict):
        return None
    for pv in props.values():
        if not isinstance(pv, dict):
            continue
        if pv.get("type") != "title":
            continue
        title_arr = pv.get("title")
        if not isinstance(title_arr, list):
            continue
        parts: list[str] = []
        for entry in title_arr:
            if not isinstance(entry, dict):
                continue
            plain = entry.get("plain_text")
            if isinstance(plain, str) and plain:
                parts.append(plain)
        title = "".join(parts).strip()
        if title:
            return title
    return None


def _notion_database_schema_keys(db_obj: dict[str, Any]) -> tuple[list[str], list[str]]:
    props = db_obj.get("properties")
    if not isinstance(props, dict):
        return [], []
    names = sorted(str(k) for k in props.keys())
    rel_names: list[str] = []
    for k, v in props.items():
        if not isinstance(v, dict):
            continue
        if v.get("type") == "relation":
            rel_names.append(str(k))
    rel_names.sort()
    return names, rel_names


def _notion_database_title(db_obj: dict[str, Any]) -> str | None:
    title_arr = db_obj.get("title")
    if not isinstance(title_arr, list):
        return None
    parts: list[str] = []
    for entry in title_arr:
        if not isinstance(entry, dict):
            continue
        plain = entry.get("plain_text")
        if isinstance(plain, str) and plain:
            parts.append(plain)
    title = "".join(parts).strip()
    return title or None


def _notion_block_parent_ref(block: dict[str, Any]) -> str | None:
    parent = block.get("parent")
    if isinstance(parent, dict):
        ptype = parent.get("type")
        if isinstance(ptype, str) and ptype.strip():
            val = parent.get(ptype)
            if isinstance(val, dict):
                id_val = val.get("id")
                if isinstance(id_val, str) and id_val.strip():
                    return f"{ptype}:{id_val.strip()}"
            elif isinstance(val, str) and val.strip():
                return f"{ptype}:{val.strip()}"
            return f"{ptype}:unknown"
    parent_id = block.get("parent_id")
    if isinstance(parent_id, str) and parent_id.strip():
        return f"parent_id:{parent_id.strip()}"
    return None


def _notion_block_rich_text_excerpt(block: dict[str, Any]) -> str | None:
    block_type = block.get("type")
    if not isinstance(block_type, str) or not block_type.strip():
        return None
    typed = block.get(block_type)
    if not isinstance(typed, dict):
        return None
    rich = typed.get("rich_text")
    if not isinstance(rich, list):
        return None
    parts: list[str] = []
    for entry in rich:
        if not isinstance(entry, dict):
            continue
        plain = entry.get("plain_text")
        if isinstance(plain, str) and plain:
            parts.append(plain)
    text = "".join(parts).strip()
    if not text:
        return None
    return text[:500]


def _append_lineage_spec(
    specs: list[_LineageSpec],
    *,
    field_path: str,
    rule_id: str,
    evidence_grade: str,
    source_paths: list[str],
    value_snapshot: Any,
) -> None:
    cc, cm = stub_lineage_confidence(field_path=field_path, rule_id=rule_id, evidence_grade=evidence_grade)
    specs.append(
        _LineageSpec(
            field_path=field_path,
            rule_id=rule_id,
            evidence_grade=evidence_grade,
            source_paths=source_paths,
            value_snapshot=value_snapshot,
            confidence_class=cc,
            confidence_metadata=cm,
        )
    )


def _resolve_transform_route(raw: RawIngestionRecord) -> tuple[CanonicalObjectKind, str]:
    key = (raw.connector, raw.resource_type)
    table = transform_routing_table()
    if key not in table:
        raise MaterializeError(f"no_transform_route:{key[0]}:{key[1]}")
    return table[key]


def _build_lineage_specs(
    *,
    raw: RawIngestionRecord,
    bundle_id: str,
    tenant_uuid: uuid.UUID,
    kind: CanonicalObjectKind,
    rule_base: str,
) -> tuple[dict[str, Any], dict[str, Any], list[_LineageSpec]]:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    specs: list[_LineageSpec] = []

    emitted: dict[str, Any] = {
        "connector": raw.connector,
        "resource_type": raw.resource_type,
        "external_id": raw.external_id,
        "source_identity_key": raw.source_identity_key,
        "source_revision_key": raw.source_revision_key,
    }
    for k in sorted(emitted.keys()):
        fp = f"raw_columns.{k}"
        rid = f"{rule_base}.column_copy"
        cc, cm = stub_lineage_confidence(field_path=fp, rule_id=rid, evidence_grade="E0")
        specs.append(
            _LineageSpec(
                field_path=fp,
                rule_id=rid,
                evidence_grade="E0",
                source_paths=[f"raw_ingestion_records.{k}"],
                value_snapshot=emitted[k],
                confidence_class=cc,
                confidence_metadata=cm,
            )
        )

    if kind == CanonicalObjectKind.MESSAGE:
        channel = _payload_path(payload, "channel") or _payload_path(payload, "channel_id")
        ts = _payload_path(payload, "ts")
        conversation_provider_id = str(channel) if channel is not None else str(raw.source_identity_key)
        if raw.resource_type == "slack.message_reply":
            thread_ts = _payload_path(payload, "thread_ts")
            if isinstance(thread_ts, str) and thread_ts.strip():
                conversation_provider_id = f"{conversation_provider_id}:thread:{thread_ts.strip()}"
        elif raw.resource_type in {
            "github.issue_comment",
            "github.pull_request_review",
            "github.pull_request_review_comment",
        }:
            pr_num = _payload_path(payload, "pull_request_number")
            if isinstance(pr_num, int):
                conversation_provider_id = f"{raw.connector}:pull_request:{pr_num}"
        elif raw.resource_type == "github.commit_comment":
            sha = _payload_path(payload, "commit_sha")
            if isinstance(sha, str) and sha.strip():
                conversation_provider_id = f"{raw.connector}:commit:{sha.strip()}"
            comment = payload.get("comment") if isinstance(payload.get("comment"), dict) else {}
            cid = comment.get("id")
            message_discriminant = str(cid if cid is not None else raw.external_id)
            logical_key = {
                "tenant_id": str(tenant_uuid),
                "mapping_bundle_id": bundle_id,
                "connector": raw.connector,
                "conversation_provider_id": conversation_provider_id,
                "message_provider_id": message_discriminant,
            }
            lk_rule = f"{rule_base}.logical_key.message"
            cc_lk, cm_lk = stub_lineage_confidence(
                field_path="logical_key", rule_id=lk_rule, evidence_grade="E1"
            )
            specs.append(
                _LineageSpec(
                    field_path="logical_key",
                    rule_id=lk_rule,
                    evidence_grade="E1",
                    source_paths=[
                        "payload_body.commit_sha",
                        "payload_body.comment.id",
                        "raw_ingestion_records.external_id",
                    ],
                    value_snapshot=logical_key,
                    confidence_class=cc_lk,
                    confidence_metadata=cm_lk,
                )
            )
            return logical_key, emitted, specs
        elif raw.resource_type == "linear.comment":
            issue_id = _payload_path(payload, "comment.issue.id") or _payload_path(payload, "comment.issueId")
            if isinstance(issue_id, str) and issue_id.strip():
                conversation_provider_id = f"linear:issue:{issue_id.strip()}"
        message_discriminant = str(ts if ts is not None else raw.external_id)
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "conversation_provider_id": conversation_provider_id,
            "message_provider_id": message_discriminant,
        }
        lk_rule = f"{rule_base}.logical_key.message"
        cc_lk, cm_lk = stub_lineage_confidence(
            field_path="logical_key", rule_id=lk_rule, evidence_grade="E1"
        )
        specs.append(
            _LineageSpec(
                field_path="logical_key",
                rule_id=lk_rule,
                evidence_grade="E1",
                source_paths=["payload_body.channel", "payload_body.ts", "raw_ingestion_records.external_id"],
                value_snapshot=logical_key,
                confidence_class=cc_lk,
                confidence_metadata=cm_lk,
            )
        )
        if channel is not None:
            emitted["payload_channel"] = channel
            ch_rule = f"{rule_base}.payload.channel"
            cc_ch, cm_ch = stub_lineage_confidence(
                field_path="attributes.payload_channel", rule_id=ch_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.payload_channel",
                    rule_id=ch_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.channel"],
                    value_snapshot=channel,
                    confidence_class=cc_ch,
                    confidence_metadata=cm_ch,
                )
            )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.ISSUE:
        issue_id = str(payload.get("id") or raw.external_id)
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "issue_provider_id": issue_id,
        }
        iss_lk_rule = f"{rule_base}.logical_key.issue"
        cc_ilk, cm_ilk = stub_lineage_confidence(
            field_path="logical_key", rule_id=iss_lk_rule, evidence_grade="E0"
        )
        specs.append(
            _LineageSpec(
                field_path="logical_key",
                rule_id=iss_lk_rule,
                evidence_grade="E0",
                source_paths=["payload_body.id", "raw_ingestion_records.external_id"],
                value_snapshot=logical_key,
                confidence_class=cc_ilk,
                confidence_metadata=cm_ilk,
            )
        )
        title = payload.get("title")
        if title is not None:
            emitted["title"] = title
            t_rule = f"{rule_base}.payload.title"
            cc_t, cm_t = stub_lineage_confidence(
                field_path="attributes.title", rule_id=t_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.title",
                    rule_id=t_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.title"],
                    value_snapshot=title,
                    confidence_class=cc_t,
                    confidence_metadata=cm_t,
                )
            )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.REPOSITORY:
        repo_obj = payload.get("repository") if isinstance(payload.get("repository"), dict) else payload
        repo_id = None
        if isinstance(repo_obj, dict):
            raw_id = repo_obj.get("id")
            if isinstance(raw_id, int):
                repo_id = str(raw_id)
            elif isinstance(raw_id, str) and raw_id.strip():
                repo_id = raw_id.strip()
            elif isinstance(repo_obj.get("full_name"), str):
                repo_id = str(repo_obj.get("full_name")).strip()
        if not repo_id:
            repo_id = str(raw.external_id).strip()
        if not repo_id:
            raise MaterializeError("repository_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "repository_provider_id": repo_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.repository",
            evidence_grade="E0",
            source_paths=["payload_body.repository.id", "payload_body.repository.full_name", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.PROJECT:
        project_obj = payload.get("project") if isinstance(payload.get("project"), dict) else payload
        project_id = str(project_obj.get("id") if isinstance(project_obj, dict) else raw.external_id).strip()
        if not project_id:
            raise MaterializeError("project_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "project_provider_id": project_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.project",
            evidence_grade="E0",
            source_paths=["payload_body.project.id", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.CYCLE:
        cycle_obj = payload.get("cycle") if isinstance(payload.get("cycle"), dict) else payload
        cycle_id = str(cycle_obj.get("id") if isinstance(cycle_obj, dict) else raw.external_id).strip()
        if not cycle_id:
            raise MaterializeError("cycle_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "cycle_provider_id": cycle_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.cycle",
            evidence_grade="E0",
            source_paths=["payload_body.cycle.id", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.INITIATIVE:
        initiative_obj = payload.get("initiative") if isinstance(payload.get("initiative"), dict) else payload
        initiative_id = str(
            initiative_obj.get("id") if isinstance(initiative_obj, dict) else raw.external_id
        ).strip()
        if not initiative_id:
            raise MaterializeError("initiative_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "initiative_provider_id": initiative_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.initiative",
            evidence_grade="E0",
            source_paths=["payload_body.initiative.id", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.CONVERSATION:
        conv = payload.get("channel") if isinstance(payload.get("channel"), dict) else payload
        conv_id = str(conv.get("id") if isinstance(conv, dict) else raw.external_id).strip()
        if not conv_id:
            raise MaterializeError("conversation_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "conversation_provider_id": conv_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.conversation",
            evidence_grade="E0",
            source_paths=["payload_body.channel.id", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.PERSON:
        if raw.resource_type == "calls.participant":
            participant = payload.get("participant") if isinstance(payload.get("participant"), dict) else None
            if participant is None and isinstance(payload.get("participant_record"), dict):
                pr = payload.get("participant_record")
                participant = pr.get("participant") if isinstance(pr.get("participant"), dict) else pr
            if participant is None:
                participant = payload
            if not isinstance(participant, dict):
                raise MaterializeError("person_payload_not_object")
            participant_id = participant.get("id") or participant.get("email") or raw.external_id
            actor_id = str(participant_id).strip()
        else:
            member = payload.get("member") if isinstance(payload.get("member"), dict) else payload
            actor_id = str(member.get("id") if isinstance(member, dict) else raw.external_id).strip()
        if not actor_id:
            raise MaterializeError("person_missing_provider_actor_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "provider_actor_id": actor_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.person",
            evidence_grade="E0",
            source_paths=["payload_body.member.id", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.MEETING:
        mtg = payload.get("meeting") if isinstance(payload.get("meeting"), dict) else payload
        meeting_id = str(mtg.get("id") if isinstance(mtg, dict) else raw.external_id).strip()
        if not meeting_id:
            raise MaterializeError("meeting_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "meeting_provider_id": meeting_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.meeting",
            evidence_grade="E0",
            source_paths=["payload_body.meeting.id", "raw_ingestion_records.external_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.WORKFLOW_RUN:
        run = payload.get("workflow_run") if isinstance(payload.get("workflow_run"), dict) else None
        if run is None and isinstance(payload.get("check_suite"), dict):
            run = payload.get("check_suite")
        if run is None:
            run = payload
        if not isinstance(run, dict):
            raise MaterializeError("workflow_run_payload_not_object")
        run_id = run.get("id")
        workflow_run_provider_id = str(run_id).strip() if run_id is not None else ""
        if not workflow_run_provider_id:
            raise MaterializeError("workflow_run_missing_provider_id")
        repo = run.get("repository") if isinstance(run.get("repository"), dict) else {}
        if not repo or (
            repo.get("id") is None
            and not (isinstance(repo.get("full_name"), str) and repo.get("full_name", "").strip())
        ):
            hr = run.get("head_repository") if isinstance(run.get("head_repository"), dict) else {}
            if hr:
                repo = hr
        repo_id = repo.get("id")
        if isinstance(repo_id, int):
            repository_provider_id = str(repo_id)
        elif isinstance(repo_id, str) and repo_id.strip():
            repository_provider_id = repo_id.strip()
        else:
            repo_name = repo.get("full_name")
            repository_provider_id = str(repo_name).strip() if isinstance(repo_name, str) else ""
        if not repository_provider_id:
            ext = str(raw.external_id or "").strip()
            marker = ":workflow_run:"
            if marker in ext:
                prefix = ext.split(marker, 1)[0].strip()
                if "/" in prefix:
                    repository_provider_id = prefix
        if not repository_provider_id:
            raise MaterializeError("workflow_run_missing_repository_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "repository_provider_id": repository_provider_id,
            "workflow_run_provider_id": workflow_run_provider_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.workflow_run",
            evidence_grade="E0",
            source_paths=["payload_body.workflow_run.id", "payload_body.workflow_run.repository.id"],
            value_snapshot=logical_key,
        )
        status = run.get("status")
        if isinstance(status, str) and status.strip():
            emitted["status"] = status.strip().lower()
        conclusion = run.get("conclusion")
        if isinstance(conclusion, str) and conclusion.strip():
            emitted["conclusion"] = conclusion.strip().lower()
        head_sha = run.get("head_sha")
        if isinstance(head_sha, str) and head_sha.strip():
            emitted["head_sha"] = head_sha.strip()
        branch = run.get("head_branch")
        if isinstance(branch, str) and branch.strip():
            emitted["head_branch"] = branch.strip()
        actor = run.get("actor") if isinstance(run.get("actor"), dict) else {}
        if actor.get("id") is not None:
            emitted["trigger_actor_id"] = str(actor.get("id"))
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.DEPLOYMENT:
        dep = payload.get("deployment") if isinstance(payload.get("deployment"), dict) else None
        if dep is None and isinstance(payload.get("release"), dict):
            dep = payload.get("release")
        if dep is None:
            dep = payload
        if not isinstance(dep, dict):
            raise MaterializeError("deployment_payload_not_object")
        dep_id = dep.get("id")
        deployment_provider_id = str(dep_id).strip() if dep_id is not None else ""
        if not deployment_provider_id:
            raise MaterializeError("deployment_missing_provider_id")
        repo = dep.get("repository") if isinstance(dep.get("repository"), dict) else {}
        repo_id = repo.get("id")
        if isinstance(repo_id, int):
            repository_provider_id = str(repo_id)
        elif isinstance(repo_id, str) and repo_id.strip():
            repository_provider_id = repo_id.strip()
        else:
            repository_provider_id = str(raw.external_id).split(":deployment:", 1)[0].strip()
        if not repository_provider_id:
            raise MaterializeError("deployment_missing_repository_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "repository_provider_id": repository_provider_id,
            "deployment_provider_id": deployment_provider_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.deployment",
            evidence_grade="E0",
            source_paths=["payload_body.deployment.id", "payload_body.deployment.repository.id"],
            value_snapshot=logical_key,
        )
        environment = dep.get("environment")
        if isinstance(environment, str) and environment.strip():
            emitted["environment"] = environment.strip()
        sha = dep.get("sha")
        if isinstance(sha, str) and sha.strip():
            emitted["commit_sha"] = sha.strip()
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.TRANSCRIPT:
        tr = payload.get("transcript_record") if isinstance(payload.get("transcript_record"), dict) else payload
        if not isinstance(tr, dict):
            raise MaterializeError("transcript_payload_not_object")
        meeting_id = tr.get("meeting_id")
        meeting_provider_id = str(meeting_id).strip() if meeting_id is not None else ""
        if not meeting_provider_id:
            raise MaterializeError("transcript_missing_meeting_provider_id")
        transcript_provider_id = str(tr.get("transcript_id") or raw.external_id).strip()
        if not transcript_provider_id:
            raise MaterializeError("transcript_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "meeting_provider_id": meeting_provider_id,
            "transcript_provider_id": transcript_provider_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.transcript",
            evidence_grade="E0",
            source_paths=["payload_body.transcript_record.meeting_id", "payload_body.transcript_record.transcript_id"],
            value_snapshot=logical_key,
        )
        seg_count = tr.get("segment_count")
        if isinstance(seg_count, int):
            emitted["segment_count"] = seg_count
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.EXECUTION_CHECK:
        if "check_run" in payload and not isinstance(payload.get("check_run"), dict):
            raise MaterializeError("execution_check_payload_not_object")
        check_run = payload.get("check_run") if isinstance(payload.get("check_run"), dict) else payload
        if not isinstance(check_run, dict):
            raise MaterializeError("execution_check_payload_not_object")

        repo_obj = check_run.get("repository") if isinstance(check_run.get("repository"), dict) else {}
        repository_provider_id: str | None = None
        repo_id = repo_obj.get("id")
        if isinstance(repo_id, int):
            repository_provider_id = str(repo_id)
        elif isinstance(repo_id, str) and repo_id.strip():
            repository_provider_id = repo_id.strip()
        elif isinstance(repo_obj.get("full_name"), str) and str(repo_obj.get("full_name")).strip():
            repository_provider_id = str(repo_obj.get("full_name")).strip()
        else:
            ext = str(raw.external_id or "").strip()
            if ext and ":" in ext:
                prefix = ext.split(":", 1)[0].strip()
                if "/" in prefix:
                    repository_provider_id = prefix
        if not repository_provider_id:
            raise MaterializeError("execution_check_missing_repository_provider_id")

        check_run_provider_id: str | None = None
        cr_id = check_run.get("id")
        if isinstance(cr_id, int):
            check_run_provider_id = str(cr_id)
        elif isinstance(cr_id, str) and cr_id.strip():
            check_run_provider_id = cr_id.strip()
        else:
            ext = str(raw.external_id or "").strip()
            marker = ":check:"
            if marker in ext:
                suffix = ext.split(marker, 1)[1].strip()
                if suffix:
                    check_run_provider_id = suffix
        if not check_run_provider_id:
            raise MaterializeError("execution_check_missing_check_run_provider_id")

        status = str(check_run.get("status") or "").strip().lower()
        if status not in {"queued", "in_progress", "completed"}:
            raise MaterializeError("execution_check_invalid_status")
        conclusion_raw = check_run.get("conclusion")
        conclusion = str(conclusion_raw).strip().lower() if conclusion_raw is not None else None
        if conclusion == "":
            conclusion = None
        if conclusion is not None and status != "completed":
            raise MaterializeError("execution_check_conclusion_without_completed_status")
        if status == "completed" and conclusion is None:
            raise MaterializeError("execution_check_completed_status_missing_conclusion")

        started_at = check_run.get("started_at")
        completed_at = check_run.get("completed_at")
        started_dt: datetime | None = None
        completed_dt: datetime | None = None
        if isinstance(started_at, str) and started_at.strip():
            try:
                started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except ValueError:
                raise MaterializeError("execution_check_invalid_started_at") from None
        if isinstance(completed_at, str) and completed_at.strip():
            try:
                completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            except ValueError:
                raise MaterializeError("execution_check_invalid_completed_at") from None
        if started_dt is not None and completed_dt is not None and completed_dt < started_dt:
            raise MaterializeError("execution_check_completed_before_started")
        duration_ms = (
            int((completed_dt - started_dt).total_seconds() * 1000)
            if started_dt is not None and completed_dt is not None
            else None
        )

        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "repository_provider_id": repository_provider_id,
            "check_run_provider_id": check_run_provider_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.execution_check",
            evidence_grade="E0",
            source_paths=[
                "payload_body.check_run.repository.id",
                "payload_body.check_run.repository.full_name",
                "payload_body.check_run.id",
                "raw_ingestion_records.external_id",
            ],
            value_snapshot=logical_key,
        )

        app = check_run.get("app") if isinstance(check_run.get("app"), dict) else {}
        app_id = app.get("id")
        if app_id is not None:
            emitted["app_id"] = str(app_id)
        check_name = check_run.get("name")
        if isinstance(check_name, str) and check_name.strip():
            emitted["check_name"] = check_name.strip()
            emitted["workflow_name"] = check_name.strip()
        emitted["status"] = status
        if conclusion is not None:
            emitted["conclusion"] = conclusion
        if isinstance(started_at, str) and started_at.strip():
            emitted["started_at"] = started_at.strip()
        if isinstance(completed_at, str) and completed_at.strip():
            emitted["completed_at"] = completed_at.strip()
        if duration_ms is not None:
            emitted["duration_ms"] = duration_ms

        head_sha = payload.get("head_sha") if isinstance(payload.get("head_sha"), str) else check_run.get("head_sha")
        if isinstance(head_sha, str) and head_sha.strip():
            emitted["commit_sha"] = head_sha.strip()
        pull_num = payload.get("pull_request_number")
        if isinstance(pull_num, int):
            emitted["pull_request_refs"] = [str(pull_num)]
        check_suite = check_run.get("check_suite") if isinstance(check_run.get("check_suite"), dict) else {}
        suite_id = check_suite.get("id")
        if suite_id is not None:
            emitted["workflow_run_ref"] = str(suite_id)
        html_url = check_run.get("html_url")
        if isinstance(html_url, str) and html_url.strip():
            emitted["html_url"] = html_url.strip()
        external_url = check_run.get("details_url")
        if isinstance(external_url, str) and external_url.strip():
            emitted["external_url"] = external_url.strip()

        _append_lineage_spec(
            specs,
            field_path="attributes.execution_state",
            rule_id=f"{rule_base}.payload.execution_state",
            evidence_grade="E0",
            source_paths=[
                "payload_body.check_run.status",
                "payload_body.check_run.conclusion",
                "payload_body.check_run.started_at",
                "payload_body.check_run.completed_at",
            ],
            value_snapshot={
                "status": emitted.get("status"),
                "conclusion": emitted.get("conclusion"),
                "started_at": emitted.get("started_at"),
                "completed_at": emitted.get("completed_at"),
                "duration_ms": emitted.get("duration_ms"),
            },
        )
        _append_lineage_spec(
            specs,
            field_path="attributes.relationship_refs",
            rule_id=f"{rule_base}.payload.relationship_refs",
            evidence_grade="E0",
            source_paths=[
                "payload_body.head_sha",
                "payload_body.pull_request_number",
                "payload_body.check_run.check_suite.id",
            ],
            value_snapshot={
                "commit_sha": emitted.get("commit_sha"),
                "pull_request_refs": emitted.get("pull_request_refs"),
                "workflow_run_ref": emitted.get("workflow_run_ref"),
            },
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.TIMELINE_MUTATION:
        if raw.resource_type in {"github.issue_timeline_event", "github.pull_request_timeline_event"}:
            te = payload.get("timeline_event") if isinstance(payload.get("timeline_event"), dict) else {}
            mutations = extract_github_timeline_mutations(payload)
            logical_key = {
                "tenant_id": str(tenant_uuid),
                "mapping_bundle_id": bundle_id,
                "connector": raw.connector,
                "target_object_ref": github_timeline_target_object_ref(payload),
                "mutation_revision": github_timeline_mutation_revision(payload, te),
            }
            _append_lineage_spec(
                specs,
                field_path="logical_key",
                rule_id=f"{rule_base}.logical_key.github_timeline_timeline_mutation",
                evidence_grade="E0",
                source_paths=[
                    "payload_body.github_pull_request_id",
                    "payload_body.github_issue_id",
                    "payload_body.timeline_event.id",
                    "payload_body.id",
                ],
                value_snapshot=logical_key,
            )
            evt_raw = te.get("event")
            if isinstance(evt_raw, str) and evt_raw.strip():
                evs = evt_raw.strip()
                emitted["github_timeline_event_type"] = evs
                _append_lineage_spec(
                    specs,
                    field_path="attributes.github_timeline_event_type",
                    rule_id=f"{rule_base}.attributes.github_timeline_event_type",
                    evidence_grade="E0",
                    source_paths=["payload_body.timeline_event.event"],
                    value_snapshot=evs,
                )
            cat = te.get("created_at")
            if isinstance(cat, str) and cat.strip():
                emitted["github_timeline_created_at"] = cat.strip()
                _append_lineage_spec(
                    specs,
                    field_path="attributes.github_timeline_created_at",
                    rule_id=f"{rule_base}.attributes.github_timeline_created_at",
                    evidence_grade="E0",
                    source_paths=["payload_body.timeline_event.created_at"],
                    value_snapshot=cat.strip(),
                )
            emitted["execution_mutations"] = mutations
            _append_lineage_spec(
                specs,
                field_path="attributes.execution_mutations",
                rule_id=f"{rule_base}.attributes.execution_mutations",
                evidence_grade="E0",
                source_paths=["payload_body.timeline_event"],
                value_snapshot=mutations,
            )
            return logical_key, emitted, specs

        status_block = payload.get("status")
        status_id = status_block.get("id") if isinstance(status_block, dict) else None
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "target_object_ref": str(payload.get("deployment_id") or raw.external_id),
            "mutation_revision": str(
                status_id or payload.get("status_id") or payload.get("state") or raw.source_revision_key
            ),
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.timeline_mutation",
            evidence_grade="E0",
            source_paths=[
                "payload_body.deployment_id",
                "payload_body.status.id",
                "payload_body.status_id",
                "payload_body.state",
            ],
            value_snapshot=logical_key,
        )
        st_src = payload.get("state")
        if isinstance(status_block, dict) and isinstance(status_block.get("state"), str):
            st_src = status_block.get("state")
        if isinstance(st_src, str) and st_src.strip():
            emitted["state"] = st_src.strip().lower()
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.CANONICAL_EVENT:
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "event_discriminant": str(payload.get("id") or raw.external_id),
            "source_raw_record_id": str(raw.id),
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.canonical_event",
            evidence_grade="E0",
            source_paths=["payload_body.id", "raw_ingestion_records.external_id", "raw_ingestion_records.id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.THREAD:
        thread_provider_id = ""
        if raw.resource_type in {"slack.thread", "slack.message_reply"}:
            ch = payload.get("channel_id") if isinstance(payload.get("channel_id"), str) else payload.get("channel")
            rep = payload.get("reply") if isinstance(payload.get("reply"), dict) else {}
            ts = payload.get("thread_ts") or payload.get("ts") or rep.get("ts")
            if isinstance(ch, str) and ch.strip() and isinstance(ts, str) and ts.strip():
                thread_provider_id = f"{ch.strip()}:{ts.strip()}"
        if raw.resource_type == "github.review_thread":
            pr_num = payload.get("pull_request_number")
            thread_id = payload.get("thread_id")
            if thread_id is not None:
                thread_provider_id = f"pr:{pr_num}:thread:{thread_id}"
        if raw.resource_type == "linear.comment_thread":
            tid = payload.get("thread_id")
            if tid is not None:
                thread_provider_id = str(tid)
        if not thread_provider_id:
            thread_provider_id = str(raw.external_id).strip()
        if not thread_provider_id:
            raise MaterializeError("thread_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "thread_provider_id": thread_provider_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.thread",
            evidence_grade="E0",
            source_paths=["payload_body.thread_ts", "payload_body.channel", "payload_body.thread_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.RECORDING:
        rec = payload.get("recording_record") if isinstance(payload.get("recording_record"), dict) else payload
        meeting_id = rec.get("meeting_id") if isinstance(rec, dict) else None
        recording_obj = rec.get("recording") if isinstance(rec.get("recording"), dict) else {}
        recording_id = recording_obj.get("recording_id") if isinstance(recording_obj, dict) else None
        meeting_provider_id = str(meeting_id).strip() if meeting_id is not None else ""
        recording_provider_id = str(recording_id).strip() if recording_id is not None else ""
        if not meeting_provider_id:
            raise MaterializeError("recording_missing_meeting_provider_id")
        if not recording_provider_id:
            recording_provider_id = str(raw.external_id).strip()
        if not recording_provider_id:
            raise MaterializeError("recording_missing_provider_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "meeting_provider_id": meeting_provider_id,
            "recording_provider_id": recording_provider_id,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.recording",
            evidence_grade="E0",
            source_paths=["payload_body.recording_record.meeting_id", "payload_body.recording_record.recording.recording_id"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.TRANSCRIPT_SEGMENT:
        seg = payload.get("segment_record") if isinstance(payload.get("segment_record"), dict) else payload
        meeting_id = seg.get("meeting_id") if isinstance(seg, dict) else None
        segment_index = seg.get("segment_index") if isinstance(seg, dict) else None
        meeting_provider_id = str(meeting_id).strip() if meeting_id is not None else ""
        if not meeting_provider_id:
            raise MaterializeError("transcript_segment_missing_meeting_provider_id")
        if not isinstance(segment_index, int):
            raise MaterializeError("transcript_segment_missing_segment_index")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "meeting_provider_id": meeting_provider_id,
            "segment_ordinal": segment_index,
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.transcript_segment",
            evidence_grade="E0",
            source_paths=["payload_body.segment_record.meeting_id", "payload_body.segment_record.segment_index"],
            value_snapshot=logical_key,
        )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.CANONICAL_REFERENCE:
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "referenced_object_kind": raw.resource_type,
            "stable_key": raw.external_id,
            "raw_record_ref": str(raw.id),
        }
        _append_lineage_spec(
            specs,
            field_path="logical_key",
            rule_id=f"{rule_base}.logical_key.reference",
            evidence_grade="E0",
            source_paths=["raw_ingestion_records.resource_type", "raw_ingestion_records.external_id", "raw_ingestion_records.id"],
            value_snapshot=logical_key,
        )
        emitted["referenced_object_kind"] = raw.resource_type
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.DOCUMENT:
        if raw.resource_type in {"slack.file", "linear.issue_attachment"}:
            if raw.resource_type == "linear.issue_attachment":
                file_obj = (
                    payload.get("attachment") if isinstance(payload.get("attachment"), dict) else payload
                )
            else:
                file_obj = payload.get("file") if isinstance(payload.get("file"), dict) else payload
            if not isinstance(file_obj, dict):
                raise MaterializeError("document_payload_not_object")
            provider_id = str(file_obj.get("id") or raw.external_id).strip()
            if not provider_id:
                raise MaterializeError("document_missing_provider_id")
            logical_key = {
                "tenant_id": str(tenant_uuid),
                "mapping_bundle_id": bundle_id,
                "connector": raw.connector,
                "document_provider_id": provider_id,
            }
            _append_lineage_spec(
                specs,
                field_path="logical_key",
                rule_id=f"{rule_base}.logical_key.document",
                evidence_grade="E0",
                source_paths=["payload_body.file.id", "raw_ingestion_records.external_id"],
                value_snapshot=logical_key,
            )
            title = file_obj.get("name") or file_obj.get("title")
            if isinstance(title, str) and title.strip():
                emitted["title"] = title.strip()
            source_url = _normalize_url(file_obj.get("url_private") or file_obj.get("url"))
            if source_url is not None:
                emitted["source_url"] = source_url
            return logical_key, emitted, specs

        page = payload.get("page") if isinstance(payload.get("page"), dict) else payload
        if not isinstance(page, dict):
            raise MaterializeError("document_payload_not_object")
        page_id = page.get("id")
        if isinstance(page_id, str) and page_id.strip():
            document_provider_id = page_id.strip()
        else:
            ext = str(raw.external_id).strip()
            if not ext:
                raise MaterializeError("document_missing_provider_id")
            document_provider_id = ext
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "document_provider_id": document_provider_id,
        }
        doc_lk_rule = f"{rule_base}.logical_key.document"
        cc_doc, cm_doc = stub_lineage_confidence(
            field_path="logical_key", rule_id=doc_lk_rule, evidence_grade="E0"
        )
        specs.append(
            _LineageSpec(
                field_path="logical_key",
                rule_id=doc_lk_rule,
                evidence_grade="E0",
                source_paths=["payload_body.page.id", "raw_ingestion_records.external_id"],
                value_snapshot=logical_key,
                confidence_class=cc_doc,
                confidence_metadata=cm_doc,
            )
        )
        parent_ref = _notion_parent_ref(page)
        if parent_ref is not None:
            emitted["parent_ref"] = parent_ref
            parent_rule = f"{rule_base}.payload.parent"
            cc_parent, cm_parent = stub_lineage_confidence(
                field_path="attributes.parent_ref",
                rule_id=parent_rule,
                evidence_grade="E0",
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.parent_ref",
                    rule_id=parent_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.page.parent"],
                    value_snapshot=parent_ref,
                    confidence_class=cc_parent,
                    confidence_metadata=cm_parent,
                )
            )
        url = _normalize_url(page.get("url"))
        if url is not None:
            emitted["source_url"] = url
            url_rule = f"{rule_base}.payload.url"
            cc_url, cm_url = stub_lineage_confidence(
                field_path="attributes.source_url", rule_id=url_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.source_url",
                    rule_id=url_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.page.url"],
                    value_snapshot=url,
                    confidence_class=cc_url,
                    confidence_metadata=cm_url,
                )
            )
        title = _notion_title_from_page(page)
        if title is not None:
            emitted["title"] = title
            title_rule = f"{rule_base}.payload.title"
            cc_title, cm_title = stub_lineage_confidence(
                field_path="attributes.title", rule_id=title_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.title",
                    rule_id=title_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.page.properties.*.title"],
                    value_snapshot=title,
                    confidence_class=cc_title,
                    confidence_metadata=cm_title,
                )
            )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.DATABASE_ROW:
        row = payload.get("row") if isinstance(payload.get("row"), dict) else payload
        if not isinstance(row, dict):
            raise MaterializeError("database_row_payload_not_object")
        row_id = row.get("id")
        if isinstance(row_id, str) and row_id.strip():
            row_provider_id = row_id.strip()
        else:
            ext = str(raw.external_id).strip()
            if not ext:
                raise MaterializeError("database_row_missing_row_id")
            row_provider_id = ext
        database_provider_id = _notion_database_id_from_row(row)
        if database_provider_id is None:
            raise MaterializeError("database_row_missing_database_id")
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "database_provider_id": database_provider_id,
            "row_provider_id": row_provider_id,
        }
        row_lk_rule = f"{rule_base}.logical_key.database_row"
        cc_row, cm_row = stub_lineage_confidence(
            field_path="logical_key", rule_id=row_lk_rule, evidence_grade="E0"
        )
        specs.append(
            _LineageSpec(
                field_path="logical_key",
                rule_id=row_lk_rule,
                evidence_grade="E0",
                source_paths=[
                    "payload_body.row.parent.database_id",
                    "payload_body.row.database_id",
                    "payload_body.row.id",
                    "raw_ingestion_records.external_id",
                ],
                value_snapshot=logical_key,
                confidence_class=cc_row,
                confidence_metadata=cm_row,
            )
        )
        relation_refs = _notion_row_relation_refs(row)
        if relation_refs:
            emitted["relation_refs"] = relation_refs
            rel_rule = f"{rule_base}.payload.relation_refs"
            cc_rel, cm_rel = stub_lineage_confidence(
                field_path="attributes.relation_refs", rule_id=rel_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.relation_refs",
                    rule_id=rel_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.row.properties.*.relation[*].id"],
                    value_snapshot=relation_refs,
                    confidence_class=cc_rel,
                    confidence_metadata=cm_rel,
                )
            )
        title = _notion_row_title(row)
        if title is not None:
            emitted["title"] = title
            title_rule = f"{rule_base}.payload.title"
            cc_title, cm_title = stub_lineage_confidence(
                field_path="attributes.title", rule_id=title_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.title",
                    rule_id=title_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.row.properties.*.title"],
                    value_snapshot=title,
                    confidence_class=cc_title,
                    confidence_metadata=cm_title,
                )
            )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.PAGE:
        if raw.resource_type == "notion.block":
            block_obj = payload.get("block") if isinstance(payload.get("block"), dict) else payload
            if not isinstance(block_obj, dict):
                raise MaterializeError("page_payload_not_object")
            page_provider_id = block_obj.get("id")
            if isinstance(page_provider_id, str) and page_provider_id.strip():
                page_provider_id = page_provider_id.strip()
            else:
                ext = str(raw.external_id).strip()
                if not ext:
                    raise MaterializeError("page_missing_provider_id")
                page_provider_id = ext
            logical_key = {
                "tenant_id": str(tenant_uuid),
                "mapping_bundle_id": bundle_id,
                "connector": raw.connector,
                "page_provider_id": page_provider_id,
            }
            page_lk_rule = f"{rule_base}.logical_key.page"
            cc_page, cm_page = stub_lineage_confidence(
                field_path="logical_key", rule_id=page_lk_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="logical_key",
                    rule_id=page_lk_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.block.id", "raw_ingestion_records.external_id"],
                    value_snapshot=logical_key,
                    confidence_class=cc_page,
                    confidence_metadata=cm_page,
                )
            )
            block_type = block_obj.get("type")
            if isinstance(block_type, str) and block_type.strip():
                emitted["block_type"] = block_type.strip()
                type_rule = f"{rule_base}.payload.block_type"
                cc_type, cm_type = stub_lineage_confidence(
                    field_path="attributes.block_type", rule_id=type_rule, evidence_grade="E0"
                )
                specs.append(
                    _LineageSpec(
                        field_path="attributes.block_type",
                        rule_id=type_rule,
                        evidence_grade="E0",
                        source_paths=["payload_body.block.type"],
                        value_snapshot=block_type.strip(),
                        confidence_class=cc_type,
                        confidence_metadata=cm_type,
                    )
                )
            parent_ref = _notion_block_parent_ref(block_obj)
            if parent_ref is not None:
                emitted["parent_ref"] = parent_ref
                parent_rule = f"{rule_base}.payload.parent"
                cc_parent, cm_parent = stub_lineage_confidence(
                    field_path="attributes.parent_ref",
                    rule_id=parent_rule,
                    evidence_grade="E0",
                )
                specs.append(
                    _LineageSpec(
                        field_path="attributes.parent_ref",
                        rule_id=parent_rule,
                        evidence_grade="E0",
                        source_paths=["payload_body.block.parent", "payload_body.block.parent_id"],
                        value_snapshot=parent_ref,
                        confidence_class=cc_parent,
                        confidence_metadata=cm_parent,
                    )
                )
            rich_excerpt = _notion_block_rich_text_excerpt(block_obj)
            if rich_excerpt is not None:
                emitted["rich_text_excerpt"] = rich_excerpt
                rich_rule = f"{rule_base}.payload.rich_text_excerpt"
                cc_rich, cm_rich = stub_lineage_confidence(
                    field_path="attributes.rich_text_excerpt",
                    rule_id=rich_rule,
                    evidence_grade="E0",
                )
                specs.append(
                    _LineageSpec(
                        field_path="attributes.rich_text_excerpt",
                        rule_id=rich_rule,
                        evidence_grade="E0",
                        source_paths=["payload_body.block.<type>.rich_text[*].plain_text"],
                        value_snapshot=rich_excerpt,
                        confidence_class=cc_rich,
                        confidence_metadata=cm_rich,
                    )
                )
            qp = raw.query_params if isinstance(raw.query_params, dict) else {}
            start_cursor = qp.get("start_cursor")
            if isinstance(start_cursor, str):
                emitted["sibling_cursor_hint"] = start_cursor
                cursor_rule = f"{rule_base}.payload.sibling_cursor_hint"
                cc_cursor, cm_cursor = stub_lineage_confidence(
                    field_path="attributes.sibling_cursor_hint",
                    rule_id=cursor_rule,
                    evidence_grade="E0",
                )
                specs.append(
                    _LineageSpec(
                        field_path="attributes.sibling_cursor_hint",
                        rule_id=cursor_rule,
                        evidence_grade="E0",
                        source_paths=["raw_ingestion_records.query_params.start_cursor"],
                        value_snapshot=start_cursor,
                        confidence_class=cc_cursor,
                        confidence_metadata=cm_cursor,
                    )
                )
            return logical_key, emitted, specs

        db_obj = payload.get("database") if isinstance(payload.get("database"), dict) else payload
        if not isinstance(db_obj, dict):
            raise MaterializeError("page_payload_not_object")
        page_provider_id = db_obj.get("id")
        if isinstance(page_provider_id, str) and page_provider_id.strip():
            page_provider_id = page_provider_id.strip()
        else:
            ext = str(raw.external_id).strip()
            if not ext:
                raise MaterializeError("page_missing_provider_id")
            page_provider_id = ext
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "page_provider_id": page_provider_id,
        }
        page_lk_rule = f"{rule_base}.logical_key.page"
        cc_page, cm_page = stub_lineage_confidence(
            field_path="logical_key", rule_id=page_lk_rule, evidence_grade="E0"
        )
        specs.append(
            _LineageSpec(
                field_path="logical_key",
                rule_id=page_lk_rule,
                evidence_grade="E0",
                source_paths=["payload_body.database.id", "raw_ingestion_records.external_id"],
                value_snapshot=logical_key,
                confidence_class=cc_page,
                confidence_metadata=cm_page,
            )
        )
        schema_keys, relation_keys = _notion_database_schema_keys(db_obj)
        if schema_keys:
            emitted["schema_property_names"] = schema_keys
            schema_rule = f"{rule_base}.payload.schema_property_names"
            cc_schema, cm_schema = stub_lineage_confidence(
                field_path="attributes.schema_property_names",
                rule_id=schema_rule,
                evidence_grade="E0",
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.schema_property_names",
                    rule_id=schema_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.database.properties"],
                    value_snapshot=schema_keys,
                    confidence_class=cc_schema,
                    confidence_metadata=cm_schema,
                )
            )
        if relation_keys:
            emitted["relation_property_names"] = relation_keys
            rel_rule = f"{rule_base}.payload.relation_property_names"
            cc_rel, cm_rel = stub_lineage_confidence(
                field_path="attributes.relation_property_names",
                rule_id=rel_rule,
                evidence_grade="E0",
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.relation_property_names",
                    rule_id=rel_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.database.properties.*.type"],
                    value_snapshot=relation_keys,
                    confidence_class=cc_rel,
                    confidence_metadata=cm_rel,
                )
            )
        title = _notion_database_title(db_obj)
        if title is not None:
            emitted["title"] = title
            t_rule = f"{rule_base}.payload.title"
            cc_t, cm_t = stub_lineage_confidence(
                field_path="attributes.title", rule_id=t_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.title",
                    rule_id=t_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.database.title"],
                    value_snapshot=title,
                    confidence_class=cc_t,
                    confidence_metadata=cm_t,
                )
            )
        return logical_key, emitted, specs

    if kind == CanonicalObjectKind.PULL_REQUEST:
        pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}
        base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
        repo = base.get("repo") if isinstance(base.get("repo"), dict) else {}
        repo_id = repo.get("id")
        if repo_id is not None:
            if isinstance(repo_id, int):
                repository_provider_id = str(repo_id)
            elif isinstance(repo_id, str) and repo_id.strip():
                repository_provider_id = repo_id.strip()
            else:
                repository_provider_id = str(repo_id)
        else:
            full_name = repo.get("full_name")
            if isinstance(full_name, str) and full_name.strip():
                repository_provider_id = full_name.strip()
            else:
                raise MaterializeError("pull_request_missing_repository_provider_id")
        num = pr.get("number")
        if not isinstance(num, int):
            raise MaterializeError("pull_request_missing_number")
        pull_request_discriminant = str(num)
        logical_key = {
            "tenant_id": str(tenant_uuid),
            "mapping_bundle_id": bundle_id,
            "connector": raw.connector,
            "repository_provider_id": repository_provider_id,
            "pull_request_discriminant": pull_request_discriminant,
        }
        pr_lk_rule = f"{rule_base}.logical_key.pull_request"
        cc_pr, cm_pr = stub_lineage_confidence(
            field_path="logical_key", rule_id=pr_lk_rule, evidence_grade="E0"
        )
        specs.append(
            _LineageSpec(
                field_path="logical_key",
                rule_id=pr_lk_rule,
                evidence_grade="E0",
                source_paths=[
                    "payload_body.pull_request.base.repo.id",
                    "payload_body.pull_request.base.repo.full_name",
                    "payload_body.pull_request.number",
                ],
                value_snapshot=logical_key,
                confidence_class=cc_pr,
                confidence_metadata=cm_pr,
            )
        )
        title = pr.get("title")
        if title is not None:
            emitted["title"] = title
            t_rule = f"{rule_base}.payload.title"
            cc_t, cm_t = stub_lineage_confidence(
                field_path="attributes.title", rule_id=t_rule, evidence_grade="E0"
            )
            specs.append(
                _LineageSpec(
                    field_path="attributes.title",
                    rule_id=t_rule,
                    evidence_grade="E0",
                    source_paths=["payload_body.pull_request.title"],
                    value_snapshot=title,
                    confidence_class=cc_t,
                    confidence_metadata=cm_t,
                )
            )
        return logical_key, emitted, specs

    raise MaterializeError(f"unsupported_transform_kind:{kind.value}")


def _validate_logical_key_shape(kind: CanonicalObjectKind, logical_key: dict[str, Any]) -> None:
    fields = logical_key_fields_for_kind(kind)
    for name in fields:
        if name not in logical_key:
            raise MaterializeError(f"logical_key_missing_field:{name}")


def resolve_materialization_input(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    raw_record_id: int,
) -> ResolvedMaterializationInput:
    """Resolve deterministic oracle projection (hashes + lineage specs) without mutating canonical tables."""
    bundle = db.get(CortexMappingBundle, bundle_id)
    if bundle is None:
        raise MaterializeError("unknown_bundle")
    if bundle.lifecycle_state not in ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM:
        raise MaterializeError(f"bundle_not_transformable:{bundle.lifecycle_state}")

    raw = db.scalars(
        select(RawIngestionRecord).where(
            RawIngestionRecord.id == raw_record_id,
            RawIngestionRecord.tenant_id == tenant_id,
        )
    ).first()
    if raw is None:
        raise MaterializeError("raw_record_not_found")

    kind, rule_base = _resolve_transform_route(raw)
    logical_key, emitted_snapshot, specs = _build_lineage_specs(
        raw=raw,
        bundle_id=bundle_id,
        tenant_uuid=tenant_id,
        kind=kind,
        rule_base=rule_base,
    )
    _validate_logical_key_shape(kind, logical_key)

    lk_hash = canonical_json_hash(logical_key)
    snap_hash = canonical_json_hash(emitted_snapshot)
    return ResolvedMaterializationInput(
        raw=raw,
        bundle=bundle,
        kind=kind,
        logical_key=logical_key,
        emitted_snapshot=emitted_snapshot,
        specs=specs,
        logical_key_hash=lk_hash,
        emitted_snapshot_hash=snap_hash,
    )


def materialize_raw_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    raw_record_id: int,
    replay_job_id: uuid.UUID | None = None,
    commit: bool = True,
) -> CortexCanonicalTransformMaterialization:
    """Deterministic materialization for one raw row under a bundle (replaces prior row on same scope).

    When ``commit`` is False, the caller must commit the session (used by replay jobs for atomic receipts).
    """
    resolved = resolve_materialization_input(db, tenant_id=tenant_id, bundle_id=bundle_id, raw_record_id=raw_record_id)
    raw = resolved.raw
    kind = resolved.kind
    logical_key = resolved.logical_key
    emitted_snapshot = resolved.emitted_snapshot
    specs = resolved.specs
    lk_hash = resolved.logical_key_hash
    snap_hash = resolved.emitted_snapshot_hash

    prior = db.scalars(
        select(CortexCanonicalTransformMaterialization).where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            CortexCanonicalTransformMaterialization.bundle_id == bundle_id,
            CortexCanonicalTransformMaterialization.raw_record_id == raw_record_id,
        )
    ).first()
    prior_id = prior.id if prior is not None else None
    prior_lk_hash = prior.logical_key_hash if prior is not None else None

    db.execute(
        delete(CortexCanonicalTransformMaterialization).where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            CortexCanonicalTransformMaterialization.bundle_id == bundle_id,
            CortexCanonicalTransformMaterialization.raw_record_id == raw_record_id,
        )
    )

    from vector.domains.cortex.canonical.temporal_runtime import (
        build_temporal_ordering_key,
        occurred_at_from_raw,
        record_temporal_supersession,
    )

    occ_at = occurred_at_from_raw(raw)
    obs_at = raw.fetched_at
    if obs_at.tzinfo is None:
        obs_at = obs_at.replace(tzinfo=UTC)
    else:
        obs_at = obs_at.astimezone(UTC)
    proc_at = datetime.now(UTC)
    order_key = build_temporal_ordering_key(
        occurred_at=occ_at,
        replay_sequence=int(raw.replay_sequence),
        source_revision_key=str(raw.source_revision_key),
        raw_record_id=int(raw_record_id),
    )

    mat = CortexCanonicalTransformMaterialization(
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        raw_record_id=raw_record_id,
        canonical_object_kind=kind.value,
        logical_key_json=logical_key,
        logical_key_hash=lk_hash,
        emitted_snapshot_json=emitted_snapshot,
        emitted_snapshot_hash=snap_hash,
        engine_build_ref=ENGINE_BUILD_REF,
        last_replay_job_id=replay_job_id,
        occurred_at=occ_at,
        observed_at=obs_at,
        canonical_processed_at=proc_at,
        source_revision_key=str(raw.source_revision_key),
        temporal_ordering_key=order_key,
    )
    db.add(mat)
    db.flush()

    ordered_specs = sorted(specs, key=lambda s: s.field_path)
    for sp in ordered_specs:
        db.add(
            CortexCanonicalFieldLineage(
                materialization_id=mat.id,
                field_path=sp.field_path,
                rule_id=sp.rule_id,
                evidence_grade=sp.evidence_grade,
                confidence_class=sp.confidence_class,
                confidence_metadata=dict(sp.confidence_metadata),
                source_paths=sp.source_paths,
                value_snapshot=sp.value_snapshot,
            )
        )
    from vector.domains.cortex.canonical.provenance_runtime import upsert_provenance_for_materialization

    upsert_provenance_for_materialization(db, mat, specs=ordered_specs)
    if prior_id is not None and prior_lk_hash is not None:
        record_temporal_supersession(
            db,
            tenant_id=tenant_id,
            bundle_id=bundle_id,
            predecessor_materialization_id=prior_id,
            predecessor_logical_key_hash=prior_lk_hash,
            successor_materialization_id=mat.id,
            causing_raw_record_id=raw_record_id,
            engine_build_ref=ENGINE_BUILD_REF,
        )
    upsert_identity_anchor_for_materialization(db, mat, connector=raw.connector)
    from vector.domains.cortex.canonical.failure_remediation_runtime import (
        deactivate_transform_materialize_failure_case,
    )

    deactivate_transform_materialize_failure_case(
        db, tenant_id=tenant_id, bundle_id=bundle_id, raw_record_id=raw_record_id
    )
    if commit:
        db.commit()
    else:
        db.flush()
    mat_fresh = db.scalars(
        select(CortexCanonicalTransformMaterialization)
        .where(CortexCanonicalTransformMaterialization.id == mat.id)
        .options(selectinload(CortexCanonicalTransformMaterialization.field_lineage))
    ).one()
    return mat_fresh


def repair_tenant_materialization_oracle_determinism_drift(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
    scan_limit: int = 500,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Re-materialize sampled rows whose persisted hashes diverge from ``resolve_materialization_input`` (G-P03-01).

    Backlog drains only create *missing* rows; this path repairs stale projections after mapping/oracle drift.
    """
    lim = max(1, min(int(scan_limit), 5000))
    bid_filter = bundle_id.strip() if isinstance(bundle_id, str) and bundle_id.strip() else None
    stmt = (
        select(CortexCanonicalTransformMaterialization)
        .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        .order_by(
            nullslast(CortexCanonicalTransformMaterialization.canonical_processed_at.desc()),
            CortexCanonicalTransformMaterialization.created_at.desc(),
        )
        .limit(lim)
    )
    if bid_filter is not None:
        stmt = stmt.where(CortexCanonicalTransformMaterialization.bundle_id == bid_filter)
    mats = list(db.scalars(stmt).all())

    mismatch_sample: list[dict[str, Any]] = []
    resolution_failed_sample: list[dict[str, Any]] = []
    repaired_count = 0
    mismatch_total = 0
    resolution_failed_total = 0

    for mat in mats:
        try:
            res = resolve_materialization_input(
                db,
                tenant_id=tenant_id,
                bundle_id=mat.bundle_id,
                raw_record_id=int(mat.raw_record_id),
            )
        except MaterializeError as exc:
            resolution_failed_total += 1
            if len(resolution_failed_sample) < 40:
                resolution_failed_sample.append(
                    {
                        "materialization_id": str(mat.id),
                        "bundle_id": mat.bundle_id,
                        "raw_record_id": mat.raw_record_id,
                        "error": str(exc),
                    }
                )
            continue
        if res.logical_key_hash == mat.logical_key_hash and res.emitted_snapshot_hash == mat.emitted_snapshot_hash:
            continue
        mismatch_total += 1
        if len(mismatch_sample) < 40:
            mismatch_sample.append(
                {
                    "materialization_id": str(mat.id),
                    "bundle_id": mat.bundle_id,
                    "raw_record_id": mat.raw_record_id,
                    "stored_logical_key_hash": mat.logical_key_hash,
                    "oracle_logical_key_hash": res.logical_key_hash,
                    "stored_snapshot_hash": mat.emitted_snapshot_hash,
                    "oracle_snapshot_hash": res.emitted_snapshot_hash,
                }
            )
        if not dry_run:
            materialize_raw_record(
                db,
                tenant_id=tenant_id,
                bundle_id=mat.bundle_id,
                raw_record_id=int(mat.raw_record_id),
            )
            repaired_count += 1

    return {
        "transform_runtime_schema_version": TRANSFORM_RUNTIME_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "bundle_id_filter": bid_filter,
        "scanned_count": len(mats),
        "mismatch_count": mismatch_total,
        "resolution_failed_count": resolution_failed_total,
        "repaired_count": repaired_count,
        "dry_run": dry_run,
        "mismatch_sample": mismatch_sample,
        "resolution_failed_sample": resolution_failed_sample,
    }


def stub_routing_pairs(
    *,
    connector: str | None = None,
    resource_type: str | None = None,
) -> list[tuple[str, str]]:
    """Connector/resource pairs with registered deterministic transforms (backlog + operator filters)."""
    pairs = list(transform_routing_table().keys())
    if connector is not None and connector.strip():
        c = connector.strip()
        pairs = [p for p in pairs if p[0] == c]
    if resource_type is not None and resource_type.strip():
        rt = resource_type.strip()
        pairs = [p for p in pairs if p[1] == rt]
    return pairs


def list_stub_routable_raw_ids_missing_materialization(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    connector: str | None,
    resource_type: str | None,
    fetch_limit: int,
) -> tuple[list[int], bool]:
    """Raw ids that match registered transform routes and have no materialization row for this tenant+bundle yet.

    Returns ``(ids, more_remain)`` where ``more_remain`` is True when at least one additional candidate exists.
    """
    pairs = stub_routing_pairs(connector=connector, resource_type=resource_type)
    if not pairs:
        return [], False
    type_or = or_(
        *[
            and_(RawIngestionRecord.connector == p[0], RawIngestionRecord.resource_type == p[1])
            for p in pairs
        ]
    )
    lim = max(1, fetch_limit)
    stmt = (
        select(RawIngestionRecord.id)
        .outerjoin(
            CortexCanonicalTransformMaterialization,
            and_(
                CortexCanonicalTransformMaterialization.raw_record_id == RawIngestionRecord.id,
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.bundle_id == bundle_id,
            ),
        )
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            type_or,
            CortexCanonicalTransformMaterialization.id.is_(None),
        )
        .order_by(RawIngestionRecord.id.asc())
        .limit(lim + 1)
    )
    rows = [int(x) for x in db.scalars(stmt).all()]
    more_remain = len(rows) > lim
    return rows[:lim], more_remain


def materialize_stub_backlog(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    connector: str | None,
    resource_type: str | None,
    batch_limit: int,
    dry_run: bool,
    pass_index: int = 0,
    topology_cooldown_seconds: int = 60,
) -> dict[str, Any]:
    """Materialize stub-routable raw rows that are missing a projection for ``bundle_id``.

    Non–stub rows are ignored (they never appear in the candidate set). Each successful row commits immediately.
    """
    bundle = db.get(CortexMappingBundle, bundle_id)
    if bundle is None:
        raise MaterializeError("unknown_bundle")
    if bundle.lifecycle_state not in ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM:
        raise MaterializeError(f"bundle_not_transformable:{bundle.lifecycle_state}")

    started_at = datetime.now(UTC)
    pairs = stub_routing_pairs(connector=connector, resource_type=resource_type)
    pair_labels = [f"{c}/{rt}" for c, rt in pairs]

    lim = max(1, min(batch_limit, 2000))
    from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
        list_forward_progress_candidate_ids,
    )

    ids, more_remain, selection_meta = list_forward_progress_candidate_ids(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        connector=connector,
        resource_type=resource_type,
        pass_index=pass_index,
        fetch_limit=lim,
    )
    id_to_rt = {
        int(rid): str(rt)
        for rid, rt in db.execute(
            select(RawIngestionRecord.id, RawIngestionRecord.resource_type).where(RawIngestionRecord.id.in_(ids))
        ).all()
    }
    attempted_by_resource_type: dict[str, int] = {}
    for rid in ids:
        rt = id_to_rt.get(int(rid), "unknown")
        attempted_by_resource_type[rt] = int(attempted_by_resource_type.get(rt, 0)) + 1

    raw_rows = list(db.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(ids))).all())
    raw_rows.sort(key=lambda r: int(r.id))
    preview_rows = preview_rebuild_raw_order(
        db, tenant_id=tenant_id, raw_record_ids=[int(r.id) for r in raw_rows]
    )
    key_by_id = {int(r["raw_record_id"]): str(r["temporal_ordering_key"]) for r in preview_rows}
    for r in raw_rows:
        key_by_id.setdefault(int(r.id), f"{int(r.id):012d}")
    plan = build_materialization_stage_plan(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        rows=raw_rows,
        temporal_key_by_id=key_by_id,
    )
    skip_ids = {int(q["raw_record_id"]) for q in plan["quarantine"] if int(q.get("raw_record_id") or 0)} | {
        int(d["raw_record_id"]) for d in plan["deferred_dependency_queue"] if int(d.get("raw_record_id") or 0)
    }
    topo_meta = {
        "topology_schema_version": plan.get("topology_schema_version"),
        "topology_stage_count": plan.get("topology_stage_count"),
        "stage_sizes": plan.get("stage_sizes"),
        "stage_dependency_wait_count": plan.get("stage_dependency_wait_count"),
        "deferred_child_count": plan.get("deferred_child_count"),
        "replay_blocker_count": plan.get("replay_blocker_count"),
        "cycle_detected": plan.get("cycle_detected"),
        "dependency_edge_count": plan.get("dependency_edge_count"),
        "quarantine_sample": (plan.get("quarantine") or [])[:40],
        "deferred_dependency_sample": (plan.get("deferred_dependency_queue") or [])[:40],
    }

    if dry_run:
        elapsed_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        return {
            "transform_runtime_schema_version": TRANSFORM_RUNTIME_SCHEMA_VERSION,
            "tenant_id": str(tenant_id),
            "bundle_id": bundle_id,
            "dry_run": True,
            "stub_resource_pairs_selected": pair_labels,
            "scope_connector": connector.strip() if connector and connector.strip() else None,
            "scope_resource_type": resource_type.strip() if resource_type and resource_type.strip() else None,
            "batch_limit_applied": lim,
            "candidate_more_remain": more_remain,
            "selected": len(ids),
            "attempted": 0,
            "topology_skipped": len(skip_ids),
            "attempted_by_resource_type": attempted_by_resource_type,
            "succeeded": 0,
            "succeeded_by_resource_type": {},
            "failures": [],
            "raw_record_ids_sample": ids[:50],
            "duration_ms": elapsed_ms,
            "throughput_rows_per_second": 0.0,
            "topology_materialization": topo_meta,
            "topology_skipped_raw_record_ids": sorted(skip_ids),
            "forward_progress": selection_meta,
        }

    failures: list[dict[str, Any]] = []
    succeeded = 0
    succeeded_by_resource_type: dict[str, int] = {}
    from vector.domains.cortex.canonical.failure_remediation_runtime import (
        record_transform_materialize_failure,
    )

    raw_rows_by_id = {int(r.id): r for r in raw_rows}
    pass_key = str(selection_meta.get("pass_key") or "")
    from vector.domains.cortex.canonical.forward_progress.deferral_store import (
        clear_deferral_for_raw_record,
        record_topology_deferrals_from_plan,
    )

    topology_deferred_recorded = record_topology_deferrals_from_plan(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        pass_key=pass_key or None,
        plan=plan,
        raw_rows_by_id=raw_rows_by_id,
        cooldown_seconds=topology_cooldown_seconds,
    )

    for stage_idx, stage in enumerate(plan.get("stages") or []):
        for rid in stage:
            if int(rid) in skip_ids:
                continue
            try:
                materialize_raw_record(db, tenant_id=tenant_id, bundle_id=bundle_id, raw_record_id=int(rid))
                succeeded += 1
                clear_deferral_for_raw_record(
                    db, tenant_id=tenant_id, bundle_id=bundle_id, raw_record_id=int(rid)
                )
                rt = id_to_rt.get(int(rid), "unknown")
                succeeded_by_resource_type[rt] = int(succeeded_by_resource_type.get(rt, 0)) + 1
            except MaterializeError as exc:
                detail = str(exc)
                failures.append(
                    {
                        "raw_record_id": int(rid),
                        "detail": detail,
                        "topology_stage_index": stage_idx,
                    }
                )
                record_transform_materialize_failure(
                    db,
                    tenant_id=tenant_id,
                    bundle_id=bundle_id,
                    raw_record_id=int(rid),
                    message=detail,
                )

    elapsed_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    throughput = (
        round(float(succeeded) / (float(elapsed_ms) / 1000.0), 3)
        if elapsed_ms > 0
        else float(succeeded)
    )
    processable_attempted = succeeded + len(failures)
    return {
        "transform_runtime_schema_version": TRANSFORM_RUNTIME_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "bundle_id": bundle_id,
        "dry_run": False,
        "stub_resource_pairs_selected": pair_labels,
        "scope_connector": connector.strip() if connector and connector.strip() else None,
        "scope_resource_type": resource_type.strip() if resource_type and resource_type.strip() else None,
        "batch_limit_applied": lim,
        "candidate_more_remain": more_remain,
        "selected": len(ids),
        "attempted": processable_attempted,
        "topology_skipped": len(skip_ids),
        "topology_deferred_recorded": topology_deferred_recorded,
        "attempted_by_resource_type": attempted_by_resource_type,
        "succeeded": succeeded,
        "succeeded_by_resource_type": succeeded_by_resource_type,
        "failures": failures,
        "raw_record_ids_sample": ids[:50],
        "duration_ms": elapsed_ms,
        "throughput_rows_per_second": throughput,
        "topology_materialization": topo_meta,
        "topology_skipped_raw_record_ids": sorted(skip_ids),
        "forward_progress": selection_meta,
    }


def resolve_default_bundle_id_for_stub_transform(db: Session, tenant_id: uuid.UUID) -> str | None:
    """Prefer tenant mapping pin → otherwise first inventory bundle eligible for stub transforms."""
    from vector.domains.cortex.canonical.mapping_bundle_registry import (
        build_tenant_mapping_registry_public_document,
    )

    doc = build_tenant_mapping_registry_public_document(db=db, tenant_id=tenant_id)
    pins = doc.get("pins_for_tenant") if isinstance(doc.get("pins_for_tenant"), list) else []
    bundles_list = doc.get("bundles") if isinstance(doc.get("bundles"), list) else []

    def bundle_eligible(bundle_id: str) -> bool:
        row = db.get(CortexMappingBundle, bundle_id)
        return (
            row is not None and row.lifecycle_state in ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM
        )

    for p in pins:
        if not isinstance(p, dict):
            continue
        bid = p.get("bundle_id")
        if isinstance(bid, str) and bid.strip() and bundle_eligible(bid.strip()):
            return bid.strip()

    for row in sorted(bundles_list, key=lambda r: str((r or {}).get("bundle_id") or "")):
        if not isinstance(row, dict):
            continue
        bid = row.get("bundle_id")
        if isinstance(bid, str) and bid.strip() and bundle_eligible(bid.strip()):
            return bid.strip()
    return None


_BACKLOG_DRAIN_BATCH_DEFAULT: Final[int] = int(os.environ.get("CANONICAL_STUB_BACKLOG_DRAIN_BATCH_SIZE", "400"))
_BACKLOG_DRAIN_MAX_BATCHES: Final[int] = int(os.environ.get("CANONICAL_STUB_BACKLOG_DRAIN_MAX_BATCHES", "5000"))
_BACKLOG_DRAIN_FAILURE_SAMPLE_CAP: Final[int] = 300


def drain_stub_materialize_backlog(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    connector: str | None = None,
    resource_type: str | None = None,
    batch_limit: int | None = None,
    pass_index: int = 0,
) -> dict[str, Any]:
    """Forward-progress-aware canonical backlog drain (topology-safe, bounded slices)."""
    from vector.domains.cortex.canonical.forward_progress.drain_runtime import (
        drain_forward_progress_backlog,
    )

    return drain_forward_progress_backlog(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        connector=connector,
        resource_type=resource_type,
        batch_limit=batch_limit,
        pass_index=pass_index,
    )


def materialization_public_dict(mat: CortexCanonicalTransformMaterialization) -> dict[str, Any]:
    rows = sorted(mat.field_lineage, key=lambda r: r.field_path)
    job_id = mat.last_replay_job_id
    return {
        "id": str(mat.id),
        "tenant_id": str(mat.tenant_id),
        "bundle_id": mat.bundle_id,
        "raw_record_id": mat.raw_record_id,
        "last_replay_job_id": str(job_id) if job_id is not None else None,
        "canonical_entity_id": str(canonical_entity_id_for_materialization(mat)),
        "phase04_boundary": dict(DEFAULT_PHASE04_BOUNDARY),
        "canonical_object_kind": mat.canonical_object_kind,
        "logical_key_json": mat.logical_key_json,
        "logical_key_hash": mat.logical_key_hash,
        "emitted_snapshot_json": mat.emitted_snapshot_json,
        "emitted_snapshot_hash": mat.emitted_snapshot_hash,
        "engine_build_ref": mat.engine_build_ref,
        "occurred_at": mat.occurred_at,
        "observed_at": mat.observed_at,
        "canonical_processed_at": mat.canonical_processed_at,
        "source_revision_key": mat.source_revision_key,
        "temporal_ordering_key": mat.temporal_ordering_key,
        "created_at": mat.created_at,
        "confidence_rollup": materialization_confidence_rollup(rows),
        "field_lineage": [
            {
                "field_path": r.field_path,
                "rule_id": r.rule_id,
                "evidence_grade": r.evidence_grade,
                "confidence_class": r.confidence_class,
                "confidence_metadata": r.confidence_metadata,
                "source_paths": r.source_paths,
                "value_snapshot": r.value_snapshot,
            }
            for r in rows
        ],
    }


def list_recent_materializations(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> list[CortexCanonicalTransformMaterialization]:
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
            .options(selectinload(CortexCanonicalTransformMaterialization.field_lineage))
            .order_by(
                nullslast(CortexCanonicalTransformMaterialization.temporal_ordering_key.desc()),
                CortexCanonicalTransformMaterialization.created_at.desc(),
            )
            .limit(lim)
        ).all()
    )
