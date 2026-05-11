#!/usr/bin/env python3
"""Validate deterministic mock dataset invariants (strategy §16 + execution stories)."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from mock_connectors.fixtures import cortex_capability_scenarios as ccs  # noqa: E402
from mock_connectors.fixtures import phase04_continuity_fixtures as p4c  # noqa: E402
from mock_connectors.fixtures import seed_config as sc  # noqa: E402
from mock_connectors.fixtures.company_generator import (  # noqa: E402
    dataset_to_json_dict,
    generate_dataset,
)


def _load_or_generate() -> dict[str, Any]:
    """Validate the live generator by default (deterministic).

    Set MOCK_VALIDATE_USE_JSON=1 to read ``fixtures/generated/dataset.json`` instead.
    """
    seed = int(os.environ.get("VECTOR_MOCK_SEED", "42"))
    out_json = _BACKEND / "mock_connectors" / "fixtures" / "generated" / "dataset.json"
    if os.environ.get("MOCK_VALIDATE_USE_JSON") == "1" and out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))
    return dataset_to_json_dict(generate_dataset(seed))


def _check_repos(gh: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    names = {r["full_name"] for r in gh["repos"]}
    for pr in gh["pull_requests"]:
        fn = pr["base"]["repo"]["full_name"]
        if fn not in names:
            errs.append(f"PR {pr.get('number')} refs unknown repo {fn}")
    return errs


def _check_commits(gh: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for c in gh["commits"]:
        if "_repo" not in c:
            errs.append(f"commit {c.get('sha')} missing _repo")
    return errs


def _check_chrono(linear: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for iss in linear["issues"]:
        ca = iss.get("createdAt")
        ua = iss.get("updatedAt")
        if ca and ua and ca > ua:
            errs.append(f"Issue {iss.get('identifier')} createdAt > updatedAt")
    return errs


def _check_loops(linear: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    blocks: dict[str, str] = {}
    for rel in linear.get("issueRelations", []):
        if rel.get("type") != "blocks":
            continue
        src = rel.get("source") or rel.get("issue", {}).get("id")
        tgt = rel.get("target") or rel.get("relatedIssue", {}).get("id")
        if src and tgt:
            blocks[src] = tgt
    for src, tgt in blocks.items():
        if tgt in blocks and blocks[tgt] == src:
            warnings.append(f"mutual blocks? {src} <-> {tgt}")
    return warnings


def _max_blocks_chain(linear: dict[str, Any]) -> int:
    adj: dict[str, list[str]] = defaultdict(list)
    for rel in linear.get("issueRelations", []):
        if rel.get("type") != "blocks":
            continue
        a = rel.get("issue", {}).get("id")
        b = rel.get("relatedIssue", {}).get("id")
        if a and b:
            adj[a].append(b)
    best: list[str] = []

    def dfs(u: str, path: list[str]) -> None:
        nonlocal best
        if len(path) > len(best):
            best = list(path)
        for v in adj[u]:
            if v in path:
                continue
            dfs(v, path + [v])

    for n in list(adj.keys()):
        dfs(n, [n])
    return len(best)


def _em_linear_ids(linear: dict[str, Any]) -> set[str]:
    return {u["id"] for u in linear.get("users", []) if "collins" in u.get("email", "").lower()}


def _check_execution_stories(linear: dict[str, Any], gh: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    required_issue_scenarios = {
        "normal_delivery",
        "review_bottleneck",
        "shadow_work",
        "misaligned_completion",
        "duplicate_work_a",
        "duplicate_work_b",
        "initiative_soc2",
        "initiative_mobile_offline",
        "epic_drift_child",
        "blocked_release",
        "fragmented_execution",
        "healthy_delivery",
    }
    seen_issue: set[str] = set()
    for iss in linear.get("issues", []):
        md = iss.get("metadata")
        if not isinstance(md, dict):
            continue
        for k in ("scenario", "execution_story"):
            v = md.get(k)
            if isinstance(v, str) and v:
                seen_issue.add(v)
    missing = required_issue_scenarios - {x for x in seen_issue if x}
    if missing:
        errs.append(f"missing issue metadata.scenario values: {sorted(missing)}")

    link_styles = Counter(
        (pr.get("metadata") or {}).get("link_style") for pr in gh.get("pull_requests", [])
    )
    for ls in ("title_ref", "body_closes", "issue_field_only", "none"):
        if link_styles.get(ls, 0) < 1:
            errs.append(f"PR link_style {ls!r} has no samples")

    if _max_blocks_chain(linear) < 5:
        errs.append("blocks dependency chain shorter than 5")

    dups = sum(1 for r in linear.get("issueRelations", []) if r.get("type") == "duplicate")
    if dups < 3:
        errs.append(f"expected >=3 duplicate relations, got {dups}")

    em_ids = _em_linear_ids(linear)
    if not em_ids:
        errs.append("no engineering manager user (sara.collins) in linear users")
    else:
        em_comments = sum(
            1
            for c in linear.get("comments", [])
            if c.get("user", {}).get("id") in em_ids
            or "People management" in (c.get("body") or "")
        )
        if em_comments < 5:
            errs.append(f"expected EM participation in comments (>=5), got {em_comments}")

    pr_states = Counter(pr.get("state") for pr in gh.get("pull_requests", []))
    if pr_states.get("open", 0) < 2 or pr_states.get("closed", 0) < 20:
        errs.append(
            f"PR lifecycle distribution weak: open={pr_states.get('open')} "
            f"closed={pr_states.get('closed')}"
        )

    return errs


def _check_phase04_continuity_fixture(data: dict[str, Any], linear: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    cf = data.get("continuity_fixture")
    if not isinstance(cf, dict):
        errs.append("continuity_fixture missing or not an object")
        return errs
    if cf.get("schema_version") != p4c.PHASE04_MOCK_FIXTURE_SCHEMA_VERSION:
        errs.append("continuity_fixture.schema_version must be phase04_mock_fixture_v1")
    sk = cf.get("scenario_key")
    if not isinstance(sk, str) or sk not in p4c.PHASE04_SCENARIO_KEYS:
        errs.append("continuity_fixture.scenario_key must be a registered Phase 04 scenario key")
    users = linear.get("users") if isinstance(linear.get("users"), list) else []
    alex_linear = sum(
        1
        for u in users
        if isinstance(u, dict) and str(u.get("displayName") or "").strip() == "Alex"
    )
    if alex_linear < 2:
        errs.append("Phase04 hostile identity slice expects >=2 Linear users with displayName 'Alex'")
    return errs


def _check_connector_depth(data: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    gh = data.get("github") if isinstance(data.get("github"), dict) else {}
    slack_events = data.get("slack_events") if isinstance(data.get("slack_events"), list) else []
    notion = data.get("notion") if isinstance(data.get("notion"), dict) else {}
    calls = data.get("calls") if isinstance(data.get("calls"), dict) else {}

    if len(gh.get("pull_request_reviews", [])) < 20:
        errs.append("github pull_request_reviews depth too low (<20)")
    if len(gh.get("issue_comments", [])) < 30:
        errs.append("github issue_comments depth too low (<30)")
    repo_n = len(gh.get("repos", [])) if isinstance(gh.get("repos"), list) else 0
    if len(gh.get("releases", [])) < max(repo_n, 1):
        errs.append("github releases depth too low (expected at least one per repo)")

    if not slack_events:
        errs.append("slack_events missing")
    else:
        kinds = Counter(str(ev.get("event_type")) for ev in slack_events if isinstance(ev, dict))
        for required in ("message", "thread_reply", "message_changed", "message_deleted"):
            if kinds.get(required, 0) == 0:
                errs.append(f"slack event_type {required!r} missing")

    databases = notion.get("databases")
    if not isinstance(databases, dict) or len(databases) < 3:
        errs.append("notion databases depth too low (<3)")
    if len(notion.get("database_rows", [])) < 20:
        errs.append("notion database_rows depth too low (<20)")
    if len(notion.get("blocks", [])) < 20:
        errs.append("notion blocks depth too low (<20)")
    if len(notion.get("comments", [])) < 20:
        errs.append("notion comments depth too low (<20)")
    if len(notion.get("relations", [])) < 5:
        errs.append("notion relations depth too low (<5)")

    call_events = calls.get("events", [])
    if not isinstance(call_events, list) or len(call_events) < 15:
        errs.append("calls events depth too low (<15)")
    else:
        transcript_count = sum(
            1
            for ev in call_events
            if isinstance(ev, dict)
            and isinstance(ev.get("transcript"), dict)
            and isinstance(ev.get("transcript", {}).get("segments"), list)
            and len(ev.get("transcript", {}).get("segments", [])) >= 2
        )
        if transcript_count < 10:
            errs.append("calls transcript depth too low (<10 events with 2+ segments)")
    return errs


def main() -> int:
    data = _load_or_generate()
    gh = data["github"]
    linear = data["linear"]

    errs: list[str] = []
    errs.extend(_check_repos(gh))
    errs.extend(_check_commits(gh))
    errs.extend(_check_chrono(linear))
    errs.extend(_check_execution_stories(linear, gh))
    errs.extend(_check_connector_depth(data))
    slack_events = data.get("slack_events") if isinstance(data.get("slack_events"), list) else []
    calls = data.get("calls") if isinstance(data.get("calls"), dict) else {}
    notion = data.get("notion") if isinstance(data.get("notion"), dict) else {}
    errs.extend(
        ccs.validate_cortex_capability_dataset_strength(
            linear, gh, slack_events, calls, notion
        )
    )
    errs.extend(_check_phase04_continuity_fixture(data, linear))

    if len(gh["repos"]) < sc.TARGET_REPOSITORIES // 2:
        errs.append(f"repo count low: {len(gh['repos'])}")
    if len(linear["issues"]) < sc.TARGET_ISSUES // 2:
        errs.append(f"issue count low: {len(linear['issues'])}")

    warns = _check_loops(linear)

    if errs:
        print("ERRORS:")
        for e in errs:
            print(" ", e)
    if warns:
        print("WARNINGS (dependency quirks):")
        for w in warns:
            print(" ", w)
    if not errs:
        print("validate_mock_dataset: OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
