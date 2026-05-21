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
    assert "pipeline/overview" in overview
    assert "PipelineActions" in overview


def test_wave2_overview_uses_pipeline_api() -> None:
    actions = (_frontend_admin() / "cortex/PipelineActions.tsx").read_text(encoding="utf-8")
    assert "pipeline/run" in actions
    assert "execution/rerun" not in actions
    assert "execution/clear" not in actions
    assert (_frontend_admin() / "cortex/PhasePageShell.tsx").is_file()
    ingestion = (_frontend_admin() / "AdminCortexIngestionPage.tsx").read_text(encoding="utf-8")
    shell = (_frontend_admin() / "cortex/PhasePageShell.tsx").read_text(encoding="utf-8")
    assert "PhasePageShell" in ingestion
    assert "pipeline/phases/${phase}/summary" in shell or "pipeline/phases/" in shell


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


def test_wave1_ingestion_no_replay_or_doctrine_tabs() -> None:
    ingestion = (_frontend_admin() / "AdminCortexIngestionPage.tsx").read_text(encoding="utf-8")
    assert "trigger-replay" not in ingestion
    assert "CORTEX_REPLAY_CONFIRM_PHRASE" not in ingestion
    assert '"replays"' not in ingestion
    assert 'activeTab === "verification"' not in ingestion
    assert 'activeTab === "coverage"' not in ingestion
    assert 'activeTab === "metrics"' not in ingestion


def test_wave1_reconstruction_no_bypass_post_buttons() -> None:
    overview = (_frontend_admin() / "AdminCortexReasoningOverviewPage.tsx").read_text(encoding="utf-8")
    job_detail = (_frontend_admin() / "AdminCortexReasoningJobDetailPage.tsx").read_text(encoding="utf-8")
    assert "runtime/reconstruct" not in overview
    assert "useMutation" not in overview
    assert "replay-twin" not in job_detail
    assert "useMutation" not in job_detail


def test_wave1_canonical_health_no_materialize_mutations() -> None:
    canonical = (_frontend_admin() / "AdminCortexCanonicalHealthPage.tsx").read_text(encoding="utf-8")
    assert "useMutation" not in canonical
    assert "materialize-backlog" not in canonical
