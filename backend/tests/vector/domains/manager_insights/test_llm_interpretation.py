"""Optional LLM interpretation layer on deterministic coordination decisions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from vector.contracts.manager_insights_activity import (
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    DecisionRuleTraceDebug,
    GapBundle,
    GapItem,
)
from vector.domains.manager_insights.compute_decisions import compute_decisions
from vector.domains.manager_insights.llm_interpretation import (
    _finalize_llm_interpretation_output,
    _interpretation_payload,
    interpret_decision_with_llm,
)


@pytest.fixture(autouse=True)
def _db_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")


def _bundle_row(*, dtype: str = "MAKE_BLOCKERS_EXPLICIT") -> DecisionBundleItem:
    rid = uuid.uuid4()
    d = DecisionItem(
        id="coordination:decision:x",
        gap_id="coordination:decision:x",
        gap_type="aggregated_situation",
        decision_type=dtype,  # type: ignore[arg-type]
        title="Title",
        rationale="Rationale text.",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={"failure_mode": "OWNERSHIP_FAILURE"},
        evidence_refs=[],
        signal_refs=["urgent_pressure"],
        dominant=True,
        created_at=datetime.now(UTC),
        run_id=rid,
        status=None,
    )
    dbg = DecisionRuleTraceDebug(
        gap_id=d.gap_id,
        matched_rule="execution_situation:INVISIBLE_BLOCKERS",
        execution_situation="INVISIBLE_BLOCKERS",
    )
    return DecisionBundleItem(decision=d, decision_debug=dbg)


def test_llm_interpretation_optional_fields_present() -> None:
    row = _bundle_row()
    assert row.llm_headline is None
    assert row.llm_explanation is None
    assert row.llm_next_step is None
    row2 = row.model_copy(update={"llm_headline": "h", "llm_explanation": "e", "llm_next_step": "n"})
    assert row2.llm_headline == "h"
    assert row2.llm_explanation == "e"
    assert row2.llm_next_step == "n"


def test_llm_interpretation_flag_off_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("VECTOR_MANAGER_INSIGHTS_LLM_INTERPRETATION", raising=False)
    out = interpret_decision_with_llm(_bundle_row())
    assert out["llm_headline"] is None
    assert out["llm_explanation"] is None
    assert out["llm_next_step"] is None


def test_llm_interpretation_safe_on_empty_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("VECTOR_MANAGER_INSIGHTS_LLM_INTERPRETATION", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    out = interpret_decision_with_llm(
        DecisionBundleItem(
            decision=DecisionItem(
                id="i",
                gap_id="i",
                gap_type="aggregated_situation",
                decision_type="ASSIGN_OWNER",  # type: ignore[arg-type]
                title="t",
                rationale="r",
                default_action=DecisionDefaultAction(kind="noop"),
                required_inputs={},
                evidence_refs=[],
                signal_refs=[],
                dominant=False,
                created_at=datetime.now(UTC),
                run_id=uuid.uuid4(),
                status=None,
            ),
            decision_debug=None,
        ),
    )
    assert out["llm_headline"] is None
    assert out["llm_explanation"] is None
    assert out["llm_next_step"] is None


def test_interpretation_payload_includes_causal_structure() -> None:
    item = _bundle_row()
    payload = _interpretation_payload(item)
    assert payload["dominant_failure"] == "OWNERSHIP_FAILURE"
    assert payload["supporting_failures"] == []
    assert isinstance(payload["signals"], list)
    assert payload["situation"] == "INVISIBLE_BLOCKERS"
    assert payload["is_dominant"] is True
    assert "decision_type" in payload and "title" in payload


def test_finalize_trims_headline_and_rejects_banned_wording() -> None:
    long_headline = " ".join([f"w{i}" for i in range(20)])
    ok = _finalize_llm_interpretation_output(
        {
            "llm_headline": long_headline,
            "llm_explanation": "Reviews sit idle on the hot path. That delays merge and slips the release cut.",
            "llm_next_step": "Name one DRI and post the blocker list in the team channel before noon.",
        },
        artifact_labels=None,
    )
    assert ok is not None
    assert len(ok["llm_headline"].split()) == 14

    labeled = _finalize_llm_interpretation_output(
        {
            "llm_headline": "Assign owner to PR #9 — no owner assigned",
            "llm_explanation": "PR #9 carries login work. Without an owner merges stall behind other hotfixes.",
            "llm_next_step": "Assign owner to PR #9 and lock scope before the nightly deploy window.",
        },
        artifact_labels=["PR #9"],
    )
    assert labeled is not None

    rejected = _finalize_llm_interpretation_output(
        {
            "llm_headline": "Ownership drift stalls delivery",
            "llm_explanation": "Work is split across tools. Teams lose a single place to commit.",
            "llm_next_step": "Address various gaps in tracking.",
        },
        artifact_labels=None,
    )
    assert rejected is None

    no_artifact = _finalize_llm_interpretation_output(
        {
            "llm_headline": "Ship faster with better process",
            "llm_explanation": "PR #9 is blocked. Teams lose merge slots waiting on reviews.",
            "llm_next_step": "Escalate reviews today.",
        },
        artifact_labels=["PR #9"],
    )
    assert no_artifact is None


def test_llm_interpretation_does_not_modify_decision_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    gaps = GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[GapItem(id="g1", type="blocker_not_tracked", description="b", evidence_pointers={})],
    )
    monkeypatch.delenv("VECTOR_MANAGER_INSIGHTS_LLM_INTERPRETATION", raising=False)
    baseline = [it.decision.decision_type for it in compute_decisions(gaps, include_decision_debug=False).items]

    monkeypatch.setenv("VECTOR_MANAGER_INSIGHTS_LLM_INTERPRETATION", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setattr(
        "vector.domains.manager_insights.llm_interpretation._call_openai_interpretation",
        lambda settings, user_json: {
            "llm_headline": "Short headline here NEX-1",
            "llm_explanation": "NEX-1 is the anchor issue. It blocks downstream work until ownership is explicit.",
            "llm_next_step": "Schedule a thirty-minute ownership sync on NEX-1 with the DRIs.",
        },
    )
    enriched = compute_decisions(gaps, include_decision_debug=False)
    assert [it.decision.decision_type for it in enriched.items] == baseline
    assert all(it.llm_headline is not None for it in enriched.items)
