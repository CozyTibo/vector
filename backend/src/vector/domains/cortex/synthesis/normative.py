"""Phase 08 SIL normative program metadata (P08-01 — normative index + program freeze).

Bumped when the normative index / program-freeze contract changes in a breaking way for consumers.
"""

from __future__ import annotations

from typing import Any

PHASE08_PROGRAM_FREEZE_VERSION: int = 1

PHASE08_STEP_PROGRAM_COUNT: int = 35

PHASE08_FREEZE_BUNDLE_IDS: tuple[str, ...] = (
    "FF-P08-0",
    "FF-P08-1",
    "FF-P08-2",
    "FF-P08-3",
    "FF-P08-4",
    "FF-P08-5",
)

PHASE08_SUBSTRATE_PIPELINE_STAGES_V1: tuple[str, ...] = (
    "Ingest",
    "Raw",
    "Canonical",
    "Identity",
    "OCTS",
    "TCRE",
    "Retrieval",
    "Synthesis",
    "Products",
)

PHASE08_REPLAY_IDENTITY_FIELD_V1: str = "synthesis_job_replay_identity"

PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1: str = "retrieval_query_replay_identity"

PHASE08_RUNTIME_PACKAGE_V1: str = "vector.domains.cortex.synthesis"

PHASE08_NORMATIVE_TREE_V1: str = "DOCS/cortex/synthesis/"

PHASE08_REPLAY_SPEC_REF_V1: str = "phase-08-replay-equivalence-spec.md"

PHASE08_DEGRADATION_TAXONOMY_SPEC_REF_V1: str = "phase-08-failure-degradation-taxonomy.md"

PHASE08_POLICY_PACK_FIXTURE_REF_V1: str = "fixtures/SynthesisPolicyPackV1_Default.json"

PHASE08_CONSTITUTIONAL_FREEZE_BUNDLE_V1: str = "P08-FINAL-FREEZE-2026-05-17"

PHASE08_DOCTRINE_FREEZE_STATUS_V1: str = "Frozen (implementation)"


def build_phase08_normative_program_document_v1() -> dict[str, Any]:
    """Public program-freeze document aligned with ``phase-08-normative-index.md`` (P08-01)."""
    from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
        hash_synthesis_policy_pack_fixture_file_v1,
    )

    return {
        "phase08_program_freeze_version": int(PHASE08_PROGRAM_FREEZE_VERSION),
        "step_program_count": int(PHASE08_STEP_PROGRAM_COUNT),
        "freeze_bundle_ids": list(PHASE08_FREEZE_BUNDLE_IDS),
        "substrate_pipeline_stages": list(PHASE08_SUBSTRATE_PIPELINE_STAGES_V1),
        "replay_identity_field": PHASE08_REPLAY_IDENTITY_FIELD_V1,
        "upstream_replay_identity_field": PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
        "runtime_package": PHASE08_RUNTIME_PACKAGE_V1,
        "normative_tree": PHASE08_NORMATIVE_TREE_V1,
        "constitutional_role": "execution_intelligence_layer",
        "replay_law_spec_ref": PHASE08_REPLAY_SPEC_REF_V1,
        "degradation_taxonomy_spec_ref": PHASE08_DEGRADATION_TAXONOMY_SPEC_REF_V1,
        "policy_pack_fixture_ref": PHASE08_POLICY_PACK_FIXTURE_REF_V1,
        "policy_pack_fixture_digest_sha256": hash_synthesis_policy_pack_fixture_file_v1(),
        "hard_upstream_gate": (
            "phase_07_authoritative_retrieval_envelopes_published_index_epoch_"
            "retrieval_query_replay_identity"
        ),
        "hard_downstream_contract": (
            "phase_09_consumes_SynthesisIntelligenceArtifactV1_and_synthesis_job_receipt_only"
        ),
        "constitutional_freeze_bundle": PHASE08_CONSTITUTIONAL_FREEZE_BUNDLE_V1,
        "doctrine_freeze_status": PHASE08_DOCTRINE_FREEZE_STATUS_V1,
    }
