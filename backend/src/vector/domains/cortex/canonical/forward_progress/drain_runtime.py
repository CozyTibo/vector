"""Forward-progress-aware canonical backlog drain (topology-safe)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_FAILED,
    CANONICAL_OUTCOME_IDLE,
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_PROGRESSED,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
    FORWARD_PROGRESS_SCHEMA_VERSION,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import (
    count_deferrals,
    release_deferrals_with_materialized_parents,
    summarize_deferral_pressure,
)
from vector.domains.cortex.canonical.forward_progress.metrics import build_forward_progress_metrics
from vector.domains.cortex.canonical.forward_progress.pass_fairness import (
    count_passes_off_cooldown,
    parse_pass_cooldown_until,
    parse_pass_topology_stall_counts,
    record_pass_topology_stall,
    serialize_pass_cooldown_until,
    serialize_pass_topology_stall_counts,
)
from vector.domains.cortex.canonical.forward_progress.pass_registry import all_canonical_passes_fair_rotation
from vector.domains.cortex.canonical.transform_runtime import (
    MaterializeError,
    materialize_stub_backlog,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.settings import Settings, get_settings


def _classify_drain_outcome(
    *,
    total_succeeded: int,
    total_failed_rows: int,
    full_rotation_topology_stall: bool,
    candidate_more_remain: bool,
    untreated_estimate: int,
    hit_slice_cap: bool,
) -> str:
    if total_failed_rows > 0 and total_succeeded == 0:
        return CANONICAL_OUTCOME_FAILED
    if total_succeeded > 0 and (candidate_more_remain or untreated_estimate > 0 or hit_slice_cap):
        return CANONICAL_OUTCOME_PARTIAL_PROGRESS
    if total_succeeded > 0:
        return CANONICAL_OUTCOME_PROGRESSED
    if full_rotation_topology_stall and (candidate_more_remain or untreated_estimate > 0):
        return CANONICAL_OUTCOME_TOPOLOGY_WAIT
    if total_succeeded == 0 and not candidate_more_remain and untreated_estimate == 0:
        return CANONICAL_OUTCOME_IDLE
    if candidate_more_remain or untreated_estimate > 0:
        return CANONICAL_OUTCOME_TOPOLOGY_WAIT
    return CANONICAL_OUTCOME_IDLE


def drain_forward_progress_backlog(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    connector: str | None = None,
    resource_type: str | None = None,
    batch_limit: int | None = None,
    pass_index: int = 0,
    pass_cooldowns: dict[str, datetime] | None = None,
    pass_stall_counts: dict[str, int] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Drain canonical backlog with pass-local fairness and success-first slice accounting."""
    cfg = settings or get_settings()
    from vector.domains.cortex.canonical.transform_runtime import (
        ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM,
        _BACKLOG_DRAIN_BATCH_DEFAULT,
    )

    lim = batch_limit if batch_limit is not None else _BACKLOG_DRAIN_BATCH_DEFAULT
    lim = max(1, min(int(lim), 2000))
    max_batches = max(1, int(cfg.cortex_canonical_forward_progress_max_batches_per_slice))
    base_cooldown_s = max(5, int(cfg.cortex_canonical_topology_wait_cooldown_seconds))
    max_pass_cooldown_s = max(
        base_cooldown_s,
        int(getattr(cfg, "cortex_canonical_pass_cooldown_max_seconds", base_cooldown_s * 4)),
    )

    bundle = db.get(CortexMappingBundle, bundle_id)
    if bundle is None:
        raise MaterializeError("unknown_bundle")
    if bundle.lifecycle_state not in ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM:
        raise MaterializeError(f"bundle_not_transformable:{bundle.lifecycle_state}")

    now = datetime.now(UTC)
    pass_cooldowns = dict(pass_cooldowns or {})
    pass_stall_counts = dict(pass_stall_counts or {})

    failure_samples: list[dict[str, Any]] = []
    total_topology_deferred = 0
    total_succeeded = 0
    total_failed_rows = 0
    total_topology_skipped = 0
    batches_run = 0
    productive_batches = 0
    topology_only_batches = 0
    pair_labels: list[str] = []
    throughput_rows_per_second_samples: list[float] = []
    pass_productivity: dict[str, int] = {}
    pass_topology_skips: dict[str, int] = {}
    drain_started_at = now
    cursor_pass_index = int(pass_index)
    full_rotation_topology_stall = False
    pass_rotations_without_success = 0
    pass_count = len(all_canonical_passes_fair_rotation()) or 1
    scoped_drain = bool(
        (connector and connector.strip()) or (resource_type and resource_type.strip())
    )
    last_batch_meta: dict[str, Any] = {}
    candidate_more_remain = False
    raw_batch: dict[str, Any] = {}

    release_deferrals_with_materialized_parents(db, tenant_id=tenant_id, bundle_id=bundle_id)

    while batches_run < max_batches:
        raw_batch = materialize_stub_backlog(
            db,
            tenant_id=tenant_id,
            bundle_id=bundle_id,
            connector=connector,
            resource_type=resource_type,
            batch_limit=lim,
            dry_run=False,
            pass_index=cursor_pass_index,
            topology_cooldown_seconds=base_cooldown_s,
            pass_cooldowns=pass_cooldowns,
            pass_stall_counts=pass_stall_counts,
            permanent_orphan_threshold=int(
                getattr(
                    cfg,
                    "cortex_canonical_permanent_orphan_deferral_threshold",
                    5,
                )
            ),
        )
        last_batch_meta = (
            raw_batch.get("forward_progress")
            if isinstance(raw_batch.get("forward_progress"), dict)
            else {}
        )
        if isinstance(last_batch_meta.get("pass_index_next"), int):
            cursor_pass_index = int(last_batch_meta["pass_index_next"])

        pass_key = str(last_batch_meta.get("pass_key") or "")

        if not pair_labels and raw_batch.get("stub_resource_pairs_selected"):
            pair_labels = list(raw_batch["stub_resource_pairs_selected"])

        selected_n = int(raw_batch.get("selected") or 0)
        attempted_n = int(raw_batch.get("attempted") or 0)
        succeeded_n = int(raw_batch.get("succeeded") or 0)
        topology_skipped_n = int(raw_batch.get("topology_skipped") or 0)
        deferred_n = int(raw_batch.get("topology_deferred_recorded") or 0)
        total_topology_deferred += deferred_n
        total_topology_skipped += topology_skipped_n
        total_succeeded += succeeded_n
        failures_batch = raw_batch.get("failures") if isinstance(raw_batch["failures"], list) else []
        total_failed_rows += len(failures_batch)
        for f in failures_batch:
            if len(failure_samples) >= 300:
                break
            if isinstance(f, dict):
                failure_samples.append(f)

        batches_run += 1
        tp = raw_batch.get("throughput_rows_per_second")
        if isinstance(tp, (float, int)):
            throughput_rows_per_second_samples.append(float(tp))

        candidate_more_remain = bool(raw_batch.get("candidate_more_remain"))

        if pass_key:
            if succeeded_n > 0:
                pass_productivity[pass_key] = int(pass_productivity.get(pass_key, 0)) + succeeded_n
            if topology_skipped_n > 0:
                pass_topology_skips[pass_key] = int(pass_topology_skips.get(pass_key, 0)) + topology_skipped_n

        if selected_n == 0 and attempted_n == 0:
            if scoped_drain:
                if not candidate_more_remain:
                    break
                pass_rotations_without_success += 1
                if pass_rotations_without_success >= pass_count:
                    full_rotation_topology_stall = True
                    break
                continue
            pass_rotations_without_success += 1
            if pass_rotations_without_success >= pass_count:
                full_rotation_topology_stall = count_passes_off_cooldown(
                    pass_cooldowns=pass_cooldowns, now=datetime.now(UTC)
                ) == 0
                break
            continue

        pass_rotations_without_success = 0

        topology_only = (
            succeeded_n == 0
            and len(failures_batch) == 0
            and (attempted_n > 0 or topology_skipped_n > 0)
        )
        if topology_only:
            topology_only_batches += 1
            if pass_key:
                record_pass_topology_stall(
                    pass_key=pass_key,
                    pass_cooldowns=pass_cooldowns,
                    pass_stall_counts=pass_stall_counts,
                    base_cooldown_seconds=base_cooldown_s,
                    max_cooldown_seconds=max_pass_cooldown_s,
                )
            # Pass-local cooldown: advance cursor and continue slice (do not terminate globally).
            if not scoped_drain and count_passes_off_cooldown(pass_cooldowns=pass_cooldowns) == 0:
                full_rotation_topology_stall = True
                break
            continue

        if succeeded_n > 0:
            productive_batches += 1
            release_deferrals_with_materialized_parents(db, tenant_id=tenant_id, bundle_id=bundle_id)

        if not candidate_more_remain:
            break

    elapsed_ms = int((datetime.now(UTC) - drain_started_at).total_seconds() * 1000)
    overall_tp = (
        round(float(total_succeeded) / (float(elapsed_ms) / 1000.0), 3)
        if elapsed_ms > 0
        else float(total_succeeded)
    )

    from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
        list_untreated_routable_count_estimate,
    )

    untreated_estimate = list_untreated_routable_count_estimate(
        db, tenant_id=tenant_id, bundle_id=bundle_id
    )
    deferral_counts = count_deferrals(db, tenant_id=tenant_id, bundle_id=bundle_id)
    deferral_pressure = summarize_deferral_pressure(db, tenant_id=tenant_id, bundle_id=bundle_id)
    hit_slice_cap = batches_run >= max_batches and (candidate_more_remain or untreated_estimate > 0)

    canonical_outcome = _classify_drain_outcome(
        total_succeeded=total_succeeded,
        total_failed_rows=total_failed_rows,
        full_rotation_topology_stall=full_rotation_topology_stall,
        candidate_more_remain=candidate_more_remain,
        untreated_estimate=untreated_estimate,
        hit_slice_cap=hit_slice_cap,
    )

    progress_made = total_succeeded > 0
    progress_density = (
        round(float(total_succeeded) / float(batches_run), 4) if batches_run > 0 else 0.0
    )
    blocked_pass_ratio = (
        round(float(topology_only_batches) / float(batches_run), 4) if batches_run > 0 else 0.0
    )

    metrics = build_forward_progress_metrics(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        untreated_estimate=untreated_estimate,
        deferral_counts=deferral_counts,
        total_succeeded=total_succeeded,
        elapsed_ms=elapsed_ms,
        productive_batches=productive_batches,
        topology_only_batches=topology_only_batches,
        progress_density=progress_density,
        blocked_pass_ratio=blocked_pass_ratio,
        deferral_pressure=deferral_pressure,
    )

    convergence_health = _convergence_health_label(
        canonical_outcome=canonical_outcome,
        untreated_estimate=untreated_estimate,
        total_succeeded=total_succeeded,
        deferral_counts=deferral_counts,
        full_rotation_topology_stall=full_rotation_topology_stall,
    )

    return {
        "forward_progress_schema_version": FORWARD_PROGRESS_SCHEMA_VERSION,
        "transform_runtime_schema_version": raw_batch.get("transform_runtime_schema_version")
        if batches_run
        else None,
        "tenant_id": str(tenant_id),
        "bundle_id": bundle_id,
        "scope_connector": connector.strip() if connector and connector.strip() else None,
        "scope_resource_type": resource_type.strip() if resource_type and resource_type.strip() else None,
        "batches_run": batches_run,
        "productive_batches": productive_batches,
        "topology_only_batches": topology_only_batches,
        "batch_limit_applied": lim,
        "total_attempted": total_succeeded + total_failed_rows + total_topology_skipped,
        "total_processable_selected": total_succeeded + total_failed_rows + total_topology_skipped,
        "total_succeeded": total_succeeded,
        "total_failed_rows": total_failed_rows,
        "total_topology_skipped": total_topology_skipped,
        "total_topology_deferred_recorded": total_topology_deferred,
        "failure_samples": failure_samples,
        "failure_samples_truncated": total_failed_rows > len(failure_samples),
        "stub_resource_pairs_selected": pair_labels,
        "hit_batch_cap": hit_slice_cap and progress_made,
        "hit_slice_cap": hit_slice_cap,
        "slice_budget_exhausted": hit_slice_cap,
        "full_rotation_topology_stall": full_rotation_topology_stall,
        "topology_wait": canonical_outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT,
        "zero_progress_spin_detected": full_rotation_topology_stall and total_succeeded == 0,
        "canonical_outcome": canonical_outcome,
        "convergence_health": convergence_health,
        "pass_index_next": cursor_pass_index,
        "pass_cooldown_until": serialize_pass_cooldown_until(pass_cooldowns),
        "pass_topology_stall_counts": serialize_pass_topology_stall_counts(pass_stall_counts),
        "pass_productivity": pass_productivity,
        "pass_topology_skips": pass_topology_skips,
        "duration_ms": elapsed_ms,
        "overall_throughput_rows_per_second": overall_tp,
        "progress_density_rows_per_batch": progress_density,
        "blocked_pass_batch_ratio": blocked_pass_ratio,
        "batch_throughput_rows_per_second_samples": throughput_rows_per_second_samples[:200],
        "progress_made": progress_made,
        "candidate_more_remain": candidate_more_remain,
        "untreated_routable_estimate": untreated_estimate,
        "deferral_counts": deferral_counts,
        "deferral_pressure_sample": deferral_pressure,
        "forward_progress_metrics": metrics,
        "last_batch_forward_progress": last_batch_meta,
    }


def _convergence_health_label(
    *,
    canonical_outcome: str,
    untreated_estimate: int,
    total_succeeded: int,
    deferral_counts: dict[str, int],
    full_rotation_topology_stall: bool,
) -> str:
    permanent = int(deferral_counts.get("deferred_permanent_orphan") or 0)
    if untreated_estimate == 0:
        return "complete"
    if total_succeeded > 0 and canonical_outcome == CANONICAL_OUTCOME_PARTIAL_PROGRESS:
        return "converging"
    if full_rotation_topology_stall and permanent > 0:
        return "structurally_incomplete"
    if full_rotation_topology_stall:
        return "blocked_by_topology"
    if canonical_outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT:
        return "blocked_by_topology"
    if total_succeeded > 0:
        return "progressing_normally"
    return "starvation_detected"
