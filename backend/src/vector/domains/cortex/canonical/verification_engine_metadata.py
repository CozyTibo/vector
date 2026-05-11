"""Static metadata for Phase 03 Step 15 verification engine (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

VERIFICATION_ENGINE_SURFACE_VERSION: Final[int] = 2


def build_verification_engine_pointer_section() -> dict[str, Any]:
    return {
        "verification_engine_surface_version": VERIFICATION_ENGINE_SURFACE_VERSION,
        "canonical_verification_run_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/verification/run"
        ),
        "canonical_verification_repair_determinism_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/verification/repair-determinism-drift"
        ),
        "canonical_verification_runs_list_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/verification/runs"
        ),
        "verification_engine_gate_ids": [
            "G-P03-01",
            "G-P03-02",
            "G-P03-03",
            "G-P03-04",
            "G-P03-06",
            "G-P03-08",
            "G-P03-09",
            "G-P03-10",
            "G-P03-16",
            "G-P03-17",
            "G-P03-21",
            "G-P03-22",
            "G-P03-23",
            "G-P03-24",
            "G-P04-08",
            "G-P04-ORG-01",
            "G-P04-LINK-01",
            "G-P04-06",
            "G-P04-04",
            "G-P04-05",
            "G-P04-CAND-01",
            "G-P04-MRG-01",
            "G-P04-01",
            "G-P04-13",
            "G-P04-02",
            "G-P04-HINT-01",
            "G-P04-TMP-01",
            "G-P04-11",
            "G-P04-BNDL-01",
            "G-P04-03",
            "G-P04-14",
            "G-P04-RPL-01",
            "G-P04-RULE-01",
            "G-P04-09",
            "G-P04-PRIM-01",
            "G-P04-10",
            "G-P04-EXP-01",
            "G-P04-AMB-01",
            "G-P04-12",
            "G-P04-VER-01",
            "G-P04-19",
            "G-P04-18",
            "G-P04-21",
            "G-P04-22",
            "G-P04-23",
            "G-P04-24",
            "G-P04-25",
            "G-P04-26",
            "G-P04-BF-01",
            "G-P04-ECO-01",
            "G-P04-CLOSE-01",
        ],
        "verification_engine_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-verification-engine-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-closure-gates-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-topology-vs-meaning-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-org-entity-and-handle-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-link-ledger-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-candidate-vs-authoritative-linkage-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-merge-governance-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-hint-and-prohibited-link-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-temporal-validity-and-revocation-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-cross-bundle-equivalence-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-continuity-replay-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-linkage-rule-engine-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-execution-primitive-persistence-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-graph-boundary-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-graph-projection-export-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-ambiguity-multiple-persona-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-verification-gates-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-failure-remediation-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-control-plane-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-backfill-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-readiness-audit.md",
            "DOCS/cortex/04-identity/phase-04-closure-gates-doctrine.md",
        ],
    }
