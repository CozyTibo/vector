"""Phase D2 — GitHub ingest cap code defaults (source of truth for prod ECS env)."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.ingestion.github_ingest_caps_ecs import (
    GITHUB_CAP_CODE_DEFAULTS_V1,
    GITHUB_CAP_ENV_KEYS_V1,
    GITHUB_CAP_LEGACY_LOW_VALUES_V1,
    evaluate_ecs_env_matches_code_defaults_v1,
    extract_github_cap_env_from_ecs_task_definition_v1,
    github_cap_ecs_environment_entries_v1,
    load_ecs_task_definition_json_v1,
    merge_github_caps_into_ecs_task_definition_v1,
    verify_infra_ecs_task_json_github_caps_v1,
)

__all__ = [
    "GITHUB_CAP_CODE_DEFAULTS_V1",
    "GITHUB_CAP_ENV_KEYS_V1",
    "GITHUB_CAP_LEGACY_LOW_VALUES_V1",
    "evaluate_ecs_env_matches_code_defaults_v1",
    "extract_github_cap_env_from_ecs_task_definition_v1",
    "github_cap_ecs_environment_entries_v1",
    "load_ecs_task_definition_json_v1",
    "merge_github_caps_into_ecs_task_definition_v1",
    "settings_defaults_match_code_v1",
    "verify_infra_ecs_task_json_github_caps_v1",
]


def settings_defaults_match_code_v1() -> dict[str, Any]:
    """Verify pydantic Field defaults match D2 code-default manifest."""
    from vector.settings import Settings

    mismatches: list[str] = []
    for field, expected in GITHUB_CAP_CODE_DEFAULTS_V1.items():
        default = Settings.model_fields[field].default
        if int(default) != int(expected):
            mismatches.append(f"{field}:model_default={default}:expected={expected}")
    return {"ok": not mismatches, "mismatches": mismatches}
