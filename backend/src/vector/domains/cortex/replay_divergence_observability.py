"""Upstream-safe replay divergence hook (Phase 07/08 → Phase 08.5 CESP).

Synthesis and other upstream packages MUST import this module instead of
``operational_runtime`` to preserve **G-P085-BND-ACYCLIC** import discipline.
"""

from __future__ import annotations

from typing import Any, Final

REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1: Final[str] = "retrieval"
REPLAY_DIVERGENCE_SOURCE_SYNTHESIS_V1: Final[str] = "synthesis"


def on_replay_divergence_observed_v1(
    *,
    tenant_id: str,
    source: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """Persist divergence + evaluate replay storm (**G-P085-ECON-02**)."""
    from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
        handle_replay_divergence_observed_v1,
    )

    handle_replay_divergence_observed_v1(
        tenant_id=tenant_id,
        source=source,
        detail=detail,
    )
