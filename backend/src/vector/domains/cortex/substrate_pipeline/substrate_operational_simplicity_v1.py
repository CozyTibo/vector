"""Wave 8 — operational simplicity: mutator registry, slice logging, CI verification."""

from __future__ import annotations

import inspect
import logging
import re
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_DIRTY, LEASE_STATUS_STALLED
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease

_LOGGER = logging.getLogger(__name__)

SUBSTRATE_SLICE_COMPLETE_LOG_EVENT: Final[str] = "substrate_slice_complete"
RUNBOOK_REL_PATH_V1: Final[str] = "DOCS/cortex/substrate_queue_runbook.md"
RUNBOOK_MAX_LINES_V1: Final[int] = 120

# Registered ``surface_kind`` values for substrate-facing HTTP/JSON (Wave 8 — ban ad-hoc strings).
REGISTERED_SURFACE_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "substrate_truth_v1",
        "ingest_handoff_v1",
        "graph_substrate_v1",
        "substrate_slice_receipt_v1",
        "operator_rebuild_identities_v1",
        "substrate_ci_gate_report_v1",
        "substrate_soak_v6_v8_v1",
    }
)

SUBSTRATE_MUTATORS_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "id": "ingest",
        "owner": "ingestion.sync_router.execute_connector_sync",
        "trigger": "ingest",
        "mutates": "raw_ingestion_records, connector_checkpoints",
        "observable": "ingest_handoff_v1.dirty_enqueued (after sync completes)",
        "idempotent": "yes — connector checkpoint + raw dedupe keys",
    },
    {
        "id": "dirty",
        "owner": "execution.convergence_dispatch.mark_dirty_and_enqueue_convergence_v1",
        "trigger": "ingest | operator_reset",
        "mutates": "cortex_tenant_convergence_leases",
        "observable": "lease.obligation_epoch, ingest_handoff_v1",
        "idempotent": "yes — obligation_epoch monotonic",
    },
    {
        "id": "materialize",
        "owner": "canonical.forward_progress.drain_forward_progress_backlog",
        "trigger": "slice",
        "mutates": "canonical_materializations, identity_anchors, deferrals",
        "observable": "canonical_lane.outcome, last_canonical_outcome",
        "idempotent": "yes — materialization keys",
    },
    {
        "id": "repair",
        "owner": "identity.identity_substrate_repair_v1.run_identity_substrate_repair_slice_v1",
        "trigger": "slice",
        "mutates": "org_entities, link_candidates, lease repair cursor",
        "observable": "identity_substrate_repair_v1 on lease, substrate_slice_receipt_v1",
        "idempotent": "yes — anchor_offset cursor",
    },
    {
        "id": "promote",
        "owner": "operational_runtime.graph_density_promotion.run_graph_density_promotion_pass_v1",
        "trigger": "slice",
        "mutates": "cortex_org_links (authoritative only)",
        "observable": "graph_substrate_v1.promotion_rule_count, promotion schedule on lease",
        "idempotent": "yes — candidate digest + policy ref",
    },
    {
        "id": "export",
        "owner": "identity.projection_export.run_graph_projection_export_for_pipeline_v1",
        "trigger": "slice",
        "mutates": "ephemeral projection hash on phase receipt / lease graph hash detail",
        "observable": "graph_substrate_v1.isolated_pct, phase receipt hash fields",
        "idempotent": "yes — stable_hash_sha256",
    },
    {
        "id": "revoke_link",
        "owner": "identity.link_ledger.soft_revoke_org_link",
        "trigger": "operator_explicit",
        "mutates": "cortex_org_links.revoked_at",
        "observable": "link explorer + graph_substrate counts",
        "idempotent": "yes — link id",
    },
    {
        "id": "operator_reset",
        "owner": "identity.identity_substrate_operator_v1.operator_rebuild_identities_v1",
        "trigger": "operator_reset",
        "mutates": "lease repair cursor + dirty obligation",
        "observable": "substrate_truth_v1.motion + repair panel",
        "idempotent": "yes — reset cursor to 0",
    },
    {
        "id": "sweep",
        "owner": "convergence.sweep.run_convergence_sweep_v1",
        "trigger": "beat_safety_net",
        "mutates": "enqueue only (mark_dirty_and_enqueue_convergence_v1)",
        "observable": "celery sweep metrics; not a direct org_link writer",
        "idempotent": "yes — per-tenant dirty check",
    },
)

_ORG_LINK_PROMOTION_ALLOWED_V1: Final[frozenset[str]] = frozenset(
    {
        "operational_runtime/graph_density_promotion.py",
        "identity/authoritative_writer.py",
    }
)

_ORG_LINK_REVOKE_ALLOWED_V1: Final[frozenset[str]] = frozenset(
    {
        "identity/link_ledger.py",
    }
)

_SUBSTRATE_COLLAPSED_REPLAY_JOB_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "identity_rebuild_from_anchors",
        "identity_continuity_rebuild",
    }
)


def emit_substrate_slice_complete_v1(
    *,
    tenant_id: Any,
    lease: CortexTenantConvergenceLease,
    manifest: dict[str, Any],
    outcome: str,
) -> None:
    """One structured log line per convergence slice (Wave 8 telemetry collapse)."""
    _LOGGER.info(
        "%s tenant_id=%s outcome=%s lease_status=%s fsm_state=%s phase_cursor=%s "
        "canonical_lane_ran=%s execution_lane_ran=%s obligation_epoch=%s target_epoch=%s",
        SUBSTRATE_SLICE_COMPLETE_LOG_EVENT,
        tenant_id,
        outcome,
        lease.status,
        lease.fsm_state,
        lease.phase_cursor,
        manifest.get("canonical_lane_ran"),
        manifest.get("execution_lane_ran"),
        lease.obligation_epoch,
        lease.target_epoch,
        extra={"substrate_slice": manifest},
    )


def build_operational_panel_v1(
    session: Session,
    *,
    tenant_id: Any,
    lease: CortexTenantConvergenceLease | None,
    canonical_lane: dict[str, Any],
    execution_lane: dict[str, Any],
    runtime_flags: dict[str, Any],
) -> dict[str, Any]:
    """Operator-facing motion predictor + hidden-behavior transparency (Wave 8)."""
    import uuid

    from vector.domains.cortex.execution.dual_lane_worker import (
        is_dual_lane_execution_on_topology_wait_enabled_v1,
    )
    from vector.domains.cortex.substrate_pipeline.canonical_phase_gate import (
        canonical_identity_may_proceed_despite_topology_v1,
    )
    from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform

    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id=tid)
    topology_wait = bool(canonical_lane.get("topology_wait"))
    may_proceed = False
    if bundle_id:
        may_proceed = canonical_identity_may_proceed_despite_topology_v1(
            session, tenant_id=tid, bundle_id=bundle_id
        )
    dual_lane_enabled = bool(runtime_flags.get("cortex_execution_dual_lane_enabled"))
    r1_on = bool(runtime_flags.get("cortex_dual_lane_run_execution_on_topology_wait"))
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    last_manifest = detail.get("last_dual_lane_slice_manifest") or {}
    execution_ran = bool(last_manifest.get("execution_lane_ran"))
    canonical_waiting = str(canonical_lane.get("lane_status") or "") == "WAITING"
    execution_lane_ran_despite_stall = bool(
        dual_lane_enabled
        and r1_on
        and topology_wait
        and execution_ran
        and canonical_waiting
    )
    next_retry_at = None
    if lease is not None and lease.next_attempt_at is not None:
        next_retry_at = lease.next_attempt_at.isoformat()
    hint = predict_next_mutation_hint_v1(
        lease_status=str(lease.status) if lease else None,
        phase_cursor=str(lease.phase_cursor) if lease else None,
        is_dirty=lease.status == LEASE_STATUS_DIRTY if lease else False,
        topology_wait=topology_wait,
        may_proceed_despite_topology=may_proceed,
    )
    return {
        "surface_kind": "substrate_operational_v1",
        "schema_version": 1,
        "next_mutation_hint": hint,
        "next_retry_at": next_retry_at,
        "canonical_topology_gate": {
            "topology_wait": topology_wait,
            "may_proceed_despite_topology": may_proceed,
            "bundle_id": bundle_id,
        },
        "dual_lane": {
            "enabled": dual_lane_enabled,
            "run_execution_on_topology_wait": r1_on,
            "execution_lane_ran_despite_canonical_stall": execution_lane_ran_despite_stall,
            "last_slice_canonical_ran": last_manifest.get("canonical_lane_ran"),
            "last_slice_execution_ran": last_manifest.get("execution_lane_ran"),
        },
        "execution_lane_status": execution_lane.get("lane_status"),
        "canonical_lane_status": canonical_lane.get("lane_status"),
    }


def predict_next_mutation_hint_v1(
    *,
    lease_status: str | None,
    phase_cursor: str | None,
    is_dirty: bool,
    topology_wait: bool,
    may_proceed_despite_topology: bool,
) -> str:
    if lease_status == LEASE_STATUS_STALLED:
        return "Clear STALLED (inspect last_error) then mark dirty or operator Repair."
    if is_dirty:
        return "Convergence worker will run dual-lane slice (canonical then execution/repair/promote)."
    if topology_wait and not may_proceed_despite_topology:
        return "Canonical topology_wait — materialize/deferrals must drain before identity repair advances."
    if topology_wait and may_proceed_despite_topology:
        return "Canonical waiting but execution lane may proceed (R1) — repair/promote on next slice."
    if phase_cursor:
        return f"Continue execution lane at phase_cursor={phase_cursor} on next slice."
    return "Trigger ingest sync or operator Repair to mark dirty and enqueue convergence."


def is_substrate_replay_job_kind_collapsed_v1(job_kind: str) -> bool:
    return job_kind.strip() in _SUBSTRATE_COLLAPSED_REPLAY_JOB_KINDS_V1


def verify_org_link_writes_scope_v1() -> list[str]:
    """Production identity/operational_runtime must not promote links outside promotion + revoke."""
    errors: list[str] = []
    cortex_root = Path(__file__).resolve().parents[1]
    promote_token = "promote_candidate_to_authoritative_link"
    for path in cortex_root.rglob("*.py"):
        if "tests" in path.parts or "archive" in path.parts:
            continue
        rel = path.relative_to(cortex_root).as_posix()
        text = path.read_text(encoding="utf-8")
        if f"{promote_token}(" not in text:
            continue
        if rel in _ORG_LINK_PROMOTION_ALLOWED_V1:
            continue
        if rel.endswith("authoritative_writer.py") or rel == "identity/__init__.py":
            continue
        errors.append(f"org_link_promotion_outside_pass:{rel}")
    return errors


def verify_slack_apply_no_bare_dirty_v1(*, repo_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    root = repo_root
    if root is None:
        from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
            discover_repo_root_v1,
        )

        root = discover_repo_root_v1()
    if root is None:
        return errors
    admin = root / "backend/src/vector/api/http/routes/admin.py"
    if not admin.is_file():
        return errors
    chunk = admin.read_text(encoding="utf-8")
    if "def admin_slack_channels_ingest_apply" in chunk:
        section = chunk.split("def admin_slack_channels_ingest_apply", 1)[1].split("\n    @r.", 1)[0]
        if "mark_tenant_dirty_v1" in section:
            errors.append("slack_channel_apply_still_marks_dirty_without_convergence_dispatch")
    return errors


def verify_failure_remediation_blocks_substrate_replay_v1() -> list[str]:
    from vector.domains.cortex.identity import failure_remediation as fr_mod

    src = inspect.getsource(fr_mod.validate_org_remediation)
    if "is_substrate_replay_job_kind_collapsed_v1" not in src:
        errors = ["failure_remediation_missing_substrate_replay_collapse"]
    else:
        errors = []
    if "org_link_replay_retry" not in src:
        errors.append("failure_remediation_missing_org_link_replay_retry_path")
    return errors


def verify_substrate_slice_complete_logging_v1() -> list[str]:
    from vector.domains.cortex.execution import dual_lane_worker as dl_mod

    src = inspect.getsource(dl_mod)
    if "emit_substrate_slice_complete_v1" not in src:
        return ["dual_lane_missing_substrate_slice_complete_log"]
    if "_return_dual_lane_slice_v1" not in src:
        return ["dual_lane_missing_slice_return_helper"]
    return []


def verify_runbook_covers_mutators_v1(*, repo_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    root = repo_root
    if root is None:
        from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
            discover_repo_root_v1,
        )

        root = discover_repo_root_v1()
    if root is None:
        return errors
    path = root / RUNBOOK_REL_PATH_V1
    if not path.is_file():
        return ["missing_substrate_runbook"]
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) > RUNBOOK_MAX_LINES_V1:
        errors.append(f"runbook_exceeds_max_lines:{len(lines)}>{RUNBOOK_MAX_LINES_V1}")
    for mut in SUBSTRATE_MUTATORS_V1:
        owner_short = mut["owner"].split(".")[-1]
        if owner_short not in text and mut["owner"] not in text:
            errors.append(f"runbook_missing_mutator:{mut['id']}")
    if "substrate_slice_complete" not in text:
        errors.append("runbook_missing_substrate_slice_complete")
    if "predict_next_mutation" not in text and "next_mutation_hint" not in text:
        errors.append("runbook_missing_mutation_predictor")
    return errors


def verify_wave8_operational_simplicity_v1(*, repo_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    errors.extend(verify_org_link_writes_scope_v1())
    errors.extend(verify_slack_apply_no_bare_dirty_v1(repo_root=repo_root))
    errors.extend(verify_failure_remediation_blocks_substrate_replay_v1())
    errors.extend(verify_substrate_slice_complete_logging_v1())
    errors.extend(verify_runbook_covers_mutators_v1(repo_root=repo_root))
    from vector.domains.cortex.substrate_pipeline import substrate_truth_v1 as truth_mod

    if "build_operational_panel_v1" not in inspect.getsource(truth_mod.build_substrate_truth_v1):
        errors.append("substrate_truth_missing_operational_panel")
    return errors
