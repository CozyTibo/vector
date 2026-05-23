"""D2 GitHub ingest cap ECS helpers — stdlib only (safe for deploy CI without SQLAlchemy)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

# Must match ``Settings`` Field defaults in settings.py (10 / 16 / 120).
GITHUB_CAP_CODE_DEFAULTS_V1: dict[str, int] = {
    "cortex_github_prs_max_pages_per_repo": 10,
    "cortex_github_pr_fetch_max_repos": 16,
    "cortex_github_repo_time_budget_seconds": 120,
}

GITHUB_CAP_ENV_KEYS_V1: dict[str, str] = {
    "cortex_github_prs_max_pages_per_repo": "CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO",
    "cortex_github_pr_fetch_max_repos": "CORTEX_GITHUB_PR_FETCH_MAX_REPOS",
    "cortex_github_repo_time_budget_seconds": "CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS",
}

GITHUB_CAP_LEGACY_LOW_VALUES_V1: dict[str, int] = {
    "CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO": 5,
    "CORTEX_GITHUB_PR_FETCH_MAX_REPOS": 8,
    "CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS": 25,
}


def github_cap_ecs_environment_entries_v1() -> list[dict[str, str]]:
    return [
        {"name": GITHUB_CAP_ENV_KEYS_V1[field], "value": str(GITHUB_CAP_CODE_DEFAULTS_V1[field])}
        for field in GITHUB_CAP_CODE_DEFAULTS_V1
    ]


def merge_github_caps_into_ecs_task_definition_v1(task_def: dict[str, Any]) -> dict[str, Any]:
    """Upsert Fix-6 trio env vars on container[0] to code defaults (removes stale lows)."""
    out = deepcopy(task_def)
    containers = list(out.get("containerDefinitions") or [])
    if not containers:
        return out
    container = dict(containers[0])
    env_list = list(container.get("environment") or [])
    by_name: dict[str, dict[str, str]] = {}
    for row in env_list:
        if isinstance(row, dict) and row.get("name"):
            by_name[str(row["name"])] = {"name": str(row["name"]), "value": str(row.get("value", ""))}
    for entry in github_cap_ecs_environment_entries_v1():
        by_name[entry["name"]] = entry
    container["environment"] = sorted(by_name.values(), key=lambda r: r["name"])
    containers[0] = container
    out["containerDefinitions"] = containers
    return out


def extract_github_cap_env_from_ecs_task_definition_v1(
    task_def: dict[str, Any],
) -> dict[str, int | None]:
    containers = task_def.get("containerDefinitions") or []
    if not containers:
        return {key: None for key in GITHUB_CAP_ENV_KEYS_V1.values()}
    env_list = containers[0].get("environment") or []
    by_name = {
        str(row.get("name")): str(row.get("value"))
        for row in env_list
        if isinstance(row, dict) and row.get("name")
    }
    out: dict[str, int | None] = {}
    for field in GITHUB_CAP_CODE_DEFAULTS_V1:
        env_key = GITHUB_CAP_ENV_KEYS_V1[field]
        raw = by_name.get(env_key)
        if raw is None or raw == "":
            out[env_key] = None
            continue
        try:
            out[env_key] = int(raw)
        except ValueError:
            out[env_key] = None
    return out


def evaluate_ecs_env_matches_code_defaults_v1(
    env_values: dict[str, int | None],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    all_match = True
    has_legacy_low = False
    for field, expected in GITHUB_CAP_CODE_DEFAULTS_V1.items():
        env_key = GITHUB_CAP_ENV_KEYS_V1[field]
        value = env_values.get(env_key)
        legacy = GITHUB_CAP_LEGACY_LOW_VALUES_V1.get(env_key)
        match = value is not None and int(value) == int(expected)
        is_legacy = value is not None and legacy is not None and int(value) == int(legacy)
        if is_legacy:
            has_legacy_low = True
        if not match:
            all_match = False
        rows[env_key] = {
            "value": value,
            "expected": expected,
            "legacy_low": legacy,
            "matches_code_default": match,
            "is_legacy_low_override": is_legacy,
        }
    return {
        "matches_code_defaults": all_match,
        "has_legacy_low_override": has_legacy_low,
        "env_rows": rows,
    }


def load_ecs_task_definition_json_v1(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_infra_ecs_task_json_github_caps_v1(
    *,
    repo_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    for rel in ("infra/ecs/backend-task.json", "infra/ecs/worker-task.json"):
        p = repo_root / rel
        if not p.is_file():
            errors.append(f"missing_{rel.replace('/', '_')}")
            continue
        task_def = load_ecs_task_definition_json_v1(p)
        ev = extract_github_cap_env_from_ecs_task_definition_v1(task_def)
        verdict = evaluate_ecs_env_matches_code_defaults_v1(ev)
        if not verdict["matches_code_defaults"]:
            errors.append(f"{rel}_caps_not_code_defaults")
    return {"ok": not errors, "errors": errors}
