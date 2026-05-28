"""Graph dirty-queue reason priority."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.graph.enqueue import enqueue_graph_entity


def test_identity_linked_does_not_downgrade_canon_materialized() -> None:
    session = MagicMock()
    existing = MagicMock()
    existing.reason = "canon_materialized"
    session.scalar.return_value = existing
    tenant_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    enqueue_graph_entity(
        session,
        tenant_id=tenant_id,
        canon_entity_id=entity_id,
        reason="identity_linked",
        entity_type="message",
    )

    assert existing.reason == "canon_materialized"
    session.add.assert_not_called()


def test_extract_reason_upgrades_identity_linked() -> None:
    session = MagicMock()
    existing = MagicMock()
    existing.reason = "identity_linked"
    session.scalar.return_value = existing
    tenant_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    enqueue_graph_entity(
        session,
        tenant_id=tenant_id,
        canon_entity_id=entity_id,
        reason="canon_materialized",
        entity_type="message",
    )

    assert existing.reason == "canon_materialized"
    session.add.assert_not_called()
