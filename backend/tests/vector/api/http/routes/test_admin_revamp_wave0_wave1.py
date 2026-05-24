"""Admin revamp Wave 0 sign-off contracts + post-R7 operator static gates."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADMIN_REVAMP_PLAN = Path("DOCS") / "cortex" / "10-admin" / "ADMIN_REVAMP_PLAN.md"


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / _ADMIN_REVAMP_PLAN).is_file():
            return root
    for root in (Path("/app"), Path("/")):
        if (root / _ADMIN_REVAMP_PLAN).is_file():
            return root
    pytest.fail("repo root not found (DOCS/cortex/10-admin/ADMIN_REVAMP_PLAN.md)")


def _frontend_admin() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        admin = root / "frontend" / "src" / "admin"
        if admin.is_dir():
            return admin
    for admin in (Path("/frontend/src/admin"), Path("/app/frontend/src/admin")):
        if admin.is_dir():
            return admin
    pytest.fail("frontend admin sources not found (mount ./frontend for docker pytest)")


def test_wave0_plan_signoff_document_present() -> None:
    plan = _repo_root() / "DOCS" / "cortex" / "10-admin" / "ADMIN_REVAMP_PLAN.md"
    assert plan.is_file()
    text = plan.read_text(encoding="utf-8")
    assert "Wave 0" in text and "Done" in text
    assert "CORTEX_TRUE_P0_SIGN_OFF" in text


def test_r7_legacy_pipeline_overview_removed() -> None:
    admin = _frontend_admin()
    assert not (admin / "AdminCortexOverviewPage.tsx").is_file()
    assert not (admin / "cortex/usePipelineOverview.ts").is_file()
    assert not (admin / "cortex/PipelineActions.tsx").is_file()


def test_r7_operator_overview_page_present() -> None:
    admin = _frontend_admin()
    overview = (admin / "operator/OperatorOverviewPage.tsx").read_text(encoding="utf-8")
    assert "useOperatorOverview" in overview
    assert "OperatorCompactActions" in overview


def test_r7_ingestion_no_replay_or_doctrine_tabs() -> None:
    ingestion = (_frontend_admin() / "AdminCortexIngestionPage.tsx").read_text(encoding="utf-8")
    assert "trigger-replay" not in ingestion
    assert "CORTEX_REPLAY_CONFIRM_PHRASE" not in ingestion
    assert '"replays"' not in ingestion
    assert 'activeTab === "verification"' not in ingestion


def test_r7_job_detail_pages_read_only() -> None:
    job_detail = (_frontend_admin() / "AdminCortexReasoningJobDetailPage.tsx").read_text(encoding="utf-8")
    synthesis_detail = (_frontend_admin() / "AdminCortexSynthesisJobDetailPage.tsx").read_text(encoding="utf-8")
    assert "useMutation" not in job_detail
    assert "useMutation" not in synthesis_detail
    assert "/retry" not in synthesis_detail


def test_wave4_admin_routes_have_no_bypass_fragments() -> None:
    routes_dir = _repo_root() / "backend" / "src" / "vector" / "api" / "http" / "routes"
    forbidden = ("materialize-backlog", "flush-rerun", "progression/continue")
    for path in routes_dir.glob("admin*.py"):
        text = path.read_text(encoding="utf-8")
        for frag in forbidden:
            assert frag not in text, f"{path.name} still references {frag}"


def test_wave4_bypass_guard_passes() -> None:
    from vector.domains.cortex.execution.admin_bypass_guard import (
        verify_no_admin_bypass_routes_registered_v1,
    )

    assert verify_no_admin_bypass_routes_registered_v1() == []
