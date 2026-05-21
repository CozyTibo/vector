"""Admin revamp Wave 0 sign-off contracts + Wave 1 surface-kill static gates."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _frontend_admin() -> Path:
    return _repo_root() / "frontend" / "src" / "admin"


def test_wave0_plan_signoff_document_present() -> None:
    plan = _repo_root() / "DOCS" / "cortex" / "10-admin" / "ADMIN_REVAMP_PLAN.md"
    assert plan.is_file()
    text = plan.read_text(encoding="utf-8")
    assert "Wave 0" in text and "Done" in text
    assert "CORTEX_TRUE_P0_SIGN_OFF" in text


def test_wave1_overview_no_flush_rerun_in_frontend() -> None:
    overview = (_frontend_admin() / "AdminCortexOverviewPage.tsx").read_text(encoding="utf-8")
    assert "flush-rerun-to-identity" not in overview
    assert "Replay all connectors" not in overview
    assert "execution/rerun" in overview or "PipelineActions" in overview


def test_wave1_deleted_doctrine_pages_absent() -> None:
    removed = [
        "AdminCortexVerificationPage.tsx",
        "AdminCortexMemoryPage.tsx",
        "AdminCortexCanonicalAdvancedLayout.tsx",
        "AdminCortexRetrievalCatalogPage.tsx",
        "retrievalAdminSurfaces.ts",
    ]
    for name in removed:
        assert not (_frontend_admin() / name).is_file(), name


def test_wave1_nav_has_nine_operator_tabs() -> None:
    layout = (_frontend_admin() / "AdminTenantCortexLayout.tsx").read_text(encoding="utf-8")
    for label in (
        "Overview",
        "Ingestion",
        "Canonical",
        "Identity",
        "Graph",
        "Reconstruction",
        "Retrieval",
        "Synthesis",
        "Settings",
    ):
        assert label in layout
    assert "Identity certification" not in layout
    assert "Traversal" not in layout or "Reconstruction" in layout
