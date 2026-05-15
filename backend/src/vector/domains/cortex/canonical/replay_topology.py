"""Replay dependency topology utilities (resource-type aware deterministic DAG)."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _payload(raw: RawIngestionRecord) -> dict[str, Any]:
    return raw.payload_body if isinstance(raw.payload_body, dict) else {}


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _slack_channel_id(p: dict[str, Any]) -> str | None:
    ch = p.get("channel_id") if isinstance(p.get("channel_id"), str) else p.get("channel")
    if isinstance(ch, str) and ch.strip():
        return ch.strip()
    return None


def _node_key(raw: RawIngestionRecord) -> str | None:
    p = _payload(raw)
    rt = raw.resource_type
    if rt == "github.issue":
        iss = _as_dict(p.get("issue"))
        iid = iss.get("id")
        return f"github.issue:{iid}" if iid is not None else None
    if rt == "github.pull_request":
        pr = _as_dict(p.get("pull_request"))
        pid = pr.get("id")
        return f"github.pull_request:{pid}" if pid is not None else None
    if rt == "github.commit":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"github.commit:{ext.strip()}"
        c = _as_dict(p.get("commit"))
        sha = c.get("sha")
        return f"github.commit:{sha}" if isinstance(sha, str) and sha.strip() else None
    if rt == "github.pull_request_review":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"github.pull_request_review:{ext.strip()}"
        return None
    if rt == "github.issue_timeline_event":
        tid = p.get("id")
        if tid is None:
            te = _as_dict(p.get("timeline_event"))
            tid = te.get("id")
        return f"github.issue_timeline_event:{tid}" if tid is not None else None
    if rt == "github.pull_request_timeline_event":
        tid = p.get("id")
        if tid is None:
            te = _as_dict(p.get("timeline_event"))
            tid = te.get("id")
        return f"github.pull_request_timeline_event:{tid}" if tid is not None else None
    if rt == "github.check_run":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"github.check_run:{ext.strip()}"
        return None
    if rt == "github.workflow_job":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"github.workflow_job:{ext.strip()}"
        return None
    if rt == "github.workflow_job_step":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"github.workflow_job_step:{ext.strip()}"
        return None
    if rt == "github.workflow_run":
        run = _as_dict(p.get("workflow_run"))
        run_id = run.get("id")
        return f"github.workflow_run:{run_id}" if run_id is not None else None
    if rt == "github.deployment":
        dep = _as_dict(p.get("deployment"))
        dep_id = dep.get("id")
        return f"github.deployment:{dep_id}" if dep_id is not None else None
    if rt == "notion.database":
        db = _as_dict(p.get("database"))
        db_id = db.get("id")
        return f"notion.database:{db_id}" if isinstance(db_id, str) and db_id.strip() else None
    if rt == "notion.block":
        block = _as_dict(p.get("block"))
        block_id = block.get("id")
        return f"notion.block:{block_id}" if isinstance(block_id, str) and block_id.strip() else None
    if rt == "calls.meeting":
        meeting = _as_dict(p.get("meeting"))
        meeting_id = meeting.get("id")
        return f"calls.meeting:{meeting_id}" if meeting_id is not None else None
    if rt == "calls.participant":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"calls.participant:{ext.strip()}"
        return None
    if rt == "linear.issue":
        iss = _as_dict(p.get("issue"))
        iid = iss.get("id")
        if isinstance(iid, str) and iid.strip():
            return f"linear.issue:{iid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.issue:{ext.strip()}"
        return None
    if rt == "linear.comment":
        c = _as_dict(p.get("comment"))
        cid = c.get("id")
        if isinstance(cid, str) and cid.strip():
            return f"linear.comment:{cid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.comment:{ext.strip()}"
        return None
    if rt == "linear.issue_attachment":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.issue_attachment:{ext.strip()}"
        return None
    if rt == "linear.activity_history":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.activity_history:{ext.strip()}"
        return None
    if rt == "linear.comment_thread":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.comment_thread:{ext.strip()}"
        return None
    if rt == "linear.issue_relation":
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.issue_relation:{ext.strip()}"
        return None
    if rt == "linear.project":
        proj = _as_dict(p.get("project"))
        pid = proj.get("id")
        if isinstance(pid, str) and pid.strip():
            return f"linear.project:{pid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.project:{ext.strip()}"
        return None
    if rt == "linear.cycle":
        cyc = _as_dict(p.get("cycle"))
        cid = cyc.get("id")
        if isinstance(cid, str) and cid.strip():
            return f"linear.cycle:{cid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.cycle:{ext.strip()}"
        return None
    if rt == "linear.issue_label":
        lab = _as_dict(p.get("issue_label"))
        lid = lab.get("id")
        if isinstance(lid, str) and lid.strip():
            return f"linear.issue_label:{lid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.issue_label:{ext.strip()}"
        return None
    if rt == "linear.initiative":
        ini = _as_dict(p.get("initiative"))
        iid = ini.get("id")
        if isinstance(iid, str) and iid.strip():
            return f"linear.initiative:{iid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.initiative:{ext.strip()}"
        return None
    if rt == "linear.project_update":
        pu = _as_dict(p.get("project_update"))
        uid = pu.get("id")
        if isinstance(uid, str) and uid.strip():
            return f"linear.project_update:{uid.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"linear.project_update:{ext.strip()}"
        return None
    if rt == "slack.thread":
        ch = _slack_channel_id(p)
        tts = p.get("thread_ts")
        if ch and isinstance(tts, str) and tts.strip():
            return f"slack.thread:{ch}:{tts.strip()}"
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            return f"slack.thread:{ext.strip()}"
        return None
    if rt == "slack.message":
        ch = _slack_channel_id(p)
        msg = _as_dict(p.get("message"))
        ts = p.get("ts") or msg.get("ts")
        if ch and isinstance(ts, str) and ts.strip():
            return f"slack.message:{ch}:{ts.strip()}"
        return None
    if rt == "slack.message_reply":
        ch = _slack_channel_id(p)
        rep = _as_dict(p.get("reply"))
        ts = p.get("ts") or rep.get("ts")
        if ch and isinstance(ts, str) and ts.strip():
            return f"slack.message_reply:{ch}:{ts.strip()}"
        return None
    return None


def _github_timeline_event_extra_dependency_keys(p: dict[str, Any], te: dict[str, Any]) -> list[str]:
    """Additional parent refs present on the timeline event object (explicit fields only)."""
    out: list[str] = []
    pre = p.get("pull_request_external_ref")
    pre_s = pre.strip() if isinstance(pre, str) else ""
    dr = _as_dict(te.get("dismissed_review"))
    drid = dr.get("review_id")
    if pre_s and drid is not None:
        out.append(f"github.pull_request_review:{pre_s}:review:{drid}")
    wf = _as_dict(te.get("workflow_run"))
    wf_id = wf.get("id")
    if wf_id is not None:
        out.append(f"github.workflow_run:{wf_id}")
    cr = _as_dict(te.get("check_run"))
    suite = _as_dict(cr.get("check_suite"))
    suite_id = suite.get("id")
    if suite_id is not None:
        out.append(f"github.workflow_run:{suite_id}")
    dep = _as_dict(te.get("deployment"))
    dep_id = dep.get("id")
    if dep_id is not None:
        out.append(f"github.deployment:{dep_id}")
    fn = p.get("repository_full_name")
    fn_s = fn.strip() if isinstance(fn, str) else ""
    ev = te.get("event")
    ev_s = ev.strip() if isinstance(ev, str) else ""
    if ev_s == "merged" and fn_s:
        msha = te.get("merge_commit_sha")
        cid = te.get("commit_id")
        sha: str | None = None
        if isinstance(msha, str) and msha.strip():
            sha = msha.strip()
        elif isinstance(cid, str) and cid.strip():
            sha = cid.strip()
        if sha is not None:
            out.append(f"github.commit:{fn_s}:{sha}")
    cr = _as_dict(te.get("check_run"))
    cr_id = cr.get("id")
    head_sha = cr.get("head_sha")
    if isinstance(fn_s, str) and cr_id is not None and isinstance(head_sha, str) and head_sha.strip():
        cext = f"{fn_s}:{head_sha.strip()}:check:{cr_id}"
        out.append(f"github.check_run:{cext}")
    return out


def _dependency_keys(raw: RawIngestionRecord) -> list[str]:
    p = _payload(raw)
    rt = raw.resource_type
    deps: list[str] = []
    if rt == "github.check_run":
        cr = _as_dict(p.get("check_run"))
        suite = _as_dict(cr.get("check_suite"))
        suite_id = suite.get("id")
        if suite_id is not None:
            deps.append(f"github.workflow_run:{suite_id}")
    elif rt == "github.workflow_job":
        rid = p.get("workflow_run_id")
        if rid is not None:
            fn = p.get("repository_full_name")
            if isinstance(fn, str) and fn.strip():
                deps.append(f"github.workflow_run:{rid}")
    elif rt == "github.workflow_job_step":
        jid = p.get("workflow_job_id")
        rid = p.get("workflow_run_id")
        fn = p.get("repository_full_name")
        if isinstance(fn, str) and fn.strip() and jid is not None and rid is not None:
            job_ext = f"{fn.strip()}:workflow_run:{rid}:job:{jid}"
            deps.append(f"github.workflow_job:{job_ext}")
    elif rt == "github.deployment_status":
        dep_id = p.get("deployment_id")
        if dep_id is not None:
            deps.append(f"github.deployment:{dep_id}")
    elif rt == "slack.thread":
        ch = _slack_channel_id(p)
        thread_ts = p.get("thread_ts")
        if ch and isinstance(thread_ts, str) and thread_ts.strip():
            deps.append(f"slack.message:{ch}:{thread_ts.strip()}")
    elif rt == "slack.message_reply":
        ch = _slack_channel_id(p)
        thread_ts = p.get("thread_ts")
        if ch and isinstance(thread_ts, str) and thread_ts.strip():
            deps.append(f"slack.thread:{ch}:{thread_ts.strip()}")
    elif rt == "slack.file":
        ch = _slack_channel_id(p)
        mts = p.get("message_ts")
        if ch and isinstance(mts, str) and mts.strip():
            deps.append(f"slack.message:{ch}:{mts.strip()}")
    elif rt == "calls.participant":
        pr = _as_dict(p.get("participant_record"))
        mid = pr.get("meeting_id")
        if mid is not None:
            deps.append(f"calls.meeting:{mid}")
    elif rt == "linear.issue_attachment":
        iid = p.get("issue_id")
        if isinstance(iid, str) and iid.strip():
            deps.append(f"linear.issue:{iid.strip()}")
    elif rt == "linear.activity_history":
        iid = p.get("issue_id")
        if isinstance(iid, str) and iid.strip():
            deps.append(f"linear.issue:{iid.strip()}")
    elif rt == "linear.comment":
        c = _as_dict(p.get("comment"))
        iss = _as_dict(c.get("issue"))
        iid = iss.get("id")
        if isinstance(iid, str) and iid.strip():
            deps.append(f"linear.issue:{iid.strip()}")
        parent = _as_dict(c.get("parent"))
        pid = parent.get("id")
        if isinstance(pid, str) and pid.strip():
            deps.append(f"linear.comment:{pid.strip()}")
    elif rt == "linear.comment_thread":
        anchor = _as_dict(p.get("anchor_comment"))
        aid = anchor.get("id")
        if isinstance(aid, str) and aid.strip():
            deps.append(f"linear.comment:{aid.strip()}")
        iss = _as_dict(p.get("issue"))
        iid = iss.get("id")
        if isinstance(iid, str) and iid.strip():
            deps.append(f"linear.issue:{iid.strip()}")
    elif rt == "linear.issue_relation":
        rel = _as_dict(p.get("issue_relation"))
        a = _as_dict(rel.get("issue"))
        b = _as_dict(rel.get("relatedIssue"))
        for node in (a, b):
            iid = node.get("id")
            if isinstance(iid, str) and iid.strip():
                deps.append(f"linear.issue:{iid.strip()}")
    elif rt == "linear.project_update":
        pu = _as_dict(p.get("project_update"))
        proj = _as_dict(pu.get("project"))
        pid = proj.get("id")
        if isinstance(pid, str) and pid.strip():
            deps.append(f"linear.project:{pid.strip()}")
    elif rt == "linear.issue":
        iss = _as_dict(p.get("issue"))
        proj = _as_dict(iss.get("project"))
        prid = proj.get("id")
        if isinstance(prid, str) and prid.strip():
            deps.append(f"linear.project:{prid.strip()}")
        cyc = _as_dict(iss.get("cycle"))
        cid = cyc.get("id")
        if isinstance(cid, str) and cid.strip():
            deps.append(f"linear.cycle:{cid.strip()}")
    elif rt == "notion.database_row":
        row = _as_dict(p.get("row"))
        parent = _as_dict(row.get("parent"))
        db_id = parent.get("database_id") or row.get("database_id")
        if isinstance(db_id, str) and db_id.strip():
            deps.append(f"notion.database:{db_id.strip()}")
    elif rt == "notion.block":
        block = _as_dict(p.get("block"))
        parent = _as_dict(block.get("parent"))
        bid = parent.get("block_id")
        if isinstance(bid, str) and bid.strip():
            deps.append(f"notion.block:{bid.strip()}")
    elif rt == "calls.transcript":
        tr = _as_dict(p.get("transcript_record"))
        meeting_id = tr.get("meeting_id")
        if meeting_id is not None:
            deps.append(f"calls.meeting:{meeting_id}")
    elif rt == "calls.transcript_segment":
        seg = _as_dict(p.get("segment_record"))
        meeting_id = seg.get("meeting_id")
        if meeting_id is not None:
            deps.append(f"calls.meeting:{meeting_id}")
    elif rt == "calls.recording":
        rec = _as_dict(p.get("recording_record"))
        meeting_id = rec.get("meeting_id")
        if meeting_id is not None:
            deps.append(f"calls.meeting:{meeting_id}")
    elif rt == "github.issue_timeline_event":
        iid = p.get("github_issue_id")
        if iid is not None:
            deps.append(f"github.issue:{iid}")
        fn = p.get("repository_full_name")
        te = _as_dict(p.get("timeline_event"))
        if isinstance(fn, str) and fn.strip():
            sha = te.get("commit_id")
            if isinstance(sha, str) and sha.strip():
                cext = f"{fn.strip()}:{sha.strip()}"
                deps.append(f"github.commit:{cext}")
        deps.extend(_github_timeline_event_extra_dependency_keys(p, te))
    elif rt == "github.pull_request_timeline_event":
        pid = p.get("github_pull_request_id")
        if pid is not None:
            deps.append(f"github.pull_request:{pid}")
        fn = p.get("repository_full_name")
        te = _as_dict(p.get("timeline_event"))
        if isinstance(fn, str) and fn.strip():
            sha = te.get("commit_id")
            if isinstance(sha, str) and sha.strip():
                cext = f"{fn.strip()}:{sha.strip()}"
                deps.append(f"github.commit:{cext}")
        pre = p.get("pull_request_external_ref")
        if not isinstance(pre, str) or not pre.strip():
            pr_num = p.get("pull_request_number")
            if isinstance(fn, str) and fn.strip() and isinstance(pr_num, int):
                pre = f"{fn.strip()}#{pr_num}"
        rev = _as_dict(te.get("review"))
        rid = rev.get("id")
        if isinstance(pre, str) and pre.strip() and rid is not None:
            deps.append(f"github.pull_request_review:{pre.strip()}:review:{rid}")
        deps.extend(_github_timeline_event_extra_dependency_keys(p, te))
    elif rt == "github.pull_request_review":
        pid = p.get("github_pull_request_id")
        if pid is not None:
            deps.append(f"github.pull_request:{pid}")
    return list(dict.fromkeys(deps))


def build_replay_dependency_topology(
    rows: list[RawIngestionRecord],
    *,
    temporal_key_by_id: dict[int, str],
) -> dict[str, Any]:
    node_key_to_id: dict[str, int] = {}
    for row in rows:
        nk = _node_key(row)
        if nk:
            node_key_to_id[nk] = int(row.id)

    edges: list[tuple[int, int]] = []
    orphans: list[dict[str, Any]] = []
    for row in rows:
        child_id = int(row.id)
        for dep in _dependency_keys(row):
            parent_id = node_key_to_id.get(dep)
            if parent_id is None:
                orphans.append(
                    {
                        "raw_record_id": child_id,
                        "resource_type": row.resource_type,
                        "missing_parent_ref": dep,
                    }
                )
                continue
            if parent_id != child_id:
                edges.append((parent_id, child_id))

    incoming: dict[int, int] = defaultdict(int)
    outgoing: dict[int, list[int]] = defaultdict(list)
    ids = [int(r.id) for r in rows]
    for pid, cid in edges:
        outgoing[pid].append(cid)
        incoming[cid] += 1
        incoming.setdefault(pid, 0)

    queue = deque(sorted([rid for rid in ids if incoming.get(rid, 0) == 0], key=lambda x: temporal_key_by_id.get(x, "")))
    ordered: list[int] = []
    while queue:
        cur = queue.popleft()
        ordered.append(cur)
        for nxt in sorted(outgoing.get(cur, []), key=lambda x: temporal_key_by_id.get(x, "")):
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(nxt)

    cycle_detected = len(ordered) != len(ids)
    if cycle_detected:
        # Keep deterministic fallback by temporal key for unresolved cycle tail.
        unresolved = [rid for rid in ids if rid not in set(ordered)]
        ordered.extend(sorted(unresolved, key=lambda x: temporal_key_by_id.get(x, "")))

    depth: dict[int, int] = {rid: 0 for rid in ids}
    for rid in ordered:
        for nxt in outgoing.get(rid, []):
            depth[nxt] = max(depth.get(nxt, 0), depth.get(rid, 0) + 1)

    return {
        "ordered_raw_record_ids": ordered,
        "dependency_edges": [{"parent_raw_record_id": p, "child_raw_record_id": c} for p, c in edges],
        "orphan_refs": orphans,
        "cycle_detected": cycle_detected,
        "max_replay_depth": max(depth.values()) if depth else 0,
    }
