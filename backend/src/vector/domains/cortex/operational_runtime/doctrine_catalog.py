"""Phase 08.5 CESP doctrine catalog builders (operator spec mirrors — not tenant truth)."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_CONTINUATION_NONCE_FIELD_V1,
    PHASE085_EXECUTIVE_BRIEF_REF_V1,
    PHASE085_FREEZE_BUNDLE_IDS,
    PHASE085_GAP_MATRIX_REF_V1,
    PHASE085_HARD_DOWNSTREAM_GATE_V1,
    PHASE085_HARD_UPSTREAM_GATE_V1,
    PHASE085_NORMATIVE_INDEX_REF_V1,
    PHASE085_NORMATIVE_TREE_V1,
    PHASE085_PROGRAM_FREEZE_VERSION,
    PHASE085_PROGRAM_ID_V1,
    PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
    PHASE085_RUNTIME_ARCHITECTURE_REF_V1,
    PHASE085_STEP_PROGRAM_COUNT,
    build_phase085_normative_program_document_v1,
)

OPERATIONAL_RUNTIME_PROGRAM_CATALOG_RUNTIME_SCHEMA_VERSION: int = 1

PHASE085_CESP_GATE_IDS_V1: tuple[str, ...] = (
    "G-P085-CESP-01",
    "G-P085-ANTI-IDLE-01",
    "G-P085-BND",
    "G-P085-GAP-MATRIX",
    "G-P085-CONT-01",
)


def build_operational_runtime_program_doctrine_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for ``GET /admin/catalog/cortex/operational-runtime/program`` (P085-01)."""
    normative_tree = PHASE085_NORMATIVE_TREE_V1
    return {
        "surface_kind": "doctrine_catalog",
        "operational_runtime_program_catalog_runtime_schema_version": int(
            OPERATIONAL_RUNTIME_PROGRAM_CATALOG_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": f"{normative_tree}{PHASE085_NORMATIVE_INDEX_REF_V1}",
        "program_id": PHASE085_PROGRAM_ID_V1,
        "phase085_program_freeze_version": int(PHASE085_PROGRAM_FREEZE_VERSION),
        "step_program_count": int(PHASE085_STEP_PROGRAM_COUNT),
        "freeze_bundle_ids": list(PHASE085_FREEZE_BUNDLE_IDS),
        "normative_program": build_phase085_normative_program_document_v1(),
        "continuity_law": {
            "spec_ref": f"{normative_tree}phase-085-substrate-continuity-doctrine.md",
            "continuation_nonce_field": PHASE085_CONTINUATION_NONCE_FIELD_V1,
            "resume_receipt_hash_field": PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
            "gate_ids": ["G-P085-CONT-01", "G-P085-PROG-01", "G-P085-WATCH-01"],
        },
        "density_law": {
            "spec_ref": f"{normative_tree}phase-085-retrieval-density-doctrine.md",
            "skip_code_prefix": "RET-SKIP-",
            "gate_ids": ["G-P085-RET-01", "G-P085-GRAPH-01", "G-P085-TCRE-01"],
        },
        "endgoal_law": {
            "spec_ref": f"{normative_tree}phase-085-endgoal-doctrine.md",
            "gate_ids": ["G-P085-ANTI-IDLE-01"],
            "invariant_ids": ["INV-01", "INV-02", "INV-03", "INV-04", "INV-05", "INV-06"],
        },
        "phase_boundary_law": {
            "spec_ref": f"{normative_tree}phase-085-phase-boundaries-doctrine.md",
            "rule_ids": [
                "CESP-BND-08-01",
                "CESP-BND-08-02",
                "CESP-BND-09-01",
                "CESP-BND-10-01",
            ],
            "gate_ids": ["G-P085-BND"],
        },
        "gap_matrix_law": {
            "spec_ref": f"{normative_tree}{PHASE085_GAP_MATRIX_REF_V1}",
            "gate_ids": ["G-P085-GAP-MATRIX"],
            "discipline": "P0_blocks_step_36_freeze",
        },
        "vocabulary_law": {
            "spec_ref": f"{normative_tree}{PHASE085_NORMATIVE_INDEX_REF_V1}#vocabulary",
            "gate_ids": ["G-P085-VOCAB"],
            "term_count": 10,
        },
        "phase09_readiness": {
            "spec_ref": f"{normative_tree}phase-085-phase-09-readiness-doctrine.md",
            "hard_gate": PHASE085_HARD_DOWNSTREAM_GATE_V1,
        },
        "executive_brief_ref": f"{normative_tree}{PHASE085_EXECUTIVE_BRIEF_REF_V1}",
        "gap_matrix_ref": f"{normative_tree}{PHASE085_GAP_MATRIX_REF_V1}",
        "runtime_architecture_ref": f"{normative_tree}{PHASE085_RUNTIME_ARCHITECTURE_REF_V1}",
        "hard_upstream_gate": PHASE085_HARD_UPSTREAM_GATE_V1,
        "gate_ids": list(PHASE085_CESP_GATE_IDS_V1),
    }
