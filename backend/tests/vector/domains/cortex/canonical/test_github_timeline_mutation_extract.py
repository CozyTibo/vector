"""Unit tests for deterministic GitHub timeline → execution_mutations extraction."""

from __future__ import annotations

from vector.domains.cortex.canonical.github_timeline_mutation_extract import (
    extract_github_timeline_mutations,
    github_timeline_mutation_revision,
    github_timeline_target_object_ref,
)


def _payload(**kwargs: object) -> dict:
    base = {
        "repository_full_name": "acme/widget",
        "github_pull_request_id": 9001,
        "pull_request_external_ref": "acme/widget#7",
        "pull_request_number": 7,
        "id": 5001,
    }
    base.update(kwargs)
    return base


def test_review_requested_emits_one_assignment_per_requested_reviewer() -> None:
    te = {
        "id": 5001,
        "event": "review_requested",
        "created_at": "2024-01-02T00:00:00Z",
        "actor": {"id": 1, "login": "alice"},
        "review_requester": {"id": 2, "login": "bob"},
        "requested_reviewer": {"id": 99, "login": "dana"},
    }
    rows = extract_github_timeline_mutations(_payload(timeline_event=te))
    assert len(rows) == 1
    assert rows[0]["mutation_kind"] == "reviewer_assignment_mutation"
    assert rows[0]["target_github_user_id"] == 99
    assert rows[0]["github_actor_login"] == "alice"


def test_review_dismissed_emits_dismissal_with_review_id_and_message() -> None:
    te = {
        "id": 5002,
        "event": "review_dismissed",
        "created_at": "2024-01-03T00:00:00Z",
        "actor": {"id": 1, "login": "alice"},
        "dismissed_review": {
            "review_id": 77,
            "dismissal_message": "not needed",
            "state": "CHANGES_REQUESTED",
        },
    }
    rows = extract_github_timeline_mutations(_payload(timeline_event=te))
    assert len(rows) == 1
    assert rows[0]["mutation_kind"] == "review_dismissal_mutation"
    assert rows[0]["github_pull_request_review_id"] == 77
    assert rows[0]["dismissal_message"] == "not needed"


def test_head_ref_force_pushed_emits_commit_and_branch_lineage() -> None:
    te = {
        "id": 5003,
        "event": "head_ref_force_pushed",
        "created_at": "2024-01-04T00:00:00Z",
        "before": "aaa",
        "after": "bbb",
        "ref": "refs/heads/feature",
    }
    rows = extract_github_timeline_mutations(_payload(timeline_event=te))
    kinds = sorted(m["mutation_kind"] for m in rows)
    assert kinds == ["branch_lineage_mutation", "commit_lineage_mutation"]


def test_execution_and_deployment_link_only_when_nested_objects_present() -> None:
    te = {
        "id": 5004,
        "event": "labeled",
        "created_at": "2024-01-05T00:00:00Z",
        "label": {"name": "x"},
    }
    assert extract_github_timeline_mutations(_payload(timeline_event=te)) == []
    te2 = {
        "id": 5005,
        "event": "deployed",
        "created_at": "2024-01-06T00:00:00Z",
        "deployment": {"id": 424242},
    }
    rows = extract_github_timeline_mutations(_payload(timeline_event=te2))
    assert [m["mutation_kind"] for m in rows] == ["deployment_link_mutation"]
    assert rows[0]["github_deployment_id"] == 424242


def test_github_timeline_target_and_revision_strings() -> None:
    p = _payload(timeline_event={"id": 9, "event": "merged"})
    assert github_timeline_target_object_ref(p) == "github.pull_request:9001"
    assert github_timeline_mutation_revision(p, {"id": 9}) == "gh_timeline_event:9"
