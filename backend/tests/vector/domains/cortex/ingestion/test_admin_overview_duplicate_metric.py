"""Admin overview duplicate-prevention metric guards."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.ingestion.admin_overview import (
    _DUPLICATE_SCAN_MAX_ROWS,
    _collect_duplicate_prevention_metric,
)


def test_duplicate_metric_deferred_when_tenant_is_large() -> None:
    session = MagicMock()
    tenant_id = uuid.uuid4()
    session.scalar.return_value = _DUPLICATE_SCAN_MAX_ROWS + 1

    out = _collect_duplicate_prevention_metric(session, tenant_id)

    assert out["status"] == "deferred"
    assert out["ratio_percent"] is None
    assert out["live_rows_examined"] == _DUPLICATE_SCAN_MAX_ROWS + 1
    session.execute.assert_not_called()
