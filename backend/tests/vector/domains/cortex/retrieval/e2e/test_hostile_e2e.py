"""E2E hostile paths — fail-closed legality, no orphan lawful reads."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError
from vector.domains.cortex.retrieval.retrieval_query_engine import execute_retrieval_query_v1


@pytest.mark.integration
def test_hostile_e2e_query_without_published_epoch(db_session: Session, e2e_tenant_id: uuid.UUID) -> None:
    with pytest.raises((RetrievalLegalityError, ValueError)):
        execute_retrieval_query_v1(
            db_session,
            tenant_id=e2e_tenant_id,
            retrieval_lookup_id="sha256:" + "f" * 64,
            envelope_body={
                "replay_pins": {"index_epoch": "epoch-never-published-00000000"},
            },
        )
