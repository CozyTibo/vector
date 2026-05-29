"""Linear issue_relation type → graph relationship kind (deterministic)."""

from __future__ import annotations

# Linear IssueRelation.type values we materialize as typed execution edges.
# Edge direction: issue (left) → relatedIssue (right), matching provider row semantics
# (source blocks target — see mock_connectors/fixtures/execution_stories.py).
_LINEAR_TYPED_KINDS: dict[str, str] = {
    "blocks": "blocks",
    "duplicate": "duplicates",
}


def relationship_kind_for_linear_relation(relation_type: object) -> tuple[str, str]:
    """Return (relationship_kind, extractor_rule) for a Linear issue relation."""
    if relation_type is None:
        return "relates_to", "linear.issue_relation.related"
    norm = str(relation_type).strip().lower()
    kind = _LINEAR_TYPED_KINDS.get(norm)
    if kind is not None:
        return kind, f"linear.issue_relation.{kind}"
    return "relates_to", "linear.issue_relation.related"
