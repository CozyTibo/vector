"""Phase 08 doctrine catalog builders (operator spec mirrors — not tenant truth)."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.synthesis.normative import (
    PHASE08_DEGRADATION_TAXONOMY_SPEC_REF_V1,
    PHASE08_FREEZE_BUNDLE_IDS,
    PHASE08_NORMATIVE_TREE_V1,
    PHASE08_PROGRAM_FREEZE_VERSION,
    PHASE08_REPLAY_IDENTITY_FIELD_V1,
    PHASE08_REPLAY_SPEC_REF_V1,
    PHASE08_STEP_PROGRAM_COUNT,
    PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
    build_phase08_normative_program_document_v1,
)
from vector.domains.cortex.synthesis.synthesis_constitutional_freeze import (
    P08_FINAL_FREEZE_BUNDLE_ID_V1,
    PHASE08_DOCTRINE_FREEZE_STATUS_V1,
    build_synthesis_constitutional_freeze_banner_v1,
)

SYNTHESIS_PROGRAM_CATALOG_RUNTIME_SCHEMA_VERSION: int = 1

PHASE08_REPLAY_GATE_IDS_V1: tuple[str, ...] = (
    "G-P08-REPLAY-01",
    "G-P08-REPLAY-02",
)


def build_synthesis_program_doctrine_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for ``GET /admin/catalog/cortex/synthesis/program`` (P08-01)."""
    normative_tree = PHASE08_NORMATIVE_TREE_V1
    return {
        "surface_kind": "doctrine_catalog",
        "synthesis_program_catalog_runtime_schema_version": int(
            SYNTHESIS_PROGRAM_CATALOG_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": f"{normative_tree}phase-08-normative-index.md",
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "step_program_count": int(PHASE08_STEP_PROGRAM_COUNT),
        "freeze_bundle_ids": list(PHASE08_FREEZE_BUNDLE_IDS),
        "normative_program": build_phase08_normative_program_document_v1(),
        "replay_law": {
            "spec_ref": f"{normative_tree}{PHASE08_REPLAY_SPEC_REF_V1}",
            "replay_identity_field": PHASE08_REPLAY_IDENTITY_FIELD_V1,
            "upstream_replay_identity_field": PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
            "gate_ids": list(PHASE08_REPLAY_GATE_IDS_V1),
        },
        "degradation_registry": {
            "spec_ref": f"{normative_tree}{PHASE08_DEGRADATION_TAXONOMY_SPEC_REF_V1}",
            "code_prefix": "SD-",
        },
        "constitutional_freeze_bundle": P08_FINAL_FREEZE_BUNDLE_ID_V1,
        "doctrine_freeze_status": PHASE08_DOCTRINE_FREEZE_STATUS_V1,
        "freeze_banner": build_synthesis_constitutional_freeze_banner_v1(),
    }
