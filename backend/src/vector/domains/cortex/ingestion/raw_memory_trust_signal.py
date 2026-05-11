"""Phase 02 Step 14 — trust-signal / proof-quality hardening for operator surfaces."""

from __future__ import annotations

from typing import Any

PROOF_QUALITY_PRIMARY_VALUES: frozenset[str] = frozenset(
    {"measured", "inferred", "stale", "partial", "unverifiable"}
)


def verify_phase02_step14_trust_signal_hardening(
    phase02_verification_truth: dict[str, Any],
) -> dict[str, Any]:
    """Structural checks that proof-quality and freshness signals are operator-safe (G14 prereq)."""
    checks: list[dict[str, Any]] = []

    pq_raw: Any = phase02_verification_truth.get("proof_quality")
    pq = pq_raw if isinstance(pq_raw, dict) else {}
    pq_ok = isinstance(pq_raw, dict)
    primary = str(pq.get("primary", ""))
    primary_ok = primary in PROOF_QUALITY_PRIMARY_VALUES
    checks.append(
        {
            "id": "s14_proof_quality_primary_valid",
            "passed": pq_ok and primary_ok,
            "detail": {"primary": primary},
        }
    )

    required_pq_keys = {
        "primary",
        "measured",
        "inferred",
        "stale_snapshot",
        "partial",
        "unverifiable",
    }
    pq_keys_ok = pq_ok and required_pq_keys.issubset(set(pq.keys()))
    checks.append(
        {
            "id": "s14_proof_quality_primitive_flags",
            "passed": pq_keys_ok,
            "detail": {"missing": sorted(required_pq_keys - set(pq.keys()))}
            if pq_ok
            else {},
        }
    )

    fr_raw: Any = phase02_verification_truth.get("freshness")
    fr = fr_raw if isinstance(fr_raw, dict) else {}
    fr_ok = isinstance(fr_raw, dict)
    label = str(fr.get("label", ""))
    label_ok = label in {"fresh", "stale"}
    checks.append(
        {
            "id": "s14_freshness_label_operator_visible",
            "passed": fr_ok and label_ok,
            "detail": {"label": label, "from_cache": fr.get("from_cache") if fr_ok else None},
        }
    )

    prec_raw: Any = phase02_verification_truth.get("precedence")
    prec = prec_raw if isinstance(prec_raw, dict) else {}
    trust_align = prec.get("trust_g1_g7_matches_closure")
    checks.append(
        {
            "id": "s14_trust_alignment_flag_present",
            "passed": isinstance(trust_align, bool),
            "detail": {"trust_g1_g7_matches_closure": trust_align},
        }
    )

    passed = all(bool(c.get("passed")) for c in checks)
    return {
        "passed": passed,
        "state": "operator_safe" if passed else "degraded",
        "checks": checks,
        "summary": {
            "proof_quality_primary": primary if primary_ok else None,
            "freshness_label": label if label_ok else None,
        },
    }
