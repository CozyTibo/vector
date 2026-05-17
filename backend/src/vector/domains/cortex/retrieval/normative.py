"""Phase 07 LRE normative program metadata (P07-01 — normative index + program freeze).

Bumped when the normative index / program-freeze contract changes in a breaking way for consumers.
"""

from __future__ import annotations

from typing import Any

PHASE07_PROGRAM_FREEZE_VERSION: int = 1

PHASE07_STEP_PROGRAM_COUNT: int = 30

PHASE07_FREEZE_BUNDLE_IDS: tuple[str, ...] = (
    "FF-P07-0",
    "FF-P07-1",
    "FF-P07-2",
    "FF-P07-3",
    "FF-P07-4",
    "FF-P07-5",
)

PHASE07_SUBSTRATE_PIPELINE_STAGES_V1: tuple[str, ...] = (
    "Raw",
    "Canonical",
    "Identity",
    "Graph",
    "Traversal",
    "TCRE",
    "Retrieval",
)

PHASE07_REPLAY_IDENTITY_FIELD_V1: str = "retrieval_query_replay_identity"

PHASE07_RUNTIME_PACKAGE_V1: str = "vector.domains.cortex.retrieval"


def build_phase07_normative_program_document_v1() -> dict[str, Any]:
    """Public program-freeze document aligned with ``phase-07-normative-index.md`` (P07-01)."""
    return {
        "phase07_program_freeze_version": int(PHASE07_PROGRAM_FREEZE_VERSION),
        "step_program_count": int(PHASE07_STEP_PROGRAM_COUNT),
        "freeze_bundle_ids": list(PHASE07_FREEZE_BUNDLE_IDS),
        "substrate_pipeline_stages": list(PHASE07_SUBSTRATE_PIPELINE_STAGES_V1),
        "replay_identity_field": PHASE07_REPLAY_IDENTITY_FIELD_V1,
        "runtime_package": PHASE07_RUNTIME_PACKAGE_V1,
        "normative_tree": "DOCS/cortex/retrieval/",
        "constitutional_role": "lawful_deterministic_retrieval_substrate",
    }
