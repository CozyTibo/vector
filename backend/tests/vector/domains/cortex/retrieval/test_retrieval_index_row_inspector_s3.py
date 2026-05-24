"""Phase S3.6 — retrieval index row inspector."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.retrieval.retrieval_index_row_inspector_v1 import (
    ROW_CLASS_GOOD_EXECUTION_V1,
    ROW_CLASS_GOOD_SUPPORTING_V1,
    ROW_CLASS_USELESS_MIRROR_V1,
    classify_retrieval_index_row_v1,
)


def _row(*, kind: str, traversal_epoch: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(index_kind=kind, traversal_epoch=traversal_epoch)


def test_org_link_without_execution_context_is_useless_mirror() -> None:
    ctx = {"has_execution_rows": False, "execution_traversal_epochs": []}
    assert (
        classify_retrieval_index_row_v1(_row(kind="org_link", traversal_epoch="te-1"), execution_context=ctx)
        == ROW_CLASS_USELESS_MIRROR_V1
    )


def test_org_link_with_matching_traversal_epoch_is_supporting() -> None:
    ctx = {"has_execution_rows": True, "execution_traversal_epochs": ["te-1"]}
    assert (
        classify_retrieval_index_row_v1(_row(kind="org_link", traversal_epoch="te-1"), execution_context=ctx)
        == ROW_CLASS_GOOD_SUPPORTING_V1
    )


def test_materialization_row_is_good_execution() -> None:
    ctx = {"has_execution_rows": True, "execution_traversal_epochs": ["te-1"]}
    assert (
        classify_retrieval_index_row_v1(_row(kind="materialization"), execution_context=ctx)
        == ROW_CLASS_GOOD_EXECUTION_V1
    )


def test_admin_route_registers_index_row_inspector() -> None:
    import inspect

    from vector.api.http.routes import admin_cortex_retrieval as mod

    src = inspect.getsource(mod.register_cortex_retrieval_routes)
    assert "/index-row-inspector" in src
    assert "build_retrieval_index_row_inspector_v1" in src
