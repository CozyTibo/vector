"""§6 Step 11 — perception_qa labels on fetch-debug (flag + optional ?perception=regex echo)."""

from __future__ import annotations

from vector.contracts.manager_insights_activity import ManagerInsightPerceptionQaDebug
from vector.domains.manager_insights.coordination_perception import build_perception_qa_debug
from vector.settings import Settings


def _settings(*, perception_llm: bool) -> Settings:
    return Settings.model_construct(
        database_url="postgresql://perception-qa-step11-test",
        openai_api_key="sk-test",
        openai_model="gpt-4o-mini",
        env="development",
        secret_key="dev-only-secret-key-min-32-chars-long!!",
        vector_manager_insights_perception_llm=perception_llm,
        vector_manager_insights_include_execution_graph=False,
        vector_manager_insights_skip_narrative_steps=False,
        vector_manager_insights_gaps_use_graph=False,
    )


def test_build_perception_qa_regex_only_when_flag_off() -> None:
    q = build_perception_qa_debug(_settings(perception_llm=False))
    assert q == ManagerInsightPerceptionQaDebug(
        evidence_path="regex_evidence_only",
        query_perception_regex=False,
        query_include_execution_graph=False,
        query_master_plan_debug=False,
        query_max_decisions=None,
        max_decisions_cap_applied=6,
        decisions_prioritized_full_count=0,
        query_persist_decisions=False,
        step42_gap_demotion_by_gap_type={},
    )


def test_build_perception_qa_llm_plus_regex_when_flag_on() -> None:
    q = build_perception_qa_debug(_settings(perception_llm=True))
    assert q.evidence_path == "llm_perception_plus_regex_evidence"
    assert q.query_perception_regex is False


def test_build_perception_qa_echoes_query_regex_hint() -> None:
    q = build_perception_qa_debug(_settings(perception_llm=False), query_perception_regex=True)
    assert q.evidence_path == "regex_evidence_only"
    assert q.query_perception_regex is True


def test_build_perception_qa_echoes_include_execution_graph_hint() -> None:
    q = build_perception_qa_debug(_settings(perception_llm=False), query_include_execution_graph=True)
    assert q.query_include_execution_graph is True


def test_build_perception_qa_effective_overrides_env() -> None:
    q = build_perception_qa_debug(_settings(perception_llm=False), perception_llm_effective=True)
    assert q.evidence_path == "llm_perception_plus_regex_evidence"


def test_build_perception_qa_echoes_master_plan_debug() -> None:
    q = build_perception_qa_debug(
        _settings(perception_llm=False),
        perception_llm_effective=True,
        query_master_plan_debug=True,
    )
    assert q.query_master_plan_debug is True


def test_build_perception_qa_echoes_max_decisions_query() -> None:
    q = build_perception_qa_debug(
        _settings(perception_llm=False),
        query_max_decisions=2,
        max_decisions_cap_applied=2,
        decisions_prioritized_full_count=5,
    )
    assert q.query_max_decisions == 2
    assert q.max_decisions_cap_applied == 2
    assert q.decisions_prioritized_full_count == 5


def test_build_perception_qa_echoes_persist_decisions_query() -> None:
    q = build_perception_qa_debug(_settings(perception_llm=False), query_persist_decisions=True)
    assert q.query_persist_decisions is True
