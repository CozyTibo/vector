"""Phase D4 — permanent topology orphan deferrals are bounded omission, not drain failure."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.deferral_store import count_deferrals
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform

P0_D4_STEP: Final[str] = "step_d4_permanent_orphan_omission_doctrine"
PHASE_D4_OMISSION_SCHEMA_VERSION: Final[int] = 1

# Fizzer prod reference (2026-05-22 unlock baseline) — bounded structural debt, not a P0 defect.
FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1: Final[int] = 466

OMISSION_CLASS_PERMANENT_TOPOLOGY_ORPHAN_V1: Final[str] = "permanent_topology_orphan"
OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1: Final[str] = "accepted_bounded_debt"
OMISSION_POSTURE_CHASE_ZERO_DEFERRALS_V1: Final[str] = "chase_zero_deferrals_forbidden"

RUNBOOK_REL_PATH_V1: Final[str] = (
    "DOCS/cortex/operational-runtime/canonical_permanent_orphan_omission_runbook.md"
)

OPERATOR_COPY_HEADLINE_V1: Final[str] = "Permanent orphans are documented omission (not a drain failure)"
OPERATOR_COPY_SUMMARY_V1: Final[str] = (
    "Topology-quarantine rows marked permanent_orphan after retry threshold are intentional "
    "bounded debt. Do not chase deferral_total → 0; chase drainable_routable and lawful graph motion."
)


def runbook_path_v1(*, repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[5]
    return root / RUNBOOK_REL_PATH_V1


def is_permanent_orphan_omission_doc_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_canonical_permanent_orphan_omission_doc_enabled)
    except Exception:  # noqa: BLE001
        return True


def evaluate_permanent_orphan_omission_posture_v1(
    *,
    deferral_counts: dict[str, int],
) -> dict[str, Any]:
    """Classify deferral posture for admin surfaces and proof gates."""
    permanent = int(deferral_counts.get("deferred_permanent_orphan") or 0)
    defer_total = int(deferral_counts.get("deferred_total") or 0)
    retry_ready = int(deferral_counts.get("deferred_retry_ready") or 0)
    permanent_share_pct = int(round(100 * permanent / defer_total)) if defer_total else 0

    chase_zero_forbidden = permanent > 0 and permanent_share_pct >= 20
    posture = (
        OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1
        if permanent > 0
        else OMISSION_POSTURE_CHASE_ZERO_DEFERRALS_V1
    )
    return {
        "omission_class": OMISSION_CLASS_PERMANENT_TOPOLOGY_ORPHAN_V1,
        "posture": posture,
        "permanent_orphan_count": permanent,
        "deferral_total": defer_total,
        "deferred_retry_ready": retry_ready,
        "permanent_share_pct": permanent_share_pct,
        "chase_zero_deferrals_forbidden": chase_zero_forbidden,
        "is_bounded_omission_not_failure": permanent > 0,
        "fizzer_reference_count": FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
        "headline": OPERATOR_COPY_HEADLINE_V1,
        "summary": OPERATOR_COPY_SUMMARY_V1,
        "operator_actions": [
            "Monitor drainable_routable_estimate (primary KPI) — not raw−mat gap.",
            "Treat permanent_orphan rows as topology omission; do not block AA on count alone.",
            "Raise GitHub ingest caps (D2) and run graph promotion (D3) to shrink retry-ready deferrals.",
            f"See runbook: {RUNBOOK_REL_PATH_V1}",
        ],
    }


def snapshot_permanent_orphan_omission_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    deferral_counts: dict[str, int] = {}
    if bundle_id:
        deferral_counts = count_deferrals(session, tenant_id=tenant_id, bundle_id=bundle_id)
    posture = evaluate_permanent_orphan_omission_posture_v1(deferral_counts=deferral_counts)
    return {
        "tenant_id": str(tenant_id),
        "bundle_id": bundle_id,
        "deferral_counts": deferral_counts,
        "deferral_omission": posture,
        "schema_version": PHASE_D4_OMISSION_SCHEMA_VERSION,
        "doc_enabled": is_permanent_orphan_omission_doc_enabled_v1(),
    }


def build_deferral_omission_operator_block_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    deferral_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """API block for pipeline overview / canonical admin."""
    counts = deferral_counts
    if counts is None:
        snap = snapshot_permanent_orphan_omission_v1(session, tenant_id=tenant_id)
        counts = dict(snap.get("deferral_counts") or {})
    posture = evaluate_permanent_orphan_omission_posture_v1(deferral_counts=counts)
    return {
        "surface_kind": "deferral_omission_posture",
        "schema_version": PHASE_D4_OMISSION_SCHEMA_VERSION,
        "enabled": is_permanent_orphan_omission_doc_enabled_v1(),
        "runbook_path": RUNBOOK_REL_PATH_V1,
        **posture,
    }
