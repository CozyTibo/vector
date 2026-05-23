"""Pipeline admin operator primary KPI helpers."""

from vector.domains.cortex.pipeline.canonical_operator_metrics import (
    OPERATOR_KPI_PRIMARY_DRAINABLE_V1,
    _canonical_operator_backlog_count,
)
from vector.settings import Settings


def test_canonical_operator_backlog_uses_drainable() -> None:
    metrics = {
        "drainable_routable_estimate": 7,
        "raw_minus_mat_admin_gap": 9000,
    }
    assert _canonical_operator_backlog_count(metrics) == 7


def test_drainable_primary_enabled_by_default() -> None:
    assert Settings.model_fields["cortex_admin_primary_kpi_drainable"].default is True
    assert OPERATOR_KPI_PRIMARY_DRAINABLE_V1 == "drainable_routable_estimate"
