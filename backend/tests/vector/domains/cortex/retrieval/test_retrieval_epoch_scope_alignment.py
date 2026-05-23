"""Unit tests for retrieval epoch / island scope alignment (B2)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    P1_C_ISLAND_SCOPE_KEY_V1,
)
from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    count_retrieval_entries_in_scope_v1,
    realign_island_scope_tags_from_prior_epoch_v1,
)


def test_count_retrieval_entries_in_scope_filters_by_tag() -> None:
    session = MagicMock()
    scope = "island-a"
    summaries = [
        {P1_C_ISLAND_SCOPE_KEY_V1: scope},
        {P1_C_ISLAND_SCOPE_KEY_V1: "other"},
        {},
    ]
    session.scalars.return_value.all.return_value = summaries
    n = count_retrieval_entries_in_scope_v1(
        session,
        tenant_id=uuid.uuid4(),
        published_index_epoch="epoch-1",
        island_scope_id=scope,
    )
    assert n == 1


@pytest.mark.integration
def test_realign_bumps_tags_from_prior_epoch(db_session) -> None:
    tenant_id = uuid.uuid4()
    prior = "epoch-prior"
    target = "epoch-target"
    scope = "scope-primary"
    lookup = "lookup-abc"

    from vector.infrastructure.db.models.cortex_retrieval_index_entry import (
        CortexRetrievalIndexEntry,
    )

    db_session.add(
        CortexRetrievalIndexEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            retrieval_lookup_id=lookup,
            index_kind="causal_chain",
            index_key="k1",
            replay_identity="replay-1",
            traversal_epoch=prior,
            index_epoch=prior,
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
            retrieval_lookup_id=lookup,
            index_kind="causal_chain",
            index_key="k1",
            replay_identity="replay-1",
            traversal_epoch=target,
            index_epoch=target,
            chronology_legality_class="strict",
            causal_legality_class="verified",
            retrieval_legality_class="retrieval_verified",
            degradation_posture="stable",
            continuity_posture="stable",
            artifact_ref_json={},
            omission_summary={},
            retrieval_policy_digest="digest",
        )
    )
    db_session.flush()

    out = realign_island_scope_tags_from_prior_epoch_v1(
        db_session,
        tenant_id=tenant_id,
        prior_published_epoch=prior,
        target_epoch=target,
        island_scope_id=scope,
    )
    assert out["tags_bumped"] == 1
    assert (
        count_retrieval_entries_in_scope_v1(
            db_session,
            tenant_id=tenant_id,
            published_index_epoch=target,
            island_scope_id=scope,
        )
        == 1
    )
