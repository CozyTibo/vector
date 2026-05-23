"""P2-C — execution island registry sync helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

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
    import inspect

    from vector.domains.cortex.operational_runtime.execution_island_registry import (
        build_island_registry_inspect_v1,
    )

    assert callable(build_island_registry_inspect_v1)
    assert inspect.signature(build_island_registry_inspect_v1).parameters["sync"].default is False


@pytest.mark.integration
def test_resolve_last_retrieval_epoch_prefers_published(db_session) -> None:
    import uuid

    from vector.domains.cortex.retrieval.retrieval_component_materialization import (
        P1_C_ISLAND_SCOPE_KEY_V1,
    )
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        ensure_published_index_epoch_v1,
        start_retrieval_index_build_v1,
        transition_retrieval_index_build_v1,
    )
    from vector.domains.cortex.operational_runtime.execution_island_registry import (
        resolve_last_retrieval_epoch_for_scope_v1,
    )
    from vector.infrastructure.db.models.cortex_retrieval_index_entry import (
        CortexRetrievalIndexEntry,
    )

    tenant_id = uuid.uuid4()
    scope = "scope-test"
    old_epoch = "epoch-old-tag-heavy"
    published_epoch = "epoch-published"

    for i in range(3):
        db_session.add(
            CortexRetrievalIndexEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                retrieval_lookup_id=f"lookup-old-{i}",
                index_kind="causal_chain",
                index_key=f"k{i}",
                replay_identity=f"replay-{i}",
                traversal_epoch=old_epoch,
                index_epoch=old_epoch,
                chronology_legality_class="strict",
                causal_legality_class="verified",
                retrieval_legality_class="retrieval_verified",
                degradation_posture="stable",
                continuity_posture="stable",
                artifact_ref_json={},
                omission_summary={P1_C_ISLAND_SCOPE_KEY_V1: scope},
                retrieval_policy_digest="digest",
            )
        )
    db_session.add(
        CortexRetrievalIndexEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            retrieval_lookup_id="lookup-published",
            index_kind="causal_chain",
            index_key="kp",
            replay_identity="replay-p",
            traversal_epoch=published_epoch,
            index_epoch=published_epoch,
            chronology_legality_class="strict",
            causal_legality_class="verified",
            retrieval_legality_class="retrieval_verified",
            degradation_posture="stable",
            continuity_posture="stable",
            artifact_ref_json={},
            omission_summary={P1_C_ISLAND_SCOPE_KEY_V1: scope},
            retrieval_policy_digest="digest",
        )
    )
    row = start_retrieval_index_build_v1(
        db_session, tenant_id=tenant_id, index_epoch=published_epoch
    )
    transition_retrieval_index_build_v1(db_session, epoch_row=row, to_state="BUILDING")
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        publish_retrieval_index_epoch_v1,
    )

    publish_retrieval_index_epoch_v1(
        db_session, tenant_id=tenant_id, index_epoch=published_epoch
    )
    db_session.flush()

    resolved = resolve_last_retrieval_epoch_for_scope_v1(
        db_session,
        tenant_id=tenant_id,
        island_scope_id=scope,
    )
    assert resolved == published_epoch
