"""Unit tests for retrieval publish contract helpers."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.retrieval.retrieval_publish_contract import (
    materialize_entry_respecting_publish_contract_v1,
)


def test_defer_publish_while_epoch_building(monkeypatch) -> None:
    session = MagicMock()
    epoch_row = MagicMock()
    epoch_row.build_state = "BUILDING"
    tenant_id = uuid.uuid4()
    index_epoch = "epoch-test"

    monkeypatch.setattr(
        "vector.domains.cortex.retrieval.retrieval_publish_contract.get_index_epoch_row_v1",
        lambda *_a, **_k: epoch_row,
    )
    captured: dict = {}

    def _fake_mat(session, *, tenant_id, index_epoch, auto_publish, **kwargs):
        captured["auto_publish"] = auto_publish
        return {"ok": True}

    monkeypatch.setattr(
        "vector.domains.cortex.retrieval.retrieval_index_materialization.materialize_retrieval_index_entry_v1",
        _fake_mat,
    )

    materialize_entry_respecting_publish_contract_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=index_epoch,
        auto_publish=True,
    )
    assert captured["auto_publish"] is False
