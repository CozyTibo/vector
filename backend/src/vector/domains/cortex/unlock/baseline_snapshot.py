"""War-room step-1 baseline snapshot validation and alive-metric extraction."""

from __future__ import annotations

from typing import Any

# Top-level keys emitted by prod_substrate_proof_queries.py (step 1 contract).
BASELINE_REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "tenant_id",
        "routable_pair_count",
        "tenant",
        "lease",
        "raw_total",
        "mat_total",
        "raw_minus_mat_admin_gap",
        "bundles",
        "primary_bundle_id",
        "anchors",
        "org_entities_active",
        "auth_links",
        "candidates",
        "raw_by_type",
        "mat_without_anchor",
        "phase_runs",
        "primitives",
        "entity_by_kind",
        "samples",
    }
)

# Present when primary_bundle_id resolves (expected on Fizzer).
BASELINE_BUNDLE_SCOPED_KEYS: frozenset[str] = frozenset(
    {
        "untreated_routable_estimate",
        "untreated_raw_any_bundle",
        "deferral_totals",
        "deferral_top",
        "topology_parent_gaps",
        "failure_cases",
        "routable_breakdown",
    }
)


def validate_baseline_snapshot(payload: dict[str, Any]) -> None:
    """Raise ValueError if payload is not a complete step-1 baseline."""
    missing = BASELINE_REQUIRED_TOP_LEVEL_KEYS - payload.keys()
    if missing:
        raise ValueError(f"baseline missing required keys: {sorted(missing)}")
    if payload.get("primary_bundle_id") and not BASELINE_BUNDLE_SCOPED_KEYS <= payload.keys():
        missing_bundle = BASELINE_BUNDLE_SCOPED_KEYS - payload.keys()
        raise ValueError(f"baseline missing bundle-scoped keys: {sorted(missing_bundle)}")


def extract_alive_baseline_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """Map raw prod query JSON to alive-criteria baseline fields (A1–A6 pre-check)."""
    lease_rows = payload.get("lease") or []
    lease = lease_rows[0] if lease_rows else {}
    deferral = (payload.get("deferral_totals") or [{}])[0]
    return {
        "tenant_id": payload.get("tenant_id"),
        "captured_at_note": "See baselines/*.json filename date",
        "primary_bundle_id": payload.get("primary_bundle_id"),
        "A1_org_entities_active": payload.get("org_entities_active"),
        "A2_authoritative_links": payload.get("auth_links"),
        "A3_candidate_links": payload.get("candidates"),
        "A4_last_canonical_outcome": lease.get("last_canonical_outcome"),
        "A4_fsm_state": lease.get("fsm_state"),
        "A4_phase_cursor": lease.get("phase_cursor"),
        "raw_total": payload.get("raw_total"),
        "mat_total": payload.get("mat_total"),
        "raw_minus_mat_admin_gap": payload.get("raw_minus_mat_admin_gap"),
        "deferrals_total": deferral.get("total"),
        "deferrals_permanent_orphan": deferral.get("permanent_orphan"),
        "anchors": payload.get("anchors"),
        "routable_unmat": (payload.get("routable_breakdown") or {}).get("routable_unmat"),
    }
