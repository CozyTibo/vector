"""Replay topology DAG/orphan detection tests."""

from __future__ import annotations

from types import SimpleNamespace

from vector.domains.cortex.canonical.replay_topology import (
    build_node_key_index,
    build_replay_dependency_topology,
)


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


def test_replay_topology_parent_before_child_and_no_cycle() -> None:
    rows = [
        _raw(
            1,
            connector="github",
            resource_type="github.workflow_run",
            payload_body={"workflow_run": {"id": 42}},
        ),
        _raw(
            2,
            connector="github",
            resource_type="github.check_run",
            payload_body={"check_run": {"id": 9, "check_suite": {"id": 42}}},
        ),
    ]
    topo = build_replay_dependency_topology(rows, temporal_key_by_id={1: "0001", 2: "0002"})
    assert topo["ordered_raw_record_ids"] == [1, 2]
    assert topo["cycle_detected"] is False
    assert topo["orphan_refs"] == []


def test_build_node_key_index_github_deployment() -> None:
    rows = [
        _raw(
            1,
            connector="github",
            resource_type="github.deployment",
            payload_body={"deployment": {"id": 999}},
        ),
    ]
    assert build_node_key_index(rows) == {"github.deployment:999": 1}  # type: ignore[arg-type]


def test_replay_topology_orphan_detection() -> None:
    rows = [
        _raw(
            10,
            connector="github",
            resource_type="github.deployment_status",
            payload_body={"deployment_id": 999, "state": "success"},
        ),
    ]
    topo = build_replay_dependency_topology(rows, temporal_key_by_id={10: "0010"})
    assert topo["cycle_detected"] is False
    assert len(topo["orphan_refs"]) == 1
    assert "github.deployment:999" in topo["orphan_refs"][0]["missing_parent_ref"]


def test_github_pr_timeline_replay_order_respects_pr_commit_review_then_timeline() -> None:
    """Execution substrate: timeline rows depend on PR, commit, and review refs present in the payload."""
    fn = "acme/widget"
    pr_ext = f"{fn}#42"
    rows = [
        _raw(
            1,
            connector="github",
            resource_type="github.pull_request",
            payload_body={"pull_request": {"id": 9001, "number": 42}},
        ),
        _raw(
            2,
            connector="github",
            resource_type="github.commit",
            external_id=f"{fn}:abc123def",
            payload_body={"commit": {"sha": "abc123def"}},
        ),
        _raw(
            3,
            connector="github",
            resource_type="github.pull_request_review",
            external_id=f"{pr_ext}:review:77",
            payload_body={"github_pull_request_id": 9001, "review": {"id": 77}},
        ),
        _raw(
            4,
            connector="github",
            resource_type="github.pull_request_timeline_event",
            external_id=f"{pr_ext}:timeline_event:501",
            payload_body={
                "id": 501,
                "repository_full_name": fn,
                "pull_request_external_ref": pr_ext,
                "pull_request_number": 42,
                "github_pull_request_id": 9001,
                "timeline_event": {
                    "id": 501,
                    "event": "reviewed",
                    "created_at": "2020-01-04T00:00:00Z",
                    "commit_id": "abc123def",
                    "review": {"id": 77},
                },
            },
        ),
    ]
    tmap = {1: "0001", 2: "0002", 3: "0003", 4: "0004"}
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=tmap)
    assert topo["orphan_refs"] == []
    assert topo["cycle_detected"] is False
    assert topo["ordered_raw_record_ids"] == [1, 2, 3, 4]


def test_github_issue_timeline_parent_is_issue() -> None:
    fn = "acme/widget"
    rows = [
        _raw(
            10,
            connector="github",
            resource_type="github.issue",
            payload_body={"issue": {"id": 555, "number": 9}},
        ),
        _raw(
            11,
            connector="github",
            resource_type="github.issue_timeline_event",
            external_id=f"{fn}:issue:555:timeline_event:901",
            payload_body={
                "id": 901,
                "repository_full_name": fn,
                "issue_number": 9,
                "github_issue_id": 555,
                "timeline_event": {"id": 901, "event": "labeled", "created_at": "2020-02-01T00:00:00Z"},
            },
        ),
    ]
    topo = build_replay_dependency_topology(rows, temporal_key_by_id={10: "0010", 11: "0011"})
    assert topo["orphan_refs"] == []
    assert topo["ordered_raw_record_ids"] == [10, 11]


def test_slack_thread_container_orders_root_then_thread_then_reply() -> None:
    cid = "C0123"
    root_ts = "1.0"
    rows = [
        _raw(
            1,
            connector="slack",
            resource_type="slack.message",
            external_id=f"{cid}:{root_ts}",
            payload_body={
                "channel_id": cid,
                "message": {"ts": root_ts, "thread_ts": root_ts, "reply_count": 2},
            },
        ),
        _raw(
            2,
            connector="slack",
            resource_type="slack.thread",
            external_id=f"{cid}:{root_ts}",
            payload_body={"channel": cid, "thread_ts": root_ts, "root_message_ts": root_ts},
        ),
        _raw(
            3,
            connector="slack",
            resource_type="slack.message_reply",
            external_id=f"{cid}:{root_ts}:1.1",
            payload_body={
                "channel_id": cid,
                "thread_ts": root_ts,
                "reply": {"ts": "1.1"},
            },
        ),
    ]
    tmap = {1: "a", 2: "b", 3: "c"}
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=tmap)
    assert topo["orphan_refs"] == []
    assert topo["ordered_raw_record_ids"] == [1, 2, 3]


def test_linear_issue_centered_subgraph_orders_parents_before_children() -> None:
    issue_id = "lin_issue_1"
    proj_id = "lin_proj_9"
    rows = [
        _raw(
            1,
            connector="linear",
            resource_type="linear.project",
            external_id=proj_id,
            payload_body={"project": {"id": proj_id, "name": "Infra"}},
        ),
        _raw(
            2,
            connector="linear",
            resource_type="linear.issue",
            external_id=issue_id,
            payload_body={"issue": {"id": issue_id, "identifier": "INF-1", "project": {"id": proj_id}}},
        ),
        _raw(
            3,
            connector="linear",
            resource_type="linear.comment",
            external_id="lin_cmt_77",
            payload_body={
                "comment": {
                    "id": "lin_cmt_77",
                    "body": "ship it",
                    "issue": {"id": issue_id},
                }
            },
        ),
        _raw(
            4,
            connector="linear",
            resource_type="linear.activity_history",
            external_id=f"{issue_id}:activity:0",
            payload_body={"issue_id": issue_id, "event": {"id": "act0", "type": "updated"}},
        ),
    ]
    tmap = {1: "p1", 2: "p2", 3: "p3", 4: "p4"}
    topo = build_replay_dependency_topology(rows, temporal_key_by_id=tmap)
    assert topo["orphan_refs"] == []
    assert topo["ordered_raw_record_ids"] == [1, 2, 3, 4]


def test_calls_participant_depends_on_meeting() -> None:
    mid = "evt_calendar_1"
    rows = [
        _raw(1, connector="calls", resource_type="calls.meeting", payload_body={"meeting": {"id": mid}}),
        _raw(
            2,
            connector="calls",
            resource_type="calls.participant",
            external_id=f"{mid}:alice@ex.com",
            payload_body={"participant_record": {"meeting_id": mid, "participant": {"email": "alice@ex.com"}}},
        ),
    ]
    topo = build_replay_dependency_topology(rows, temporal_key_by_id={1: "a", 2: "b"})
    assert topo["orphan_refs"] == []
    assert topo["ordered_raw_record_ids"] == [1, 2]
