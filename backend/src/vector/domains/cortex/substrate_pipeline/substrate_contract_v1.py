"""Wave 7 — collapsed substrate API contracts (truth, graph, handoff, slice receipt, phase receipt)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import jsonschema  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY, PHASE_04_GRAPH
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_WAITING_ASYNC,
    PHASE_OUTCOMES_TERMINAL,
    read_phase_receipt_from_output,
)

INGEST_HANDOFF_SCHEMA_VERSION: Final[int] = 1
INGEST_HANDOFF_SURFACE_KIND: Final[str] = "ingest_handoff_v1"

GRAPH_SUBSTRATE_SCHEMA_VERSION: Final[int] = 1
GRAPH_SUBSTRATE_SURFACE_KIND: Final[str] = "graph_substrate_v1"

SUBSTRATE_SLICE_RECEIPT_SCHEMA_VERSION: Final[int] = 1
SUBSTRATE_SLICE_RECEIPT_SURFACE_KIND: Final[str] = "substrate_slice_receipt_v1"

PHASE_RECEIPT_V1_DETERMINISTIC_VERSION: Final[str] = "substrate_receipt_v1"


def discover_substrate_contracts_dir_v1() -> Path:
    """Packaged schemas (docker/CI) or monorepo ``backend/contracts``."""
    here = Path(__file__).resolve()
    packaged = here.parent / "schemas"
    if (packaged / "substrate_truth_v1.schema.json").is_file():
        return packaged
    for candidate in (
        here.parents[5] / "contracts",
        here.parents[4] / "contracts",
    ):
        if (candidate / "substrate_truth_v1.schema.json").is_file():
            return candidate
    return packaged


def load_json_schema_v1(name: str) -> dict[str, Any]:
    path = discover_substrate_contracts_dir_v1() / name
    return json.loads(path.read_text(encoding="utf-8"))


def build_ingest_handoff_v1(
    *,
    dirty_enqueued: bool,
    obligation_epoch: int | None,
    reason: str | None = None,
    celery_task_id: str | None = None,
) -> dict[str, Any]:
    """Unified post-ingest handoff shape (replaces Celery task-id fiction)."""
    return {
        "surface_kind": INGEST_HANDOFF_SURFACE_KIND,
        "schema_version": INGEST_HANDOFF_SCHEMA_VERSION,
        "dirty_enqueued": bool(dirty_enqueued),
        "obligation_epoch": obligation_epoch,
        "reason": reason,
        "celery_task_id": celery_task_id,
    }


def build_graph_substrate_v1(
    session: Session,
    *,
    tenant_id: Any,
    include_connected_components: bool = True,
) -> dict[str, Any]:
    """Authoritative graph topology KPIs — single shape for truth + phase 04."""
    import uuid

    from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import _query_graph_truth_v1

    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    metrics = _query_graph_truth_v1(
        session,
        tenant_id=tid,
        include_connected_components=include_connected_components,
    )
    isolated_pct = round(100.0 - float(metrics.get("entities_in_auth_graph_pct") or 0.0), 2)
    components = metrics.get("connected_components") or {}
    largest_component_entity_pct = None
    if isinstance(components, dict) and components.get("largest_component_size") is not None:
        active = int(metrics.get("active_entities") or 0)
        largest = int(components["largest_component_size"])
        if active > 0:
            largest_component_entity_pct = round(100.0 * largest / active, 2)

    return {
        "surface_kind": GRAPH_SUBSTRATE_SURFACE_KIND,
        "schema_version": GRAPH_SUBSTRATE_SCHEMA_VERSION,
        "tenant_id": str(tid),
        "primary_metric_key": "unique_auth_pairs",
        "unique_auth_pairs": int(metrics.get("unique_auth_pairs") or 0),
        "promotion_rule_count": int(metrics.get("promotion_rule_count") or 0),
        "dup_factor": metrics.get("dup_factor"),
        "dup_factor_severity": metrics.get("dup_factor_severity"),
        "active_entities": int(metrics.get("active_entities") or 0),
        "entities_in_auth_graph": int(metrics.get("entities_in_auth_graph") or 0),
        "entities_isolated": int(metrics.get("entities_isolated") or 0),
        "entities_in_auth_graph_pct": float(metrics.get("entities_in_auth_graph_pct") or 0.0),
        "isolated_pct": isolated_pct,
        "largest_component_entity_pct": largest_component_entity_pct,
        "connected_components": components if components else None,
        "diagnostics": {
            "auth_edge_rows": int(metrics.get("auth_edge_rows") or 0),
            "note": "auth_edge_rows is diagnostic only; trust unique_auth_pairs",
        },
    }


def build_substrate_slice_receipt_v1(
    *,
    tenant_id: str,
    bundle_id: str,
    substrate_trigger: str,
    repair_slice: dict[str, Any],
    identity_audit: dict[str, Any] | None = None,
    promotion_pass: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single repair-slice receipt (replaces projection receipt forest on lease)."""
    repair = repair_slice.get("identity_substrate_repair") or {}
    return {
        "surface_kind": SUBSTRATE_SLICE_RECEIPT_SURFACE_KIND,
        "schema_version": SUBSTRATE_SLICE_RECEIPT_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "bundle_id": bundle_id,
        "substrate_trigger": substrate_trigger,
        "repair": {
            "anchor_offset_after": repair.get("anchor_offset_after"),
            "anchor_backfill_exhausted": repair.get("anchor_backfill_exhausted"),
            "anchors_total": repair.get("anchors_total"),
            "entities_upserted": repair.get("entities_upserted"),
        },
        "identity_audit": identity_audit,
        "promotion_pass": _normalize_promotion_pass_v1(promotion_pass),
    }


def _normalize_promotion_pass_v1(promotion: dict[str, Any] | None) -> dict[str, Any] | None:
    if not promotion:
        return None
    return {
        "scheduled": promotion.get("scheduled"),
        "path": promotion.get("path"),
        "trigger": promotion.get("trigger"),
        "promotion_rule_count": promotion.get("promotion_rule_count"),
        "links_promoted": promotion.get("links_promoted"),
    }


def validate_phase_receipt_v1(output_json: dict[str, Any] | None) -> list[str]:
    """Return error codes if phase output lacks a valid ``substrate_phase_receipt`` envelope."""
    errors: list[str] = []
    if not output_json:
        errors.append("missing_output_json")
        return errors
    rec = read_phase_receipt_from_output(output_json)
    if rec is None:
        errors.append("missing_substrate_phase_receipt")
        return errors
    outcome = rec.get("outcome")
    allowed = PHASE_OUTCOMES_TERMINAL | {PHASE_OUTCOME_WAITING_ASYNC}
    if outcome not in allowed:
        errors.append(f"invalid_phase_outcome:{outcome}")
    if rec.get("deterministic_version") != PHASE_RECEIPT_V1_DETERMINISTIC_VERSION:
        errors.append("invalid_phase_receipt_deterministic_version")
    if not rec.get("receipt_hash"):
        errors.append("missing_receipt_hash")
    return errors


def validate_substrate_truth_v1(payload: dict[str, Any]) -> list[str]:
    """Validate truth document against ``substrate_truth_v1.schema.json`` (CI gate)."""
    errors: list[str] = []
    schema_path = discover_substrate_contracts_dir_v1() / "substrate_truth_v1.schema.json"
    if not schema_path.is_file():
        return ["missing_substrate_truth_schema_file"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(payload), key=lambda e: e.path):
        errors.append(f"substrate_truth_schema:{err.message}")
    return errors


def verify_wave7_contract_collapse_v1(*, repo_root: Path | None = None) -> list[str]:
    """Wave 7 static + schema gates for collapsed substrate contracts."""
    import inspect

    errors: list[str] = []
    root = repo_root
    if root is None:
        from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
            discover_repo_root_v1,
        )

        root = discover_repo_root_v1()
    contracts = discover_substrate_contracts_dir_v1()
    for name in ("substrate_truth_v1.schema.json", "phase_receipt_v1.schema.json"):
        if not (contracts / name).is_file():
            errors.append(f"missing_contract_file:{name}")
    if root is not None:
        yaml_path = root / "backend/contracts/substrate_v1.yaml"
        if not yaml_path.is_file():
            errors.append("missing_contract_file:substrate_v1.yaml")

    from vector.domains.cortex.execution import convergence_dispatch as cd_mod

    cd_src = inspect.getsource(cd_mod.mark_dirty_and_enqueue_convergence_v1)
    if "ingest_handoff_v1" not in cd_src:
        errors.append("convergence_dispatch_missing_ingest_handoff_v1")

    from vector.domains.cortex.substrate_pipeline import substrate_truth_v1 as truth_mod

    truth_src = inspect.getsource(truth_mod.build_substrate_truth_v1)
    if "graph_substrate" not in truth_src or "ingest_handoff" not in truth_src:
        errors.append("substrate_truth_missing_wave7_fields")

    admin_path = (root / "backend/src/vector/api/http/routes/admin.py") if root else None
    if admin_path and admin_path.is_file():
        admin_src = admin_path.read_text(encoding="utf-8")
        if "raise_identity_replay_jobs_primary_route_gone_v1" not in admin_src:
            errors.append("admin_missing_replay_jobs_410_wiring")

    if root is not None:
        fe = root / "frontend/src/admin/operator/fetchOperator.ts"
        if fe.is_file() and "fetchSubstrateTruth" not in fe.read_text(encoding="utf-8"):
            errors.append("frontend_missing_fetchSubstrateTruth")

    return errors


def validate_phase03_phase04_outputs_v1(
    phase03_output: dict[str, Any] | None,
    phase04_output: dict[str, Any] | None,
) -> list[str]:
    """Wave 7 — phase 03/04 outputs must carry ``substrate_phase_receipt``."""
    errors: list[str] = []
    for label, output in (("phase03", phase03_output), ("phase04", phase04_output)):
        if output is None:
            continue
        for code in validate_phase_receipt_v1(output):
            errors.append(f"{label}:{code}")
    return errors
