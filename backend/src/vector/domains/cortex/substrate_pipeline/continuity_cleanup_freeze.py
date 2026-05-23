"""Cleanup / freeze policies (non-numbered plan requirements).

- Collapse per-phase proof scripts → ``continuity_audit_snapshot.py`` + panel
- Ban unlock_step09/10/12 during active 48h AA hold (AA7)
- Freeze per-island synthesis inspect sign-off until B1 + C1 prove scopes > 0
- Island registry sync on publish only (inspect default read-only)
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
)
from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    count_retrieval_entries_in_scope_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c4_aa_clock_restart import (
    C4_CLOCK_RESTART_GENERATION_V1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p2_aa_clock import (
    CONTINUITY_AA_HOLD_HOURS_V1,
    aa_clock_hold_elapsed_hours_v1,
    continuity_aa_clock_baseline_path_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
    CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1,
    CANONICAL_AUDIT_SNAPSHOT_MODULE_V1,
    deprecated_continuity_proof_script_names_v1,
)

CLEANUP_FREEZE_SCHEMA_VERSION: Final[int] = 1

BANNED_WEDGE_SCRIPT_NAMES_V1: Final[tuple[str, ...]] = (
    "archive/unlock/unlock_step09_graph_octs_walk.py",
    "archive/unlock/unlock_step10_retrieval.py",
    "archive/unlock/unlock_step12_track_b_p3.py",
)

WEDGE_SCRIPT_PATTERN_NAMES_V1: Final[tuple[str, ...]] = (
    "unlock_step09",
    "unlock_step10",
    "unlock_step12",
)


class WedgeScriptBannedDuringHoldError(RuntimeError):
    """Raised when unlock wedge scripts run during active 48h AA hold."""


def load_aa_clock_t0_from_repo_v1(
    *,
    repo_root: Path,
    baseline_date: str | None = None,
) -> dict[str, Any] | None:
    from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c4_aa_clock_restart import (
        load_aa_clock_t0_baseline_v1,
    )

    path = continuity_aa_clock_baseline_path_v1(
        repo_root=repo_root,
        date_suffix=baseline_date,
    )
    if not path.is_file():
        return None
    return load_aa_clock_t0_baseline_v1(path)


def is_aa48_hold_clock_active_v1(
    t0_baseline: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> bool:
    """True when C4-restarted 48h M3 hold window is in progress."""
    if not t0_baseline or bool(t0_baseline.get("superseded")):
        return False
    if int(t0_baseline.get("clock_restart_generation") or 0) < C4_CLOCK_RESTART_GENERATION_V1:
        return False
    started_raw = str(t0_baseline.get("clock_started_at") or "")
    if not started_raw:
        return False
    started = datetime.fromisoformat(started_raw)
    elapsed = aa_clock_hold_elapsed_hours_v1(clock_started_at=started, now=now)
    required = float(t0_baseline.get("hold_hours_required") or CONTINUITY_AA_HOLD_HOURS_V1)
    return elapsed < required


def aa7_wedge_free_ack_allowed_v1(
    *,
    aa_hold_active: bool,
    at_clock_start: bool,
) -> bool:
    """C2: wedge-free ack only at clock start, not on daily hold checks."""
    if not aa_hold_active:
        return True
    return at_clock_start


def evaluate_aa7_hold_policy_context_v1(
    *,
    repo_root: Path | None = None,
    baseline_date: str | None = None,
    at_clock_start: bool = False,
) -> dict[str, Any]:
    t0: dict[str, Any] | None = None
    if repo_root is not None:
        t0 = load_aa_clock_t0_from_repo_v1(repo_root=repo_root, baseline_date=baseline_date)
    hold_active = is_aa48_hold_clock_active_v1(t0)
    return {
        "aa_hold_active": hold_active,
        "wedge_free_ack_allowed": aa7_wedge_free_ack_allowed_v1(
            aa_hold_active=hold_active,
            at_clock_start=at_clock_start,
        ),
        "unlock_wedge_scripts_banned": hold_active,
        "clock_restart_generation": (t0 or {}).get("clock_restart_generation"),
        "clock_started_at": (t0 or {}).get("clock_started_at"),
    }


def evaluate_b1_retrieval_scopes_proven_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str | None = None,
) -> dict[str, Any]:
    """B1: published epoch + in-scope retrieval entries for primary island."""
    scope = island_scope_id or FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    in_scope = 0
    if published and scope:
        in_scope = count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=published,
            island_scope_id=scope,
        )
    proven = bool(published) and in_scope > 0
    return {
        "b1_proven": proven,
        "published_index_epoch": published,
        "primary_island_scope_id": scope,
        "retrieval_entries_in_scope": in_scope,
    }


def evaluate_c1_synthesis_scopes_proven_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """C1: phase-08 empty-scope gate — scopes/entries exist when required."""
    from vector.domains.cortex.substrate_pipeline.continuity_p0_phase08_empty_scope_truth import (
        snapshot_phase08_empty_scope_truth_v1,
    )

    snap = snapshot_phase08_empty_scope_truth_v1(session, tenant_id=tenant_id)
    wiring = dict(snap.get("wiring") or {})
    receipts = list(snap.get("phase08_receipts") or [])
    any_scopes = any(int(r.get("scopes_scheduled") or 0) > 0 for r in receipts)
    any_entries = any(int(r.get("retrieval_entries_in_epoch") or 0) > 0 for r in receipts)
    gate_ok = all(
        bool(r.get("phase08_empty_scope_gate_ok", True))
        for r in receipts
    ) if receipts else bool(wiring.get("gate_enabled"))
    proven = bool(any_scopes or any_entries) and gate_ok and not any(
        r.get("empty_scope_violation") for r in receipts
    )
    return {
        "c1_proven": proven,
        "gate_enabled": wiring.get("gate_enabled"),
        "phase08_receipt_count": len(receipts),
        "any_scopes_scheduled": any_scopes,
        "any_retrieval_entries_in_epoch": any_entries,
        "empty_scope_violations": [
            r.get("pipeline_run_id")
            for r in receipts
            if r.get("empty_scope_violation")
        ],
    }


def evaluate_per_island_synthesis_signoff_freeze_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Freeze per-island synthesis inspect sign-off until B1 + C1 prove scopes > 0."""
    b1 = evaluate_b1_retrieval_scopes_proven_v1(session, tenant_id=tenant_id)
    c1 = evaluate_c1_synthesis_scopes_proven_v1(session, tenant_id=tenant_id)
    eligible = bool(b1.get("b1_proven")) and bool(c1.get("c1_proven"))
    reasons: list[str] = []
    if not b1.get("b1_proven"):
        reasons.append("b1_retrieval_in_scope_entries_required")
    if not c1.get("c1_proven"):
        reasons.append("c1_phase08_scopes_or_empty_scope_gate_required")
    return {
        "surface_kind": "per_island_synthesis_signoff_freeze",
        "schema_version": CLEANUP_FREEZE_SCHEMA_VERSION,
        "signoff_eligible": eligible,
        "signoff_frozen": not eligible,
        "global_degradation_brief_hidden": not c1.get("c1_proven"),
        "reasons": reasons,
        "b1": b1,
        "c1": c1,
    }


def assert_wedge_script_allowed_v1(
    script_path: str | Path,
    *,
    repo_root: Path | None = None,
    baseline_date: str | None = None,
) -> None:
    """Block unlock_step09/10/12 during 48h hold unless explicit override env."""
    name = Path(script_path).name
    banned_names = {Path(p).name for p in BANNED_WEDGE_SCRIPT_NAMES_V1}
    if name not in banned_names:
        return
    if os.environ.get("CORTEX_ALLOW_UNLOCK_WEDGE_SCRIPTS", "").lower() in ("1", "true", "yes"):
        return
    hold_ctx = evaluate_aa7_hold_policy_context_v1(
        repo_root=repo_root,
        baseline_date=baseline_date,
    )
    if hold_ctx.get("unlock_wedge_scripts_banned"):
        raise WedgeScriptBannedDuringHoldError(
            f"{name} is banned during the active 48h AA hold (AA7). "
            "Use autonomous convergence + continuity_audit_snapshot.py. "
            "Emergency override: CORTEX_ALLOW_UNLOCK_WEDGE_SCRIPTS=1"
        )


def verify_cleanup_freeze_wiring_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    import inspect

    errors: list[str] = []
    root = repo_root or Path(__file__).resolve().parents[6]

    from vector.domains.cortex.substrate_pipeline import continuity_proof_panel as panel_mod
    from vector.domains.cortex.substrate_pipeline import continuity_audit_snapshot as snap_mod
    from vector.domains.cortex.synthesis import synthesis_per_island as pi_mod
    from vector.domains.cortex.operational_runtime import execution_island_registry as reg_mod

    panel_src = inspect.getsource(panel_mod.build_continuity_proof_panel_v1)
    if "evaluate_aa7_no_wedge_scripts_v1" not in panel_src:
        errors.append("panel_missing_aa7_evaluator")
    if "aa_hold_active" not in inspect.getsource(panel_mod.evaluate_aa7_no_wedge_scripts_v1):
        errors.append("aa7_missing_hold_active_policy")

    snap_src = inspect.getsource(snap_mod.build_continuity_audit_snapshot_v1)
    if "build_continuity_proof_panel_v1" not in snap_src:
        errors.append("audit_snapshot_missing_panel")
    deprecated = set(deprecated_continuity_proof_script_names_v1())
    if CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1 in deprecated:
        errors.append("canonical_audit_snapshot_must_not_be_deprecated")
    if len(deprecated) < 20:
        errors.append("deprecated_proof_script_catalog_too_small")

    pi_src = inspect.getsource(pi_mod.build_per_island_synthesis_inspect_v1)
    if "evaluate_per_island_synthesis_signoff_freeze_v1" not in pi_src:
        errors.append("per_island_inspect_missing_signoff_freeze")

    reg_sig = inspect.signature(reg_mod.build_island_registry_inspect_v1)
    if reg_sig.parameters["sync"].default is not False:
        errors.append("island_registry_inspect_sync_default_not_false")

    reg_src = inspect.getsource(reg_mod.build_island_registry_inspect_v1)
    if "sync on publish" not in reg_src.lower() and "B3" not in reg_src:
        errors.append("island_registry_inspect_missing_publish_only_doc")

    scripts_dir = root / "backend" / "scripts"
    for script in BANNED_WEDGE_SCRIPT_NAMES_V1:
        path = scripts_dir / script
        if not path.is_file():
            errors.append(f"missing_wedge_script_for_guard:{script}")
            continue
        body = path.read_text(encoding="utf-8")
        if "assert_wedge_script_allowed_v1" not in body:
            errors.append(f"wedge_script_missing_guard:{script}")

    audit_script = scripts_dir / CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1
    if not audit_script.is_file():
        errors.append("missing_canonical_audit_snapshot_script")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "cleanup_freeze_schema_version": CLEANUP_FREEZE_SCHEMA_VERSION,
        "deprecated_proof_script_count": len(deprecated),
        "canonical_entrypoints": [
            f"backend/scripts/{CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1}",
            CANONICAL_AUDIT_SNAPSHOT_MODULE_V1,
        ],
        "banned_wedge_scripts": list(BANNED_WEDGE_SCRIPT_NAMES_V1),
    }


def build_cleanup_freeze_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    repo_root: Path | None = None,
    baseline_date: str | None = None,
) -> dict[str, Any]:
    hold_ctx = evaluate_aa7_hold_policy_context_v1(
        repo_root=repo_root,
        baseline_date=baseline_date,
    )
    signoff = evaluate_per_island_synthesis_signoff_freeze_v1(session, tenant_id=tenant_id)
    wiring = verify_cleanup_freeze_wiring_v1(repo_root=repo_root)
    return {
        "surface_kind": "continuity_cleanup_freeze",
        "schema_version": CLEANUP_FREEZE_SCHEMA_VERSION,
        "aa_hold": hold_ctx,
        "per_island_signoff_freeze": signoff,
        "wiring": wiring,
        "deprecated_proof_scripts": list(deprecated_continuity_proof_script_names_v1()),
    }
