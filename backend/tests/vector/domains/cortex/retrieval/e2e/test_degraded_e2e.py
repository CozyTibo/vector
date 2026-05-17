"""E2E degraded substrate — lawful omissions, not silent failure."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.query_execution import (
    RetrievalQueryExecutionError,
    execute_retrieval_query_envelope_v1,
)


@pytest.mark.integration
def test_degraded_e2e_unresolved_addressing(db_session: Session, e2e_tenant_id: uuid.UUID) -> None:
    with pytest.raises(RetrievalQueryExecutionError):
        execute_retrieval_query_envelope_v1(
            db_session,
            tenant_id=e2e_tenant_id,
            body={
                "schema_version": 1,
                "tenant_id": str(e2e_tenant_id),
                "workload_class": "causal_chain",
                "intent": "inspect",
                "execution_partition": "authoritative",
                "addressing": {"artifact_kind": "causal_chain", "artifact_ref": "missing-ref"},
            },
        )
