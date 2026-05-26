"""P2-B — event-driven execution triggers (ingest dirty, identity promotion, graph-hash walks)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.convergence_dispatch import mark_dirty_and_enqueue_convergence_v1
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.identity.projection_export import build_org_graph_projection_export_document
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
    schedule_octs_walks_for_tenant_v1,
)

_LOGGER = logging.getLogger(__name__)

P2_B_STEP = "2b_event_triggers"
DETAIL_KEY_EVENT_TRIGGERS_V1: Final[str] = "event_triggers"
DETAIL_KEY_LAST_GRAPH_HASH_V1: Final[str] = "last_graph_projection_stable_hash_sha256"
DETAIL_KEY_LAST_GRAPH_ISOLATED_PCT_V1: Final[str] = "last_graph_isolated_pct_v1"

EVENT_TRIGGER_INGEST_V1: Final[str] = "post_ingestion_mark_dirty"
EVENT_TRIGGER_IDENTITY_PROMOTION_V1: Final[str] = "identity_projection_promotion"
EVENT_TRIGGER_GRAPH_HASH_V1: Final[str] = "graph_projection_hash_changed"


def is_execution_event_triggers_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_execution_event_triggers_enabled)
    except Exception:  # noqa: BLE001
        return True


def is_substrate_walk_schedule_skipped_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_substrate_skip_walk_schedule_v1)
    except Exception:  # noqa: BLE001
        return True


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_event_triggers_detail(lease: Any) -> dict[str, Any]:
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    raw = detail.get(DETAIL_KEY_EVENT_TRIGGERS_V1)
    return dict(raw) if isinstance(raw, dict) else {}


def _persist_event_triggers_detail(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    patch: dict[str, Any],
) -> dict[str, Any]:
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None:
        return {"persisted": False, "reason": "no_lease"}
    detail = dict(lease.detail_json or {})
    triggers = _read_event_triggers_detail(lease)
    triggers.update(patch)
    triggers["updated_at"] = _now_iso()
    detail[DETAIL_KEY_EVENT_TRIGGERS_V1] = triggers
    lease.detail_json = detail
    session.flush()
    return triggers


def trigger_post_ingestion_execution_v1(
    *,
    tenant_id: uuid.UUID,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Ingest completion: mark tenant dirty + enqueue convergence slice."""
    if not is_execution_event_triggers_enabled_v1():
        return {"triggered": False, "reason": "event_triggers_disabled"}
    out = mark_dirty_and_enqueue_convergence_v1(
        tenant_id=tenant_id,
        reason=reason,
        telemetry_trigger=f"{EVENT_TRIGGER_INGEST_V1}:{reason}",
    )
    return {
        "trigger": EVENT_TRIGGER_INGEST_V1,
        "triggered": bool(out.get("scheduled")),
        "dispatch": out,
    }


def trigger_identity_promotion_after_substrate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    substrate: dict[str, Any],
) -> dict[str, Any]:
    """Wave 1: promotion is owned by ``run_identity_substrate_repair_slice_v1`` only."""
    _ = substrate
    if not is_execution_event_triggers_enabled_v1():
        return {"triggered": False, "reason": "event_triggers_disabled"}
    manifest = {
        "trigger": EVENT_TRIGGER_IDENTITY_PROMOTION_V1,
        "triggered": False,
        "at": _now_iso(),
        "promotion_scheduled": False,
        "schedule_reason": "delegated_to_repair_slice_v1",
        "delegated_to": "run_identity_substrate_repair_slice_v1",
    }
    _persist_event_triggers_detail(
        session,
        tenant_id=tenant_id,
        patch={"last_identity_promotion": manifest},
    )
    return {"trigger": EVENT_TRIGGER_IDENTITY_PROMOTION_V1, **manifest, "promotion": None}


def trigger_graph_hash_walk_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    graph_projection_stable_hash: str | None,
    pipeline_run_id: uuid.UUID | None = None,
    force_schedule: bool = False,
) -> dict[str, Any]:
    """When authoritative graph projection hash changes, schedule OCTS walks (P2-B)."""
    new_hash = (graph_projection_stable_hash or "").strip()
    if not is_execution_event_triggers_enabled_v1():
        return {
            "trigger": EVENT_TRIGGER_GRAPH_HASH_V1,
            "triggered": False,
            "reason": "event_triggers_disabled",
            "graph_hash": new_hash or None,
        }

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    prior = str(detail.get(DETAIL_KEY_LAST_GRAPH_HASH_V1) or "").strip()
    changed = bool(new_hash) and new_hash != prior

    schedule_target_run_id = pipeline_run_id
    fresh_run: dict[str, Any] | None = None
    if changed and pipeline_run_id is not None:
        from vector.domains.cortex.substrate_pipeline.post_ingestion_fresh_pipeline_run import (
            start_fresh_pipeline_run_after_graph_change_v1,
        )

        fresh_run = start_fresh_pipeline_run_after_graph_change_v1(
            session,
            tenant_id=tenant_id,
            graph_projection_stable_hash=new_hash,
            prior_pipeline_run_id=pipeline_run_id,
        )
        if fresh_run.get("started") and fresh_run.get("fresh_pipeline_run_id"):
            schedule_target_run_id = uuid.UUID(str(fresh_run["fresh_pipeline_run_id"]))

    schedule_out: dict[str, Any] | None = None
    skip_walks = is_substrate_walk_schedule_skipped_v1() and not force_schedule
    if (changed or force_schedule) and new_hash and not skip_walks:
        schedule_out = schedule_octs_walks_for_tenant_v1(
            tenant_id=tenant_id,
            trigger=TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
            pipeline_run_id=schedule_target_run_id,
            graph_projection_stable_hash=new_hash,
            force=force_schedule,
            session=session,
        )

    manifest: dict[str, Any] = {
        "trigger": EVENT_TRIGGER_GRAPH_HASH_V1,
        "triggered": changed or force_schedule,
        "at": _now_iso(),
        "prior_hash": prior or None,
        "new_hash": new_hash or None,
        "hash_changed": changed,
        "walk_schedule": schedule_out,
        "walks_scheduled": bool((schedule_out or {}).get("scheduled")),
        "substrate_skip_walk_schedule_v1": skip_walks,
    }
    if skip_walks:
        manifest["walk_schedule_skipped_reason"] = "cortex_substrate_skip_walk_schedule_v1"
    if fresh_run and fresh_run.get("started") and fresh_run.get("fresh_pipeline_run_id"):
        manifest["fresh_pipeline_run_id"] = fresh_run["fresh_pipeline_run_id"]
        manifest["superseded_pipeline_run_ids"] = list(fresh_run.get("superseded_pipeline_run_ids") or [])
        manifest["resume_from_phase"] = fresh_run.get("resume_from_phase")
        manifest["no_phase_mirror"] = True

    if lease is not None and new_hash:
        lease_detail = dict(lease.detail_json or {})
        lease_detail[DETAIL_KEY_LAST_GRAPH_HASH_V1] = new_hash
        triggers = _read_event_triggers_detail(lease)
        triggers["last_graph_hash_walk"] = manifest
        triggers["updated_at"] = _now_iso()
        lease_detail[DETAIL_KEY_EVENT_TRIGGERS_V1] = triggers
        lease.detail_json = lease_detail
        session.flush()

    if changed:
        _LOGGER.info(
            "graph_hash_changed_walk_schedule tenant_id=%s prior=%s new=%s scheduled=%s fresh_run=%s",
            tenant_id,
            prior[:12] if prior else "—",
            new_hash[:12],
            bool((schedule_out or {}).get("scheduled")),
            (fresh_run or {}).get("fresh_pipeline_run_id"),
        )

    return manifest


def resolve_live_graph_projection_hash_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> str | None:
    export_doc = build_org_graph_projection_export_document(session, tenant_id=tenant_id)
    return str(export_doc.get("stable_hash_sha256") or "").strip() or None


def build_event_triggers_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin / proof surface for P2-B trigger state."""
    from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
        build_substrate_traversal_scheduling_catalog_v1,
    )

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    live_hash = resolve_live_graph_projection_hash_v1(session, tenant_id=tenant_id)
    stored_hash = str(detail.get(DETAIL_KEY_LAST_GRAPH_HASH_V1) or "").strip() or None
    catalog = build_substrate_traversal_scheduling_catalog_v1()
    return {
        "surface_kind": "execution_event_triggers",
        "event_triggers_enabled": is_execution_event_triggers_enabled_v1(),
        "live_graph_projection_stable_hash": live_hash,
        "stored_graph_projection_stable_hash": stored_hash,
        "graph_hash_in_sync": bool(live_hash and stored_hash and live_hash == stored_hash),
        "event_triggers_detail": _read_event_triggers_detail(lease),
        "schedule_triggers": list(catalog.get("schedule_triggers") or []),
        "graph_hash_trigger_registered": TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1
        in (catalog.get("schedule_triggers") or []),
    }
