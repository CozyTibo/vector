"""End-to-end deterministic reconstruction scenarios (raw exhaust → topology + mutations)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from vector.domains.cortex.canonical.github_timeline_mutation_extract import extract_github_timeline_mutations
from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
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


def _timeline_payload(
    *,
    fn: str,
    pr_ext: str,
    pr_num: int,
    pr_gid: int,
    te_id: int,
    timeline_event: dict,
) -> dict:
    return {
        "id": te_id,
        "repository_full_name": fn,
        "pull_request_external_ref": pr_ext,
        "pull_request_number": pr_num,
        "github_pull_request_id": pr_gid,
        "timeline_event": timeline_event,
        "provider_event_timestamp": timeline_event.get("created_at"),
    }


def _materialize_mutations(payload: dict) -> list[dict]:
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        id=1,
        connector="github",
        resource_type="github.pull_request_timeline_event",
        external_id="x",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body=payload,
    )
    lk, emitted, _ = _build_lineage_specs(
        raw=raw,
        bundle_id="bundle.scenario",
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.TIMELINE_MUTATION,
        rule_base="rule.registry.github.github.pull_request_timeline_event",
    )
    assert lk["target_object_ref"] == f"github.pull_request:{payload['github_pull_request_id']}"
    return list(emitted.get("execution_mutations") or [])


def test_scenario_review_dismissal_after_review_then_merge_chain() -> None:
    """Review lifecycle + merge: topology orders PR → review → reviewed → dismissed → merged."""
    fn = "o/r"
    pr_ext = f"{fn}#1"
    pr_gid = 100
    rows = [
        _raw(1, connector="github", resource_type="github.pull_request", payload_body={"pull_request": {"id": pr_gid, "number": 1}}),
        _raw(
            2,
            connector="github",
            resource_type="github.pull_request_review",
            external_id=f"{pr_ext}:review:77",
            payload_body={"github_pull_request_id": pr_gid, "review": {"id": 77}},
        ),
        _raw(
            10,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:timeline:10",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=1,
                pr_gid=pr_gid,
                te_id=10,
                timeline_event={
                    "id": 10,
                    "event": "reviewed",
                    "created_at": "2024-01-01T00:00:00Z",
                    "review": {"id": 77, "state": "COMMENTED", "user": {"id": 5, "login": "r1"}},
                },
            ),
        ),
        _raw(
            11,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:timeline:11",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=1,
                pr_gid=pr_gid,
                te_id=11,
                timeline_event={
                    "id": 11,
                    "event": "review_dismissed",
                    "created_at": "2024-01-02T00:00:00Z",
                    "actor": {"id": 1, "login": "lead"},
                    "dismissed_review": {"review_id": 77, "dismissal_message": "obsolete", "state": "COMMENTED"},
                },
            ),
        ),
        _raw(
            12,
            connector="github",
            resource_type="github.commit",
            external_id=f"{fn}:merge_sha",
            payload_body={"commit": {"sha": "merge_sha"}},
        ),
        _raw(
            13,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:timeline:13",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=1,
                pr_gid=pr_gid,
                te_id=13,
                timeline_event={
                    "id": 13,
                    "event": "merged",
                    "created_at": "2024-01-04T00:00:00Z",
                    "merge_commit_sha": "merge_sha",
                    "merge_method": "squash",
                },
            ),
        ),
    ]
    tmap = {1: "0001", 2: "0002", 10: "0010", 11: "0011", 12: "0003", 13: "0999"}
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=tmap)
    assert topo["orphan_refs"] == []
    order = topo["ordered_raw_record_ids"]
    # DAG guarantees: PR and review before reviewed/dismissed; merge commit before merged timeline; no merge→review edge in API.
    assert order.index(1) < order.index(2) < order.index(10) < order.index(11)
    assert order.index(1) < order.index(13) and order.index(12) < order.index(13)

    m_reviewed = extract_github_timeline_mutations(rows[2].payload_body)
    assert m_reviewed[0]["mutation_kind"] == "review_state_mutation"
    m_dismiss = extract_github_timeline_mutations(rows[3].payload_body)
    assert m_dismiss[0]["mutation_kind"] == "review_dismissal_mutation"
    m_merge = _materialize_mutations(rows[5].payload_body)
    assert m_merge[0]["mutation_kind"] == "merge_state_mutation"
    assert m_merge[0]["merge_commit_sha"] == "merge_sha"


def test_scenario_draft_ready_checks_deployment_explicit_refs() -> None:
    fn = "o/r"
    pr_ext = f"{fn}#2"
    pr_gid = 200
    wf_id = 9999
    dep_id = 8888
    rows = [
        _raw(1, connector="github", resource_type="github.pull_request", payload_body={"pull_request": {"id": pr_gid, "number": 2}}),
        _raw(
            20,
            connector="github",
            resource_type="github.workflow_run",
            payload_body={"workflow_run": {"id": wf_id}},
        ),
        _raw(
            21,
            connector="github",
            resource_type="github.deployment",
            external_id=f"{fn}:deployment:{dep_id}",
            payload_body={"deployment": {"id": dep_id}},
        ),
        _raw(
            30,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t30",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=2,
                pr_gid=pr_gid,
                te_id=30,
                timeline_event={
                    "id": 30,
                    "event": "converted_to_draft",
                    "created_at": "2024-02-01T00:00:00Z",
                },
            ),
        ),
        _raw(
            31,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t31",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=2,
                pr_gid=pr_gid,
                te_id=31,
                timeline_event={
                    "id": 31,
                    "event": "ready_for_review",
                    "created_at": "2024-02-02T00:00:00Z",
                },
            ),
        ),
        _raw(
            32,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t32",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=2,
                pr_gid=pr_gid,
                te_id=32,
                timeline_event={
                    "id": 32,
                    "event": "head_ref_force_pushed",
                    "created_at": "2024-02-03T00:00:00Z",
                    "workflow_run": {"id": wf_id},
                    "before": "000",
                    "after": "111",
                },
            ),
        ),
        _raw(
            33,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t33",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=2,
                pr_gid=pr_gid,
                te_id=33,
                timeline_event={
                    "id": 33,
                    "event": "labeled",
                    "created_at": "2024-02-04T00:00:00Z",
                    "label": {"name": "x"},
                    "deployment": {"id": dep_id},
                },
            ),
        ),
    ]
    tmap = {i: f"{i:04d}" for i in [1, 20, 21, 30, 31, 32, 33]}
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=tmap)
    assert topo["orphan_refs"] == []
    # PR (1) then workflow (20), deployment (21), then timeline rows depending on PR / wf / deployment / commits
    assert topo["ordered_raw_record_ids"][0] == 1
    assert 20 in topo["ordered_raw_record_ids"][:3]
    assert 21 in topo["ordered_raw_record_ids"][:4]

    m32 = extract_github_timeline_mutations(rows[5].payload_body)
    kinds_32 = sorted(m["mutation_kind"] for m in m32)
    assert "commit_lineage_mutation" in kinds_32
    assert "branch_lineage_mutation" in kinds_32
    assert any(m.get("github_workflow_run_id") == wf_id for m in m32)
    m33 = extract_github_timeline_mutations(rows[6].payload_body)
    assert any(m["mutation_kind"] == "deployment_link_mutation" and m["github_deployment_id"] == dep_id for m in m33)


def test_scenario_review_reassignment_chain_ordering() -> None:
    fn = "o/r"
    pr_ext = f"{fn}#3"
    pr_gid = 300
    rows = [
        _raw(1, connector="github", resource_type="github.pull_request", payload_body={"pull_request": {"id": pr_gid, "number": 3}}),
        _raw(
            40,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t40",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=3,
                pr_gid=pr_gid,
                te_id=40,
                timeline_event={
                    "id": 40,
                    "event": "review_requested",
                    "created_at": "2024-03-01T00:00:00Z",
                    "review_requester": {"id": 1, "login": "a"},
                    "requested_reviewer": {"id": 10, "login": "u10"},
                },
            ),
        ),
        _raw(
            41,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t41",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=3,
                pr_gid=pr_gid,
                te_id=41,
                timeline_event={
                    "id": 41,
                    "event": "review_request_removed",
                    "created_at": "2024-03-02T00:00:00Z",
                    "review_requester": {"id": 1, "login": "a"},
                    "requested_reviewer": {"id": 10, "login": "u10"},
                },
            ),
        ),
        _raw(
            42,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:t42",
            payload_body=_timeline_payload(
                fn=fn,
                pr_ext=pr_ext,
                pr_num=3,
                pr_gid=pr_gid,
                te_id=42,
                timeline_event={
                    "id": 42,
                    "event": "review_requested",
                    "created_at": "2024-03-03T00:00:00Z",
                    "review_requester": {"id": 1, "login": "a"},
                    "requested_reviewer": {"id": 11, "login": "u11"},
                },
            ),
        ),
    ]
    tmap = {i: f"{i:04d}" for i in [1, 40, 41, 42]}
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=tmap)
    assert topo["ordered_raw_record_ids"] == [1, 40, 41, 42]
    kinds = [extract_github_timeline_mutations(rows[i].payload_body)[0]["mutation_kind"] for i in [1, 2, 3]]
    assert kinds == ["reviewer_assignment_mutation", "reviewer_removal_mutation", "reviewer_assignment_mutation"]
