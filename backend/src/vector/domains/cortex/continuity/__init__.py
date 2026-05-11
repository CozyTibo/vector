"""Phase 3.5 — organizational continuity foundation (reference plane, edges, primitives, bundle semantics).

Normative: ``DOCS/cortex/03-canonical/phase-35-organizational-continuity-foundation.md``.

This package introduces **contracts and deterministic utilities only**. It does not resolve identities,
infer causality, or persist graph storage. Phase 04+ consumes these primitives.
"""

from __future__ import annotations

from vector.domains.cortex.continuity.public_document import (
    CONTINUITY_FOUNDATION_SCHEMA_VERSION,
    build_phase35_continuity_public_document,
)

__all__ = [
    "CONTINUITY_FOUNDATION_SCHEMA_VERSION",
    "build_phase35_continuity_public_document",
]
