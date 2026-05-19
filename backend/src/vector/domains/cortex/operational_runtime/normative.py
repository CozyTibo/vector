"""Phase 08.5 CESP normative program metadata (P085-01 — normative index + program freeze)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Final

PHASE085_PROGRAM_FREEZE_VERSION: Final[int] = 1

PHASE085_STEP_PROGRAM_COUNT: Final[int] = 36

PHASE085_PROGRAM_ID_V1: Final[str] = "CESP"

PHASE085_FREEZE_BUNDLE_IDS: Final[tuple[str, ...]] = (
    "FF-P085-0",
    "FF-P085-1",
    "FF-P085-2",
    "FF-P085-3",
    "FF-P085-4",
    "FF-P085-5",
    "FF-P085-6",
)

PHASE085_SUBSTRATE_EXECUTION_CHAIN_V1: Final[tuple[str, ...]] = (
    "ingestion",
    "post_ingestion_refresh",
    "phase_02_canonical",
    "phase_03_identity",
    "phase_04_graph",
    "phase_05_traversal",
    "phase_06_tcre",
    "phase_07_retrieval",
    "phase_08_synthesis",
)

PHASE085_CONTINUATION_NONCE_FIELD_V1: Final[str] = "continuation_nonce"

PHASE085_RESUME_RECEIPT_HASH_FIELD_V1: Final[str] = "resume_receipt_hash"

PHASE085_RUNTIME_PACKAGE_V1: Final[str] = "vector.domains.cortex.operational_runtime"

PHASE085_NORMATIVE_TREE_V1: Final[str] = "DOCS/cortex/operational-runtime/"

PHASE085_NORMATIVE_INDEX_REF_V1: Final[str] = "phase-085-normative-index.md"

PHASE085_EXECUTIVE_BRIEF_REF_V1: Final[str] = "PHASE085_EXECUTIVE_BRIEF.md"

PHASE085_GAP_MATRIX_REF_V1: Final[str] = "cesp-spec-gap-matrix.md"

PHASE085_RUNTIME_ARCHITECTURE_REF_V1: Final[str] = "phase-085-runtime-architecture.md"

PHASE085_HARD_UPSTREAM_GATE_V1: Final[str] = "phase_08_sil_frozen_implementation"

PHASE085_HARD_DOWNSTREAM_GATE_V1: Final[str] = "G-P085-CLOSE-01_before_phase_09"

PHASE085_PROGRAM_FREEZE_BUNDLE_V1: Final[str] = "P085-PROGRAM-FREEZE-2026-05-18"

PHASE085_DOCTRINE_IMPLEMENTATION_STATUS_V1: Final[str] = "Strong (Step 1 implementation)"


def _repo_root_v1() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        marker = root / "DOCS" / "cortex" / "operational-runtime" / PHASE085_NORMATIVE_INDEX_REF_V1
        if marker.is_file():
            return root
    msg = "operational_runtime_normative_repo_root_not_found"
    raise FileNotFoundError(msg)


def hash_phase085_executive_brief_fixture_file_v1() -> str:
    """Pinned digest of ``PHASE085_EXECUTIVE_BRIEF.md`` for program-freeze attestation."""
    path = _repo_root_v1() / "DOCS" / "cortex" / "operational-runtime" / PHASE085_EXECUTIVE_BRIEF_REF_V1
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def build_phase085_normative_program_document_v1() -> dict[str, Any]:
    """Public program-freeze document aligned with ``phase-085-normative-index.md`` (P085-01 / CESp-01)."""
    return {
        "phase085_program_freeze_version": int(PHASE085_PROGRAM_FREEZE_VERSION),
        "program_id": PHASE085_PROGRAM_ID_V1,
        "step_program_count": int(PHASE085_STEP_PROGRAM_COUNT),
        "freeze_bundle_ids": list(PHASE085_FREEZE_BUNDLE_IDS),
        "substrate_execution_chain": list(PHASE085_SUBSTRATE_EXECUTION_CHAIN_V1),
        "continuation_nonce_field": PHASE085_CONTINUATION_NONCE_FIELD_V1,
        "resume_receipt_hash_field": PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
        "runtime_package": PHASE085_RUNTIME_PACKAGE_V1,
        "normative_tree": PHASE085_NORMATIVE_TREE_V1,
        "constitutional_role": "continuous_execution_substrate_maturation",
        "normative_index_ref": PHASE085_NORMATIVE_INDEX_REF_V1,
        "executive_brief_ref": PHASE085_EXECUTIVE_BRIEF_REF_V1,
        "gap_matrix_ref": PHASE085_GAP_MATRIX_REF_V1,
        "runtime_architecture_ref": PHASE085_RUNTIME_ARCHITECTURE_REF_V1,
        "executive_brief_fixture_digest_sha256": hash_phase085_executive_brief_fixture_file_v1(),
        "hard_upstream_gate": PHASE085_HARD_UPSTREAM_GATE_V1,
        "hard_downstream_gate": PHASE085_HARD_DOWNSTREAM_GATE_V1,
        "program_freeze_bundle": PHASE085_PROGRAM_FREEZE_BUNDLE_V1,
        "doctrine_implementation_status": PHASE085_DOCTRINE_IMPLEMENTATION_STATUS_V1,
        "primary_gate_id": "G-P085-CESP-01",
    }
