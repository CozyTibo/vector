"""Emit lists of ``NormalizedReference`` from raw payload shapes (provenance-first, deterministic).

These helpers are safe to call from future transform extensions or offline indexers; they do not
mutate canonical tables.
"""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.continuity.reference_normalize import (
    normalize_git_commit_sha,
    normalize_git_repository_full_name,
    normalize_github_deployment_id,
    normalize_github_pull_request_ref,
    normalize_github_workflow_run_id,
    normalize_slack_message_ref,
    normalize_slack_thread_ref,
)


def emit_github_workflow_run_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract repository + run id + optional head_sha from ``payload_body``-shaped dict."""
    out: list[dict[str, Any]] = []
    run = payload.get("workflow_run") if isinstance(payload.get("workflow_run"), dict) else {}
    repo_obj = run.get("repository") if isinstance(run.get("repository"), dict) else {}
    fn = repo_obj.get("full_name")
    if not isinstance(fn, str) or not fn.strip():
        ext = payload.get("source_object_id") if isinstance(payload.get("source_object_id"), str) else ""
        if ":workflow_run:" in ext:
            fn = ext.split(":workflow_run:", 1)[0].strip()
    rid = run.get("id")
    ref_run = normalize_github_workflow_run_id(
        fn if isinstance(fn, str) else None,
        rid,
        source_paths=["payload_body.workflow_run.id", "payload_body.workflow_run.repository.full_name"],
    )
    out.append(ref_run)
    repo_ref = normalize_git_repository_full_name(
        fn if isinstance(fn, str) else None,
        source_paths=["payload_body.workflow_run.repository.full_name"],
    )
    if repo_ref["status"] == "ok":
        out.append(repo_ref)
    head_sha = run.get("head_sha")
    if isinstance(head_sha, str) and head_sha.strip():
        out.append(
            normalize_git_commit_sha(
                head_sha.strip(),
                source_paths=["payload_body.workflow_run.head_sha"],
            )
        )
    return out


def emit_github_pull_request_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}
    repo = pr.get("head", {}).get("repo") if isinstance(pr.get("head"), dict) else {}
    if not isinstance(repo, dict):
        repo = {}
    fn = repo.get("full_name") if isinstance(repo.get("full_name"), str) else None
    num = pr.get("number")
    ref = normalize_github_pull_request_ref(fn, num, source_paths=["payload_body.pull_request"])
    return [ref] if ref["status"] == "ok" else [ref]


def emit_slack_message_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ch = payload.get("channel") or payload.get("channel_id")
    if isinstance(ch, dict):
        ch = ch.get("id")
    ts = payload.get("ts")
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    if not ts and isinstance(msg, dict):
        ts = msg.get("ts")
    ref = normalize_slack_message_ref(
        str(ch) if ch is not None else None,
        str(ts) if ts is not None else None,
        source_paths=["payload_body.channel", "payload_body.ts"],
    )
    out = [ref]
    thread_ts = payload.get("thread_ts") or (msg.get("thread_ts") if isinstance(msg, dict) else None)
    if thread_ts:
        out.append(
            normalize_slack_thread_ref(
                str(ch) if ch is not None else None,
                str(thread_ts),
                source_paths=["payload_body.thread_ts"],
            )
        )
    return out


def emit_github_deployment_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dep = payload.get("deployment") if isinstance(payload.get("deployment"), dict) else {}
    repo = dep.get("repository") if isinstance(dep.get("repository"), dict) else {}
    fn = repo.get("full_name") if isinstance(repo.get("full_name"), str) else None
    did = dep.get("id")
    ref = normalize_github_deployment_id(fn, did, source_paths=["payload_body.deployment"])
    out: list[dict[str, Any]] = [ref]
    sha = dep.get("sha")
    if isinstance(sha, str) and sha.strip():
        out.append(normalize_git_commit_sha(sha.strip(), source_paths=["payload_body.deployment.sha"]))
    return out
