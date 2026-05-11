"""Operator-facing JSON: Phase 3.5 continuity foundation (contracts + versions)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from vector.domains.cortex.continuity.bundle_continuity_semantics import CONTINUITY_BUNDLE_SEMANTICS_VERSION
from vector.domains.cortex.continuity.edge_contracts import CONTINUITY_EDGE_CONTRACT_VERSION, ContinuityEdgeKind
from vector.domains.cortex.continuity.execution_primitives import EXECUTION_PRIMITIVE_SCHEMA_VERSION, ExecutionPrimitiveKind
from vector.domains.cortex.continuity.reference_schema import REFERENCE_CONTRACT_VERSION, ReferenceFamily
from vector.domains.cortex.continuity.temporal_continuity import TEMPORAL_CONTINUITY_HELPER_VERSION

CONTINUITY_FOUNDATION_SCHEMA_VERSION: Final[int] = 1


def build_phase35_continuity_public_document(*, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
    return {
        "continuity_foundation_schema_version": CONTINUITY_FOUNDATION_SCHEMA_VERSION,
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "normative_doctrine": "DOCS/cortex/03-canonical/phase-35-organizational-continuity-foundation.md",
        "contract_versions": {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "continuity_edge_contract_version": CONTINUITY_EDGE_CONTRACT_VERSION,
            "execution_primitive_schema_version": EXECUTION_PRIMITIVE_SCHEMA_VERSION,
            "continuity_bundle_semantics_version": CONTINUITY_BUNDLE_SEMANTICS_VERSION,
            "temporal_continuity_helper_version": TEMPORAL_CONTINUITY_HELPER_VERSION,
        },
        "reference_families": [f.value for f in ReferenceFamily],
        "continuity_edge_kinds": [e.value for e in ContinuityEdgeKind],
        "execution_primitive_kinds": [p.value for p in ExecutionPrimitiveKind],
        "non_goals": [
            "identity_merge",
            "causal_inference",
            "ml_edge_prediction",
            "semantic_summarization",
        ],
        "phase04_inputs": [
            "NormalizedReference.canonical_form for join keys",
            "ContinuityEdgeContract for graph projection",
            "ExecutionPrimitiveEnvelope for org-shaped spans",
            "bundle_continuity_semantics for cross-pin rules",
        ],
    }
