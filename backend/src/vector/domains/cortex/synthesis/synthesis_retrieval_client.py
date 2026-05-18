"""Isolated Phase **07** retrieval client — sole synthesis import surface for query execution.

Normative: ``phase-08-synthesis-runtime-architecture.md`` §1 (retrieval_client).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session


def execute_retrieval_query_for_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope_body: Mapping[str, Any],
) -> dict[str, Any]:
    """Delegate to Phase **07** ``execute_retrieval_query_v1`` (import boundary isolated here)."""
    from vector.domains.cortex.retrieval.retrieval_query_engine import execute_retrieval_query_v1

    return execute_retrieval_query_v1(
        session,
        tenant_id=tenant_id,
        envelope_body=dict(envelope_body),
    )


def is_retrieval_query_execution_error(exc: BaseException) -> bool:
    from vector.domains.cortex.retrieval.query_execution import RetrievalQueryExecutionError

    return isinstance(exc, RetrievalQueryExecutionError)
