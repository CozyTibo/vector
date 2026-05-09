"""Deterministic execution-story reconstruction from GitHub timeline raw exhaust."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.canonical.github_timeline_mutation_extract import extract_github_timeline_mutations
from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
from vector.domains.cortex.canonical.transform_routing_registry import transform_routing_table
from vector.domains.cortex.canonical.transform_runtime import _build_lineage_specs


def _raw(
    rid: int,
    *,
    connector: str,
    resource_type: str,
    payload_body: dict,
    external_id: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=rid,
        connector=connector,
        resource_type=resource_type,
        payload_body=payload_body,
        external_id=external_id,
    )


def _github_timeline_event_sequence(
    rows: list[SimpleNamespace],
    *,
    temporal_key_by_id: dict[int, str],
) -> list[str]:
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=temporal_key_by_id)
    by_id = {int(r.id): r for r in rows}
    out: list[str] = []
    for rid in topo["ordered_raw_record_ids"]:
        r = by_id[int(rid)]
        if r.resource_type != "github.pull_request_timeline_event":
            continue
        te = r.payload_body.get("timeline_event") if isinstance(r.payload_body.get("timeline_event"), dict) else {}
        ev = te.get("event")
        if isinstance(ev, str) and ev.strip():
            out.append(ev.strip())
    return out


def test_routing_registry_maps_github_timelines_to_timeline_mutation() -> None:
    table = transform_routing_table()
    assert ("github", "github.issue_timeline_event") in table
    assert ("github", "github.pull_request_timeline_event") in table
    assert table[("github", "github.issue_timeline_event")][0] == CanonicalObjectKind.TIMELINE_MUTATION
    assert table[("github", "github.pull_request_timeline_event")][0] == CanonicalObjectKind.TIMELINE_MUTATION


def test_pr_timeline_mutation_materialization_surfaces_execution_mutations() -> None:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        id=4242,
        connector="github",
        resource_type="github.pull_request_timeline_event",
        external_id="acme/widget#1:timeline_event:9",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "id": 9,
            "repository_full_name": "acme/widget",
            "pull_request_external_ref": "acme/widget#1",
            "pull_request_number": 1,
            "github_pull_request_id": 100,
            "timeline_event": {
                "id": 9,
                "event": "head_ref_force_pushed",
                "created_at": "2024-06-01T12:00:00Z",
                "before": "a" * 40,
                "after": "b" * 40,
                "ref": "refs/heads/feature",
            },
        },
    )
    lk, emitted, specs = _build_lineage_specs(
        raw=raw,
        bundle_id="bundle.timeline.test",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.TIMELINE_MUTATION,
        rule_base="rule.registry.github.github.pull_request_timeline_event",
    )
    assert lk["target_object_ref"] == "github.pull_request:100"
    assert lk["mutation_revision"] == "gh_timeline_event:9"
    assert emitted.get("github_timeline_event_type") == "head_ref_force_pushed"
    muts = emitted.get("execution_mutations") or []
    kinds = sorted(m["mutation_kind"] for m in muts)
    assert kinds == ["branch_lineage_mutation", "commit_lineage_mutation"]
    assert any(s.field_path == "attributes.execution_mutations" for s in specs)


def test_execution_story_order_from_pr_timeline_exhaust() -> None:
    """Replay order over timeline rows follows deterministic temporal keys once parents are satisfied."""
    fn = "nexora/demo"
    pr_ext = f"{fn}#3"
    pr_id = 8000
    story_events = [
        "review_requested",
        "ready_for_review",
        "head_ref_force_pushed",
        "synchronize",
        "reviewed",
        "merged",
    ]
    rows: list[SimpleNamespace] = [
        _raw(
            1,
            connector="github",
            resource_type="github.pull_request",
            payload_body={"pull_request": {"id": pr_id, "number": 3}},
        ),
    ]
    tmap: dict[int, str] = {1: "00001"}
    base = 100
    for idx, ev in enumerate(story_events):
        te_id = base + idx
        rid = 10 + idx
        body: dict = {
            "id": te_id,
            "repository_full_name": fn,
            "pull_request_external_ref": pr_ext,
            "pull_request_number": 3,
            "github_pull_request_id": pr_id,
            "timeline_event": {
                "id": te_id,
                "event": ev,
                "created_at": f"2024-01-{10 + idx:02d}T10:00:00Z",
            },
        }
        if ev == "review_requested":
            body["timeline_event"]["review_requester"] = {"id": 1, "login": "bot"}
            body["timeline_event"]["requested_reviewer"] = {"id": 2, "login": "rev"}
        if ev == "reviewed":
            body["timeline_event"]["review"] = {"id": 50, "state": "APPROVED", "user": {"id": 2, "login": "rev"}}
        if ev == "merged":
            body["timeline_event"]["merge_commit_sha"] = "deadbeef"
        if ev == "head_ref_force_pushed":
            body["timeline_event"]["before"] = "a" * 40
            body["timeline_event"]["after"] = "b" * 40
            body["timeline_event"]["ref"] = "refs/heads/feature"
        rows.append(
            _raw(
                rid,
                connector="github",
                resource_type="github.pull_request_timeline_event",
                external_id=f"{pr_ext}:timeline_event:{te_id}",
                payload_body=body,
            )
        )
        tmap[rid] = f"{rid:05d}"
    assert _github_timeline_event_sequence(rows, temporal_key_by_id=tmap) == story_events

    # Each timeline row yields deterministic mutation kinds (empty for synchronize / unknown families).
    for r in rows[1:]:
        muts = extract_github_timeline_mutations(r.payload_body)
        ev = r.payload_body["timeline_event"]["event"]
        if ev == "review_requested":
            assert muts[0]["mutation_kind"] == "reviewer_assignment_mutation"
        elif ev == "ready_for_review":
            assert muts[0]["mutation_kind"] == "pull_request_state_mutation"
        elif ev == "head_ref_force_pushed":
            assert {m["mutation_kind"] for m in muts} >= {"commit_lineage_mutation", "branch_lineage_mutation"}
        elif ev == "synchronize":
            assert muts == []
        elif ev == "reviewed":
            assert muts[0]["mutation_kind"] == "review_state_mutation"
        elif ev == "merged":
            assert muts[0]["mutation_kind"] == "merge_state_mutation"
