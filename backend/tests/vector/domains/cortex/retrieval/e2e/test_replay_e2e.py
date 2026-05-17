"""E2E replay stability after pipeline materialization."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    index_tcre_chain_for_retrieval_v1,
)
from vector.domains.cortex.retrieval.testing import assert_lawful_query_replay_stable_v1


@pytest.mark.integration
def test_replay_e2e_double_query_identity(db_session: Session, e2e_tenant_id: uuid.UUID) -> None:
    """Uses materialization API (not raw ORM insert) with published epoch."""
    replay = f"e2e-replay-{uuid.uuid4().hex[:8]}"
    chain = f"chain-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=e2e_tenant_id,
        causal_chain_id=chain,
        replay_identity=replay,
        traversal_epoch=f"epoch-{uuid.uuid4().hex[:8]}",
    )
    db_session.commit()
    envelope = {
        "schema_version": 1,
        "tenant_id": str(e2e_tenant_id),
        "workload_class": "causal_chain",
        "intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_lookup_id": row.retrieval_lookup_id,
        "replay_pins": {
            "replay_identity": replay,
            "index_epoch": row.index_epoch,
            "tcre_policy_bundle_digest": TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
            "expected_replay_identity": replay,
        },
    }
    out = assert_lawful_query_replay_stable_v1(db_session, tenant_id=e2e_tenant_id, envelope=envelope)
    assert out["passed"]
