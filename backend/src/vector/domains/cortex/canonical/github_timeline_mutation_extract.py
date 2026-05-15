"""Deterministic execution-mutation extraction from GitHub issue/PR timeline payloads.

Maps only explicit fields present on the provider timeline event object (no inference).
"""

from __future__ import annotations

from typing import Any


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _actor_fields(actor: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(actor, dict):
        return out
    aid = actor.get("id")
    if aid is not None:
        out["github_actor_id"] = aid
    login = actor.get("login")
    if isinstance(login, str) and login.strip():
        out["github_actor_login"] = login.strip()
    return out


def _user_target_fields(user: Any, *, prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(user, dict):
        return out
    uid = user.get("id")
    if uid is not None:
        out[f"{prefix}_github_user_id"] = uid
    login = user.get("login")
    if isinstance(login, str) and login.strip():
        out[f"{prefix}_github_login"] = login.strip()
    return out


def _team_target_fields(team: Any, *, prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(team, dict):
        return out
    tid = team.get("id")
    if tid is not None:
        out[f"{prefix}_github_team_id"] = tid
    slug = team.get("slug")
    if isinstance(slug, str) and slug.strip():
        out[f"{prefix}_github_team_slug"] = slug.strip()
    return out


def _pr_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    pr_id = payload.get("github_pull_request_id")
    if pr_id is not None:
        out["github_pull_request_id"] = pr_id
    pre = payload.get("pull_request_external_ref")
    if isinstance(pre, str) and pre.strip():
        out["pull_request_external_ref"] = pre.strip()
    prn = payload.get("pull_request_number")
    if isinstance(prn, int):
        out["pull_request_number"] = prn
    return out


def _issue_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    iid = payload.get("github_issue_id")
    if iid is not None:
        out["github_issue_id"] = iid
    inum = payload.get("issue_number")
    if isinstance(inum, int):
        out["issue_number"] = inum
    return out


def _repo_fn(payload: dict[str, Any]) -> str | None:
    fn = payload.get("repository_full_name")
    if isinstance(fn, str) and fn.strip():
        return fn.strip()
    return None


def extract_github_timeline_mutations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a deterministically ordered list of mutation dicts derived from explicit timeline fields."""
    te = payload.get("timeline_event")
    if not isinstance(te, dict):
        return []
    event = te.get("event")
    if not isinstance(event, str) or not event.strip():
        return []
    ev = event.strip()
    repo_fn = _repo_fn(payload)
    created_at = te.get("created_at")
    created_s = created_at if isinstance(created_at, str) and created_at.strip() else None
    te_id = te.get("id")
    if te_id is None:
        te_id = payload.get("id")

    base_ctx: dict[str, Any] = {}
    if repo_fn is not None:
        base_ctx["repository_full_name"] = repo_fn
    base_ctx.update(_pr_envelope(payload))
    base_ctx.update(_issue_envelope(payload))
    if created_s is not None:
        base_ctx["github_timeline_created_at"] = created_s
    if te_id is not None:
        base_ctx["github_timeline_event_id"] = te_id
    base_ctx.update(_actor_fields(te.get("actor")))

    out: list[dict[str, Any]] = []

    def _append(mutation_kind: str, ordinal: int, fields: dict[str, Any]) -> None:
        row: dict[str, Any] = {"mutation_kind": mutation_kind, "mutation_ordinal": ordinal}
        for k in sorted(fields.keys()):
            v = fields[k]
            if v is not None:
                row[k] = v
        out.append(row)

    ordinal = 0

    if ev == "review_requested":
        rr = te.get("review_requester")
        req_u = te.get("requested_reviewer")
        req_t = te.get("requested_team")
        common = dict(base_ctx)
        if isinstance(rr, dict):
            rrid = rr.get("id")
            if rrid is not None:
                common["review_requester_github_user_id"] = rrid
            rr_login = rr.get("login")
            if isinstance(rr_login, str) and rr_login.strip():
                common["review_requester_github_login"] = rr_login.strip()
        if isinstance(req_u, dict):
            fld = dict(common)
            fld.update(_user_target_fields(req_u, prefix="target"))
            _append("reviewer_assignment_mutation", ordinal, fld)
            ordinal += 1
        if isinstance(req_t, dict):
            fld = dict(common)
            fld.update(_team_target_fields(req_t, prefix="target"))
            _append("reviewer_assignment_mutation", ordinal, fld)
            ordinal += 1
    elif ev == "review_request_removed":
        rr = te.get("review_requester")
        req_u = te.get("requested_reviewer")
        req_t = te.get("requested_team")
        common = dict(base_ctx)
        if isinstance(rr, dict):
            rrid = rr.get("id")
            if rrid is not None:
                common["review_requester_github_user_id"] = rrid
            rr_login = rr.get("login")
            if isinstance(rr_login, str) and rr_login.strip():
                common["review_requester_github_login"] = rr_login.strip()
        if isinstance(req_u, dict):
            fld = dict(common)
            fld.update(_user_target_fields(req_u, prefix="target"))
            _append("reviewer_removal_mutation", ordinal, fld)
            ordinal += 1
        if isinstance(req_t, dict):
            fld = dict(common)
            fld.update(_team_target_fields(req_t, prefix="target"))
            _append("reviewer_removal_mutation", ordinal, fld)
            ordinal += 1
    elif ev == "reviewed":
        rev = _as_dict(te.get("review"))
        fld = dict(base_ctx)
        rid = rev.get("id")
        if rid is not None:
            fld["github_pull_request_review_id"] = rid
        st = rev.get("state")
        if isinstance(st, str) and st.strip():
            fld["github_review_state"] = st.strip()
        fld.update(_user_target_fields(rev.get("user"), prefix="review_author"))
        cid = te.get("commit_id")
        if isinstance(cid, str) and cid.strip():
            fld["commit_sha"] = cid.strip()
        _append("review_state_mutation", ordinal, fld)
        ordinal += 1
    elif ev == "review_dismissed":
        dr = _as_dict(te.get("dismissed_review"))
        fld = dict(base_ctx)
        rid = dr.get("review_id")
        if rid is not None:
            fld["github_pull_request_review_id"] = rid
        dm = dr.get("dismissal_message")
        if isinstance(dm, str) and dm.strip():
            fld["dismissal_message"] = dm.strip()
        dcid = dr.get("dismissal_commit_id")
        if isinstance(dcid, str) and dcid.strip():
            fld["dismissal_commit_sha"] = dcid.strip()
        st = dr.get("state")
        if isinstance(st, str) and st.strip():
            fld["dismissed_review_state"] = st.strip()
        _append("review_dismissal_mutation", ordinal, fld)
        ordinal += 1
    elif ev in {"converted_to_draft", "ready_for_review", "closed", "reopened"}:
        fld = dict(base_ctx)
        fld["github_pull_request_event"] = ev
        _append("pull_request_state_mutation", ordinal, fld)
        ordinal += 1
    elif ev == "merged":
        fld = dict(base_ctx)
        fld["github_pull_request_event"] = ev
        msha = te.get("merge_commit_sha")
        cid = te.get("commit_id")
        merge_sha: str | None = None
        if isinstance(msha, str) and msha.strip():
            merge_sha = msha.strip()
        elif isinstance(cid, str) and cid.strip():
            merge_sha = cid.strip()
        if merge_sha is not None:
            fld["merge_commit_sha"] = merge_sha
        mm = te.get("merge_method")
        if isinstance(mm, str) and mm.strip():
            fld["merge_method"] = mm.strip()
        _append("merge_state_mutation", ordinal, fld)
        ordinal += 1
    elif ev in {"auto_merge_enabled", "auto_merge_disabled"}:
        fld = dict(base_ctx)
        fld["github_auto_merge_event"] = ev
        _append("auto_merge_state_mutation", ordinal, fld)
        ordinal += 1
    elif ev == "head_ref_force_pushed":
        fld = dict(base_ctx)
        before = te.get("before")
        if isinstance(before, str) and before.strip():
            fld["before_commit_sha"] = before.strip()
        after_sha = te.get("after")
        if isinstance(after_sha, str) and after_sha.strip():
            fld["after_commit_sha"] = after_sha.strip()
        cid = te.get("commit_id")
        if isinstance(cid, str) and cid.strip():
            fld["commit_sha"] = cid.strip()
        ref = te.get("ref")
        if isinstance(ref, str) and ref.strip():
            fld["git_ref"] = ref.strip()
        if any(k in fld for k in ("before_commit_sha", "after_commit_sha", "commit_sha")):
            _append("commit_lineage_mutation", ordinal, fld)
            ordinal += 1
        br_fld = dict(base_ctx)
        for k in ("git_ref", "before_commit_sha", "after_commit_sha"):
            if k in fld:
                br_fld[k] = fld[k]
        if len(br_fld) > len(base_ctx):
            _append("branch_lineage_mutation", ordinal, br_fld)
            ordinal += 1
    elif ev == "base_ref_changed":
        fld = dict(base_ctx)
        for key in ("base_ref", "base_ref_before", "base_ref_after"):
            v = te.get(key)
            if isinstance(v, str) and v.strip():
                fld[key] = v.strip()
        if fld.keys() & {"base_ref", "base_ref_before", "base_ref_after"}:
            _append("branch_lineage_mutation", ordinal, fld)
            ordinal += 1
    elif ev in {"assigned", "unassigned"}:
        assignee = te.get("assignee")
        if isinstance(assignee, dict):
            fld = dict(base_ctx)
            fld.update(_user_target_fields(assignee, prefix="assignee"))
            kind = "ownership_mutation"
            fld["github_assignment_event"] = ev
            _append(kind, ordinal, fld)
            ordinal += 1
    elif ev in {"labeled", "unlabeled", "milestoned", "demilestoned", "locked", "unlocked", "pinned", "unpinned"}:
        # No mutation family in charter; skip (stored as timeline with empty execution_mutations).
        pass

    # CI / delivery linkage — only explicit nested objects with stable ids
    wf = _as_dict(te.get("workflow_run"))
    wf_id = wf.get("id")
    if wf_id is not None:
        fld = dict(base_ctx)
        fld["github_workflow_run_id"] = wf_id
        _append("execution_link_mutation", ordinal, fld)
        ordinal += 1
    cr = _as_dict(te.get("check_run"))
    cr_id = cr.get("id")
    if cr_id is not None:
        fld = dict(base_ctx)
        fld["github_check_run_id"] = cr_id
        suite = _as_dict(cr.get("check_suite"))
        sid = suite.get("id")
        if sid is not None:
            fld["github_check_suite_id"] = sid
        head_sha = cr.get("head_sha")
        fn = base_ctx.get("repository_full_name")
        if isinstance(fn, str) and fn.strip() and isinstance(head_sha, str) and head_sha.strip():
            fld["github_check_run_external_ref"] = f"{fn.strip()}:{head_sha.strip()}:check:{cr_id}"
        _append("execution_link_mutation", ordinal, fld)
        ordinal += 1
    dep = _as_dict(te.get("deployment"))
    dep_id = dep.get("id")
    if dep_id is not None:
        fld = dict(base_ctx)
        fld["github_deployment_id"] = dep_id
        _append("deployment_link_mutation", ordinal, fld)
        ordinal += 1

    out.sort(key=lambda m: (str(m.get("mutation_kind", "")), int(m.get("mutation_ordinal", 0)), str(m.get("github_timeline_event_id", ""))))
    return out


def github_timeline_target_object_ref(payload: dict[str, Any]) -> str:
    """Stable target ref string aligned with replay_topology node keys."""
    pid = payload.get("github_pull_request_id")
    if pid is not None:
        return f"github.pull_request:{pid}"
    iid = payload.get("github_issue_id")
    if iid is not None:
        return f"github.issue:{iid}"
    return "github.timeline:unknown"


def github_timeline_mutation_revision(payload: dict[str, Any], timeline_event: dict[str, Any]) -> str:
    te_id = timeline_event.get("id")
    if te_id is None:
        te_id = payload.get("id")
    if te_id is None:
        te_id = "unknown"
    return f"gh_timeline_event:{te_id}"
