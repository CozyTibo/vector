"""Phase 08.5 P085-04 — closed vocabulary registry (normative index §Vocabulary)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_INDEX_REF_V1,
    PHASE085_NORMATIVE_TREE_V1,
)

PHASE085_VOCABULARY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_VOCABULARY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}{PHASE085_NORMATIVE_INDEX_REF_V1}#vocabulary"
)

PHASE085_VOCABULARY_TERM_IDS_V1: Final[tuple[str, ...]] = (
    "CESP",
    "OPERATIONAL_ALIVENESS",
    "FAKE_GREEN_IDLE",
    "STARVATION",
    "HEALTHY_IDLE",
    "CONTINUATION",
    "DENSITY",
    "RECOVERY_RECEIPT",
    "RET_SKIP",
    "OPERATIONAL_ALIVE",
)

PHASE085_VOCABULARY_ENTRIES_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "term_id": "CESP",
        "label": "CESP",
        "definition": "Continuous Execution Substrate Program — Phase 08.5",
    },
    {
        "term_id": "OPERATIONAL_ALIVENESS",
        "label": "Operational aliveness",
        "definition": (
            "Tenant satisfies continuity + density + activation + survivability + truth "
            "(executive brief)"
        ),
    },
    {
        "term_id": "FAKE_GREEN_IDLE",
        "label": "Fake-green idle",
        "definition": (
            "Stage healthy while eligible work exists upstream — forbidden for "
            "graph/traversal/TCRE/retrieval/synthesis"
        ),
    },
    {
        "term_id": "STARVATION",
        "label": "Starvation",
        "definition": (
            "Upstream artifacts exist but downstream stage processed_count = 0 beyond T_starve"
        ),
    },
    {
        "term_id": "HEALTHY_IDLE",
        "label": "Healthy idle",
        "definition": (
            "No eligible upstream artifacts and operator-classified idle — may show green"
        ),
    },
    {
        "term_id": "CONTINUATION",
        "label": "Continuation",
        "definition": "Durable async-gap state between pipeline phases (TCRE wait, etc.)",
    },
    {
        "term_id": "DENSITY",
        "label": "Density",
        "definition": "Lawful row/scope growth rate per stage (not raw ingest volume)",
    },
    {
        "term_id": "RECOVERY_RECEIPT",
        "label": "Recovery receipt",
        "definition": "Canonical hash proving idempotent resume attempt",
    },
    {
        "term_id": "RET_SKIP",
        "label": "RET-SKIP-*",
        "definition": "Retrieval materialization skip taxonomy (extends Phase 07)",
    },
    {
        "term_id": "OPERATIONAL_ALIVE",
        "label": "OPERATIONAL_ALIVE",
        "definition": "Maturity class required for Phase 09",
    },
)


def build_phase085_vocabulary_catalog_v1() -> dict[str, Any]:
    """Operator catalog of closed CESP vocabulary (P085-04)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_vocabulary_runtime_schema_version": int(PHASE085_VOCABULARY_RUNTIME_SCHEMA_VERSION),
        "spec_ref": PHASE085_VOCABULARY_SPEC_REF_V1,
        "term_ids": list(PHASE085_VOCABULARY_TERM_IDS_V1),
        "terms": [dict(entry) for entry in PHASE085_VOCABULARY_ENTRIES_V1],
        "term_count": len(PHASE085_VOCABULARY_ENTRIES_V1),
    }


def vocabulary_term_labels_v1() -> list[str]:
    return [str(entry["label"]) for entry in PHASE085_VOCABULARY_ENTRIES_V1]
