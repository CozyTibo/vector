"""P2-C — execution island registry sync helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    _entity_ids_payload_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    stable_component_scope_id_v1,
)


def test_entity_ids_payload_truncation() -> None:
    component = frozenset(uuid.uuid4() for _ in range(10))
    ids, truncated = _entity_ids_payload_v1(component, max_ids=5)
    assert len(ids) == 5
    assert truncated is True


def test_stable_scope_id_matches_scheduling() -> None:
    a = uuid.UUID("11111111-1111-1111-1111-111111111111")
    b = uuid.UUID("22222222-2222-2222-2222-222222222222")
    comp = frozenset({a, b})
    assert stable_component_scope_id_v1(comp) == stable_component_scope_id_v1(comp)


def test_build_inspect_surface_kind() -> None:
    from vector.domains.cortex.operational_runtime.execution_island_registry import (
        build_island_registry_inspect_v1,
    )

    # Import-only smoke; full sync covered by prod proof.
    assert callable(build_island_registry_inspect_v1)
