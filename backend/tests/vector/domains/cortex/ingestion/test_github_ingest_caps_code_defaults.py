"""D2 — GitHub ingest cap code defaults and ECS merge helper."""

from __future__ import annotations

import json
from pathlib import Path

from vector.domains.cortex.ingestion.github_ingest_caps_code_defaults import (
    GITHUB_CAP_CODE_DEFAULTS_V1,
    evaluate_ecs_env_matches_code_defaults_v1,
    merge_github_caps_into_ecs_task_definition_v1,
    settings_defaults_match_code_v1,
    verify_infra_ecs_task_json_github_caps_v1,
)

REPO_ROOT = Path(__file__).resolve().parents[6]


def test_settings_defaults_match_manifest() -> None:
    assert settings_defaults_match_code_v1()["ok"] is True


def test_merge_ecs_task_definition_sets_code_defaults() -> None:
    task_def = {
        "containerDefinitions": [
            {
                "name": "backend",
                "environment": [
                    {"name": "ENV", "value": "production"},
                    {"name": "CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO", "value": "5"},
                ],
            }
        ]
    }
    merged = merge_github_caps_into_ecs_task_definition_v1(task_def)
    env = {row["name"]: row["value"] for row in merged["containerDefinitions"][0]["environment"]}
    assert int(env["CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO"]) == 10
    assert int(env["CORTEX_GITHUB_PR_FETCH_MAX_REPOS"]) == 16
    assert int(env["CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS"]) == 120


def test_evaluate_legacy_low_detected() -> None:
    verdict = evaluate_ecs_env_matches_code_defaults_v1(
        {
            "CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO": 5,
            "CORTEX_GITHUB_PR_FETCH_MAX_REPOS": 8,
            "CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS": 25,
        }
    )
    assert verdict["matches_code_defaults"] is False
    assert verdict["has_legacy_low_override"] is True


def test_infra_ecs_json_aligned() -> None:
    assert verify_infra_ecs_task_json_github_caps_v1(repo_root=REPO_ROOT)["ok"] is True


def test_code_defaults_manifest_matches_settings_fields() -> None:
    for field, value in GITHUB_CAP_CODE_DEFAULTS_V1.items():
        from vector.settings import Settings

        assert int(Settings.model_fields[field].default) == value
