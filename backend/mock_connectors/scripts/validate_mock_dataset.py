#!/usr/bin/env python3
"""Validate deterministic mock dataset invariants (strategy §16)."""

from __future__ import annotations

import json
import os
import sys
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
    seed = int(os.environ.get("VECTOR_MOCK_SEED", "42"))
    out_json = _BACKEND / "mock_connectors" / "fixtures" / "generated" / "dataset.json"
    if out_json.exists():
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
    # Build adjacency for blocks
    blocks: dict[str, str] = {}
    for rel in linear.get("issueRelations", []):
        if rel.get("type") == "blocks":
            blocks[rel["source"]] = rel["target"]
    for src, tgt in blocks.items():
        if tgt in blocks and blocks[tgt] == src:
            warnings.append(f"mutual blocks? {src} <-> {tgt}")
    return warnings


def main() -> int:
    data = _load_or_generate()
    gh = data["github"]
    linear = data["linear"]

    errs: list[str] = []
    errs.extend(_check_repos(gh))
    errs.extend(_check_commits(gh))
    errs.extend(_check_chrono(linear))

    # Scale soft checks
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
