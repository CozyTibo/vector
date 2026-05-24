"""Phase S3.2 — org_link cap and conditional skip tests."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_materialization_caps_v1 import (
    DEFAULT_MAX_ORG_LINK_ENTRIES_PER_EPOCH_V1,
    EXECUTION_MIX_SKIP_ORG_LINK_RATIO_V1,
    get_retrieval_max_org_link_entries_per_epoch_v1,
    retrieval_skip_org_link_when_execution_mix_met_enabled_v1,
)


def test_default_org_link_cap_is_100(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_RETRIEVAL_MAX_ORG_LINK_ENTRIES_PER_EPOCH", raising=False)
    assert DEFAULT_MAX_ORG_LINK_ENTRIES_PER_EPOCH_V1 == 100
    assert get_retrieval_max_org_link_entries_per_epoch_v1() == 100


def test_org_link_skip_enabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_RETRIEVAL_SKIP_ORG_LINK_WHEN_EXECUTION_MIX_MET", raising=False)
    assert retrieval_skip_org_link_when_execution_mix_met_enabled_v1() is True


def test_org_link_skip_disabled_via_env(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_RETRIEVAL_SKIP_ORG_LINK_WHEN_EXECUTION_MIX_MET", "0")
    assert retrieval_skip_org_link_when_execution_mix_met_enabled_v1() is False


def test_execution_mix_skip_threshold_matches_gate() -> None:
    assert EXECUTION_MIX_SKIP_ORG_LINK_RATIO_V1 == 0.60


def test_should_skip_org_link_when_execution_ratio_met(monkeypatch) -> None:
    from vector.domains.cortex.retrieval import retrieval_materialization_caps_v1 as caps

    monkeypatch.setattr(
        caps,
        "count_epoch_index_entries_by_kind_v1",
        lambda session, *, tenant_id, index_epoch: {
            "total": 100,
            "execution": 65,
            "org_link": 0,
            "by_kind": {"materialization": 65, "walk": 0},
        },
    )
    skip, meta = caps.should_skip_org_link_materialization_v1(
        None,  # type: ignore[arg-type]
        tenant_id=__import__("uuid").uuid4(),
        index_epoch="epoch-test",
    )
    assert skip is True
    assert meta.get("skip_org_link") is True
