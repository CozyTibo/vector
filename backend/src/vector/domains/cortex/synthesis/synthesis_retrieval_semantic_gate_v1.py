"""Wave S4 — Q1: phase 08 must not run on org_link-heavy published retrieval (fail-loud)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

FAILURE_CODE_RETRIEVAL_NOT_SEMANTIC_V1: Final[str] = "retrieval_not_semantic"


class SynthesisRetrievalSemanticError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def is_synthesis_retrieval_semantic_gate_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_synthesis_retrieval_semantic_gate_enabled)
    except Exception:  # noqa: BLE001
        return True


def enforce_retrieval_semantic_before_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
) -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import (
        enforce_retrieval_semantic_mix_before_publish_v1,
        is_retrieval_semantic_mix_gate_enabled_v1,
    )

    if not is_synthesis_retrieval_semantic_gate_enabled_v1():
        return {"skipped": True, "reason": "synthesis_retrieval_semantic_gate_disabled"}
    if not is_retrieval_semantic_mix_gate_enabled_v1():
        return {"skipped": True, "reason": "retrieval_mix_gate_disabled"}
    try:
        mix_audit = enforce_retrieval_semantic_mix_before_publish_v1(
            session,
            tenant_id=tenant_id,
            index_epoch=published_index_epoch,
        )
        return {"ok": True, "mix_audit": mix_audit}
    except Exception as exc:  # noqa: BLE001
        from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import (
            FAILURE_CODE_SEMANTIC_MIX_V1,
            RetrievalSemanticMixError,
        )

        if isinstance(exc, RetrievalSemanticMixError) and exc.code == FAILURE_CODE_SEMANTIC_MIX_V1:
            raise SynthesisRetrievalSemanticError(
                FAILURE_CODE_RETRIEVAL_NOT_SEMANTIC_V1,
                detail=dict(exc.detail or {}),
            ) from exc
        raise
