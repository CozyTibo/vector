"""Unit tests for unlinked scoped entity counting."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.graph.admin import count_unlinked_scoped_entities


def test_count_unlinked_scoped_entities_uses_scalar_count() -> None:
    tenant_id = uuid.uuid4()
    session = MagicMock()
    session.scalar.return_value = 42

    count = count_unlinked_scoped_entities(session, tenant_id)

    assert count == 42
    session.scalar.assert_called_once()
