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
    }
    seen_issue = {
        (iss.get("metadata") or {}).get("scenario")
        for iss in linear.get("issues", [])
        if isinstance(iss.get("metadata"), dict)
    }
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


def main() -> int:
    data = _load_or_generate()
    gh = data["github"]
    linear = data["linear"]

    errs: list[str] = []
    errs.extend(_check_repos(gh))
    errs.extend(_check_commits(gh))
    errs.extend(_check_chrono(linear))
    errs.extend(_check_execution_stories(linear, gh))

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
