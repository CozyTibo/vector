"""Phase summary + explorer builders for ``GET …/cortex/pipeline/phases/{phase}/*``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.canonical_phase_admin_lite import (
    build_canonical_phase_summary_metrics_v1,
)
from vector.domains.cortex.canonical.transform_runtime import (
    list_recent_materializations,
    materialization_public_dict,
)
from vector.domains.cortex.completeness.graph_completeness_projection import (
    project_graph_completeness_v1,
)
from vector.domains.cortex.completeness.tcre_completeness_projection import (
    project_tcre_completeness_v1,
)
from vector.domains.cortex.completeness.traversal_completeness_projection import (
    project_traversal_completeness_v1,
)
from vector.domains.cortex.identity.control_plane import build_identity_control_plane
from vector.domains.cortex.identity.org_ambiguity import count_open_org_ambiguity_records
from vector.domains.cortex.identity.org_entities import list_org_entities, org_entity_public_dict
from vector.domains.cortex.identity.link_explorer import list_org_link_explorer_rows
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import list_raw_records_for_connector
from vector.domains.cortex.pipeline.pipeline_admin_overview import build_pipeline_overview_phases_v1
from vector.domains.cortex.reasoning.runtime import (
    build_reasoning_runtime_health_v1,
    list_reconstruction_jobs_v1,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    build_retrieval_coverage_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    list_synthesis_artifacts_for_tenant_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    build_synthesis_overview_catalog_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.settings import Settings

_VALID_PHASES = frozenset(
    {
        "ingestion",
        "canonical",
        "identity",
        "graph",
        "reconstruction",
        "retrieval",
        "synthesis",
    }
)

_EXPLORER_COLUMNS: dict[str, list[str]] = {
    "ingestion": ["connector", "external_id", "ingested_at", "resource_type", "payload_preview"],
    "canonical": ["canonical_type", "source", "entity", "updated_at", "status"],
    "identity": ["kind", "display", "anchors", "confidence"],
    "graph": [
        "edge_type",
        "promotion_rule",
        "source",
        "target",
        "created_at",
        "evidence",
        "continuity",
    ],
    "reconstruction": ["job_id", "status", "created_at", "scope"],
    "retrieval": ["index_type", "coverage", "object_count", "status"],
    "synthesis": ["artifact_type", "scope", "created_at", "status"],
}


def _assert_phase(phase: str) -> str:
    key = (phase or "").strip().lower()
    if key not in _VALID_PHASES:
        msg = f"unsupported_phase:{phase}"
        raise ValueError(msg)
    return key


def _phase_row_from_phases_payload(phases_payload: dict[str, Any], phase: str) -> dict[str, Any]:
    phase_row = next((p for p in phases_payload["phases"] if p["phase"] == phase), None)
    if phase_row is None:
        raise ValueError("phase_not_in_overview")
    return phase_row


def _summary_envelope_from_phase_row(
    phases_payload: dict[str, Any],
    phase: str,
    *,
    extra: dict[str, Any],
) -> dict[str, Any]:
    phase_row = _phase_row_from_phases_payload(phases_payload, phase)
    return {
        "surface_kind": "phase_summary",
        "phase": phase,
        "tenant_id": phases_payload["tenant_id"],
        "status": phase_row["status"],
        "processed_count": phase_row.get("processed_count"),
        "backlog_count": phase_row.get("backlog_count"),
        "last_success_at": phase_row.get("last_success_at"),
        "blockers": phase_row.get("blockers") or [],
        **extra,
    }


def _build_phase_summary_extra_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    phase: str,
) -> dict[str, Any]:
    key = _assert_phase(phase)

    if key == "ingestion":
        ing = build_cortex_ingestion_admin_overview(session, settings, tenant_id)
        return {
            "connectors": ing.get("connectors") or [],
            "checkpoints": [
                {
                    "connector": row["connector"],
                    "checkpoint_last_incremental_at": row.get("checkpoint_last_incremental_at"),
                }
                for row in ing.get("connectors") or []
            ],
        }

    if key == "canonical":
        return build_canonical_phase_summary_metrics_v1(session, tenant_id=tenant_id)

    if key == "identity":
        cp = build_identity_control_plane(session, tenant_id=tenant_id)
        cards = cp.get("cards") or {}
        certification_warnings: list[str] = []
        open_amb = int((cards.get("ambiguous_identities") or {}).get("value") or 0)
        pending = int((cards.get("pending_merges") or {}).get("value") or 0)
        bundle_gaps = int((cards.get("bundle_equivalence_gaps") or {}).get("value") or 0)
        if open_amb > 0:
            certification_warnings.append(f"{open_amb} unresolved org ambiguity record(s)")
        if pending > 0:
            certification_warnings.append(f"{pending} merge proposal(s) awaiting decision")
        if bundle_gaps > 0:
            certification_warnings.append(f"{bundle_gaps} bundle equivalence gap(s)")
        if count_open_org_ambiguity_records(session, tenant_id=tenant_id) > open_amb:
            certification_warnings.append("Additional open ambiguity cases in registry")
        return {
            "cards": cards,
            "certification_warnings": certification_warnings,
            "freshness_label": cp.get("freshness_label"),
            "computed_at": cp.get("computed_at"),
        }

    if key == "graph":
        from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
            build_semantic_readiness_v1,
        )

        graph_env = project_graph_completeness_v1(session, tenant_id=tenant_id)
        trav_env = project_traversal_completeness_v1(session, tenant_id=tenant_id)
        metrics = dict(graph_env.get("metrics") or {})
        truth = dict(build_semantic_readiness_v1(session, tenant_id=tenant_id).get("graph_truth") or {})
        auth_rows = int(truth.get("auth_edge_rows") or metrics.get("authoritative_link_count") or 0)
        unique_pairs = int(truth.get("unique_auth_pairs") or 0)
        return {
            "graph_metrics": metrics,
            "graph_truth": truth,
            "traversal_substrate_state": trav_env.get("substrate_state"),
            "node_count": int(metrics.get("entity_count") or graph_env.get("total_objects") or 0),
            "edge_count": auth_rows,
            "edge_count_deprecated_primary": True,
            "auth_edge_rows": auth_rows,
            "auth_edge_rows_deprecated_primary": True,
            "primary_metric_key": str(truth.get("primary_metric_key") or "unique_auth_pairs"),
            "unique_auth_pairs": unique_pairs,
            "dup_factor": truth.get("dup_factor"),
            "dup_factor_severity": truth.get("dup_factor_severity"),
            "promotion_rule_count": int(truth.get("promotion_rule_count") or 0),
            "promotions_by_rule_id": list(truth.get("promotions_by_rule_id") or []),
            "orphan_count": int(metrics.get("orphan_node_count") or graph_env.get("unresolved_count") or 0),
            "degraded_count": int(graph_env.get("degraded_count") or 0),
        }

    if key == "reconstruction":
        health = build_reasoning_runtime_health_v1(session, tenant_id=tenant_id)
        return {
            "queue_depth": int(health.get("queue_depth_proxy") or 0),
            "failed_jobs": int(health.get("failed_job_count") or 0),
            "job_status_counts": dict(health.get("job_status_counts") or {}),
            "last_successful_job": health.get("last_successful_job"),
            "canonical_materialization_count": health.get("canonical_materialization_count"),
        }

    if key == "retrieval":
        coverage = build_retrieval_coverage_catalog_v1(session, tenant_id=tenant_id)
        return {
            "indexed_count": coverage.get("indexed_count"),
            "coverage_percent": coverage.get("coverage_percent"),
            "published_index_epoch": coverage.get("published_index_epoch"),
            "substrate_state": coverage.get("substrate_state"),
            "index_lag_epochs": coverage.get("index_lag_epochs"),
        }

    syn_overview = build_synthesis_overview_catalog_v1(session, tenant_id=tenant_id)
    return {
        "eligible_scopes": syn_overview.get("eligible_scopes"),
        "synthesized_scopes": syn_overview.get("synthesized_scopes"),
        "coverage_percent": syn_overview.get("coverage_percent"),
        "health_strip": syn_overview.get("health_strip"),
    }


def _explorer_envelope(
    *,
    phase: str,
    tenant_id: uuid.UUID,
    items: list[dict[str, Any]],
    truncated: bool,
    total: int,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    return {
        "surface_kind": "phase_explorer",
        "phase": phase,
        "tenant_id": str(tenant_id),
        "columns": _EXPLORER_COLUMNS[phase],
        "items": items,
        "truncated": truncated,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def build_phase_summary_detail_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    phase: str,
) -> dict[str, Any]:
    """Phase-specific summary payload without recomputing the full pipeline overview."""
    key = _assert_phase(phase)
    extra = _build_phase_summary_extra_v1(
        session, settings, tenant_id=tenant_id, phase=key
    )
    return {
        "surface_kind": "phase_summary_detail",
        "phase": key,
        "tenant_id": str(tenant_id),
        **extra,
    }


def build_phase_summary_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    phase: str,
) -> dict[str, Any]:
    key = _assert_phase(phase)
    phases_payload = build_pipeline_overview_phases_v1(session, tenant_id=tenant_id)
    extra = _build_phase_summary_extra_v1(
        session, settings, tenant_id=tenant_id, phase=key
    )
    return _summary_envelope_from_phase_row(phases_payload, key, extra=extra)


def build_phase_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    phase: str,
    limit: int = 50,
    offset: int = 0,
    connector: str | None = None,
    resource_type: str | None = None,
    search_query: str | None = None,
    include_health_rows: bool = False,
) -> dict[str, Any]:
    key = _assert_phase(phase)
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))

    if key == "ingestion":
        conn = (connector or "slack").strip()
        items, truncated, total = list_raw_records_for_connector(
            session,
            tenant_id,
            conn,
            limit=lim,
            offset=off,
            resource_type=resource_type,
            search_query=search_query,
            include_health_rows=include_health_rows,
        )
        rows = []
        for row in items:
            rows.append(
                {
                    "connector": conn,
                    "external_id": row.get("external_id"),
                    "ingested_at": _iso_timestamp(row.get("fetched_at")),
                    "resource_type": row.get("resource_type"),
                    "payload_preview": _payload_preview(row.get("payload_body")),
                    "raw_record_id": row.get("id"),
                    "evidence": row,
                }
            )
        return _explorer_envelope(
            phase=key,
            tenant_id=tenant_id,
            items=rows,
            truncated=truncated,
            total=total,
            limit=lim,
            offset=off,
        )

    if key == "canonical":
        mats = list_recent_materializations(session, tenant_id=tenant_id, limit=lim + off)
        mat_page = mats[off : off + lim]
        rows = []
        for mat in mat_page:
            pub = materialization_public_dict(mat)
            rows.append(
                {
                    "canonical_type": pub.get("canonical_object_kind"),
                    "source": pub.get("source_revision_key") or pub.get("bundle_id"),
                    "entity": pub.get("canonical_entity_id"),
                    "updated_at": _iso_timestamp(pub.get("canonical_processed_at"))
                    or _iso_timestamp(pub.get("created_at")),
                    "status": "materialized",
                    "materialization_id": pub.get("id"),
                    "evidence": pub,
                }
            )
        return _explorer_envelope(
            phase=key,
            tenant_id=tenant_id,
            items=rows,
            truncated=len(mats) > off + lim,
            total=len(mats),
            limit=lim,
            offset=off,
        )

    if key == "identity":
        entities = list_org_entities(session, tenant_id=tenant_id, limit=lim + off)
        entity_page = entities[off : off + lim]
        rows = []
        for ent in entity_page:
            pub = org_entity_public_dict(ent)
            meta = dict(pub.get("metadata_json") or {})
            display = (
                str(meta.get("display_name") or meta.get("label") or "")
                or str(pub.get("identity_key_fingerprint") or "")[:16]
            )
            rows.append(
                {
                    "kind": pub.get("entity_kind"),
                    "display": display or pub.get("id"),
                    "anchors": pub.get("identity_key_fingerprint"),
                    "confidence": str(meta.get("confidence_class") or "n/a"),
                    "entity_id": pub.get("id"),
                    "evidence": pub,
                }
            )
        return _explorer_envelope(
            phase=key,
            tenant_id=tenant_id,
            items=rows,
            truncated=len(entities) > off + lim,
            total=len(entities),
            limit=lim,
            offset=off,
        )

    if key == "graph":
        link_filters = (
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.link_authority == "authoritative",
            CortexOrgLink.revoked_at.is_(None),
        )
        total = int(
            session.scalar(select(func.count()).select_from(CortexOrgLink).where(*link_filters)) or 0
        )
        links = list(
            session.scalars(
                select(CortexOrgLink)
                .where(*link_filters)
                .order_by(CortexOrgLink.created_at.desc())
                .offset(off)
                .limit(lim + 1)
            ).all()
        )
        truncated = len(links) > lim
        if truncated:
            links = links[:lim]
        explorer = list_org_link_explorer_rows(
            session, tenant_id=tenant_id, limit=lim, authoritative_only=True
        )
        explorer_by_id = {str(r.get("link_id")): r for r in explorer}
        rows = []
        for link in links:
            ex = explorer_by_id.get(str(link.id)) or {}
            rows.append(
                {
                    "edge_type": link.link_type,
                    "promotion_rule": link.rule_id or ex.get("rule_version") or "—",
                    "source": str(link.source_entity_id),
                    "target": str(link.target_entity_id),
                    "created_at": link.created_at.isoformat() if link.created_at else None,
                    "evidence": ex.get("evidence_count", 0),
                    "continuity": ex.get("replay_state") or ex.get("drift_class") or "n/a",
                    "link_id": str(link.id),
                    "evidence_detail": {
                        **ex,
                        "link_authority": link.link_authority,
                        "promoted_from_candidate_id": (
                            str(link.promoted_from_candidate_id)
                            if link.promoted_from_candidate_id
                            else None
                        ),
                        "rule_id": link.rule_id,
                        "link_class": link.link_class,
                        "valid_from": link.valid_from.isoformat() if link.valid_from else None,
                        "valid_to": link.valid_to.isoformat() if link.valid_to else None,
                        "evidence_raw_record_ids": link.evidence_raw_record_ids or [],
                        "metadata_json": link.metadata_json or {},
                    },
                }
            )
        return _explorer_envelope(
            phase=key,
            tenant_id=tenant_id,
            items=rows,
            truncated=truncated,
            total=total,
            limit=lim,
            offset=off,
        )

    if key == "reconstruction":
        jobs = list_reconstruction_jobs_v1(session, tenant_id=tenant_id, limit=lim + off)
        job_page = jobs[off : off + lim]
        rows = []
        for job in job_page:
            raw_scope = job.get("scope_json")
            scope: dict[str, Any] = raw_scope if isinstance(raw_scope, dict) else {}
            rows.append(
                {
                    "job_id": job.get("job_id"),
                    "status": job.get("status"),
                    "created_at": job.get("created_at"),
                    "scope": str(scope.get("materialization_limit") or scope.get("scope") or "default"),
                    "detail_path": f"/admin/tenants/{tenant_id}/cortex/reconstruction/jobs/{job.get('job_id')}",
                    "evidence": job,
                }
            )
        return _explorer_envelope(
            phase=key,
            tenant_id=tenant_id,
            items=rows,
            truncated=len(jobs) > off + lim,
            total=len(jobs),
            limit=lim,
            offset=off,
        )

    if key == "retrieval":
        coverage = build_retrieval_coverage_catalog_v1(session, tenant_id=tenant_id)
        published = coverage.get("published_index_epoch")
        grouped = session.execute(
            select(
                CortexRetrievalIndexEntry.index_epoch,
                CortexRetrievalIndexEntry.index_kind,
                func.count().label("row_count"),
            )
            .where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
            .group_by(
                CortexRetrievalIndexEntry.index_epoch,
                CortexRetrievalIndexEntry.index_kind,
            )
            .order_by(CortexRetrievalIndexEntry.index_epoch.desc())
        ).all()
        all_rows: list[dict[str, Any]] = [
            {
                "index_type": str(epoch or "unknown"),
                "coverage": coverage.get("coverage_percent"),
                "object_count": int(cnt),
                "status": str(kind or "unknown"),
                "published": epoch == published,
                "evidence": {"index_epoch": epoch, "index_kind": kind, "row_count": int(cnt)},
            }
            for epoch, kind, cnt in grouped
        ]
        retrieval_page = all_rows[off : off + lim]
        return _explorer_envelope(
            phase=key,
            tenant_id=tenant_id,
            items=retrieval_page,
            truncated=len(all_rows) > off + lim,
            total=len(all_rows),
            limit=lim,
            offset=off,
        )

    artifacts = list_synthesis_artifacts_for_tenant_v1(session, tenant_id=tenant_id, limit=lim + off)
    art_page = artifacts[off : off + lim]
    rows = []
    for art in art_page:
        rows.append(
            {
                "artifact_type": art.get("artifact_kind") or art.get("artifact_type"),
                "scope": art.get("retrieval_lookup_id") or art.get("synthesis_publication_epoch") or "—",
                "created_at": _iso_timestamp(art.get("created_at")),
                "status": "published" if art.get("published") else "draft",
                "artifact_id": art.get("artifact_id") or art.get("id"),
                "evidence": art,
            }
        )
    return _explorer_envelope(
        phase=key,
        tenant_id=tenant_id,
        items=rows,
        truncated=len(artifacts) > off + lim,
        total=len(artifacts),
        limit=lim,
        offset=off,
    )


def _payload_preview(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    keys = list(body.keys())[:6]
    return ", ".join(keys) if keys else "(empty)"


def _iso_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)
