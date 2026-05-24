"""R7 — operator frontend cleanup static gates."""

from __future__ import annotations

from pathlib import Path

import pytest


def _frontend_admin() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        admin = root / "frontend" / "src" / "admin"
        if admin.is_dir():
            return admin
    pytest.fail("frontend admin sources not found")


def test_r7_legacy_pipeline_pages_removed() -> None:
    admin = _frontend_admin()
    removed = [
        "AdminCortexOverviewPage.tsx",
        "AdminCortexGraphPage.tsx",
        "AdminCortexIdentityPage.tsx",
        "AdminCortexReconstructionPage.tsx",
        "AdminCortexRetrievalPage.tsx",
        "AdminCortexSynthesisPage.tsx",
        "AdminCortexCanonicalHealthPage.tsx",
        "cortex/usePipelineOverview.ts",
        "cortex/fetchPipelineOverviewSlice.ts",
        "cortex/PhasePageShell.tsx",
        "cortex/PipelineActions.tsx",
        "operator/AdminCortexOverviewGateway.tsx",
    ]
    for name in removed:
        assert not (admin / name).is_file(), name


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "frontend" / "src" / "main.tsx").is_file():
            return root
    pytest.fail("repo root not found")


def test_r7_operator_nav_and_routes() -> None:
    admin = _frontend_admin()
    layout = (admin / "AdminTenantCortexLayout.tsx").read_text(encoding="utf-8")
    main = (_repo_root() / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    for label in ("Overview", "Runtime", "Queues", "Inspect", "Ingestion", "Canonical", "Settings"):
        assert label in layout
    assert "OperatorOverviewPage" in main
    assert "OperatorRuntimePage" in main
    assert "OperatorGraphInspectPage" in main
    assert "AdminCortexOverviewGateway" not in main


def test_r7_ingestion_uses_operator_overview() -> None:
    admin = _frontend_admin()
    ingestion = (admin / "AdminCortexIngestionPage.tsx").read_text(encoding="utf-8")
    assert "useOperatorOverview" in ingestion
    assert "PhasePageShell" not in ingestion
    assert "usePipelineOverview" not in ingestion


def test_r7_operator_integration_routes_present() -> None:
    """Overview + runtime + inspect graph remain wired (backend R0–R5)."""
    from vector.api.http.routes import admin_cortex_operator  # noqa: PLC0415

    src = Path(admin_cortex_operator.__file__).read_text(encoding="utf-8")
    assert '"/overview"' in src or "operator/overview" in src
    assert '"/runtime"' in src or "operator/runtime" in src
    assert "inspect/retrieval/lineage" in src or "inspect/retrieval" in src
