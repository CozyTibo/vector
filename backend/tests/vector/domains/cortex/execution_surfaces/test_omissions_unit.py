"""Unit tests for execution surface omission helpers."""

from vector.domains.cortex.execution_surfaces.omissions import (
    EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE,
    OBSERVATION_ACTIVITY_FOOTNOTE,
    section,
    with_items,
)


def test_section_empty_includes_omission() -> None:
    payload = section(
        count=0,
        empty_code="no_graph_relationships",
        empty_message="No graph relationships found.",
        empty_remediation="Run graph pass.",
    )
    assert payload["count"] == 0
    assert payload["omission"]["code"] == "no_graph_relationships"
    assert payload["omission"]["remediation"] == "Run graph pass."


def test_with_items_clears_omission_when_nonempty() -> None:
    base = section(
        count=0,
        empty_code="empty",
        empty_message="Empty",
        empty_remediation=None,
    )
    out = with_items(base, [{"id": "1"}])
    assert out["count"] == 1
    assert out["omission"] is None


def test_footnotes_non_empty() -> None:
    assert "observation" in OBSERVATION_ACTIVITY_FOOTNOTE.lower()
    assert "not yet" in EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE.lower()
