"""Requested vs granted connector permissions for admin diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from vector.settings import Settings

PermissionModel = Literal[
    "oauth_scopes",
    "github_app",
    "notion_integration",
    "oauth_scope_single",
    "google_oauth",
]
IngestHealth = Literal["ok", "warn", "unknown", "not_connected"]


def parse_comma_scopes(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    return sorted({p.strip() for p in str(raw).split(",") if p.strip()})


# Scopes required for Cortex Slack organizational exhaust (conversations.list + history).
SLACK_RECOMMENDED_INGEST_SCOPES: frozenset[str] = frozenset(
    {
        "channels:read",
        "channels:history",
        "groups:history",
        "users:read",
        "users:read.email",
    }
)

SLACK_OPTIONAL_INGEST_SCOPES: frozenset[str] = frozenset(
    {
        "channels:join",
        "im:history",
        "mpim:history",
        "usergroups:read",
        "pins:read",
    }
)


@dataclass(frozen=True)
class ConnectionPermissionSnapshot:
    permission_model: PermissionModel
    requested: list[str]
    granted: list[str] | None
    recommended_for_ingestion: list[str] | None
    missing_requested: list[str]
    missing_recommended: list[str]
    extra_granted: list[str]
    ingest_health: IngestHealth
    notes: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "permission_model": self.permission_model,
            "requested": self.requested,
            "granted": self.granted,
            "recommended_for_ingestion": self.recommended_for_ingestion,
            "missing_requested": self.missing_requested,
            "missing_recommended": self.missing_recommended,
            "extra_granted": self.extra_granted,
            "ingest_health": self.ingest_health,
            "notes": self.notes,
        }


def _scope_diff(
    *,
    requested: set[str],
    granted: set[str] | None,
    recommended: set[str] | frozenset[str] | None,
) -> tuple[list[str], list[str], list[str], IngestHealth, str | None]:
    if granted is None:
        return [], [], [], "unknown", None
    missing_requested = sorted(requested - granted)
    rec = set(recommended) if recommended is not None else set()
    missing_recommended = sorted(rec - granted)
    extra_granted = sorted(granted - requested) if requested else sorted(granted)
    if missing_recommended:
        health: IngestHealth = "warn"
        note = (
            "Granted scopes are missing capabilities needed for full Slack message ingest "
            "(conversations.history). Re-connect after updating SLACK_BOT_SCOPES and the Slack app."
        )
    elif missing_requested:
        health = "warn"
        note = (
            "User approved fewer scopes than this deployment requests. "
            "Re-run connect and approve all listed scopes."
        )
    else:
        health = "ok"
        note = None
    return missing_requested, missing_recommended, extra_granted, health, note


def slack_permission_snapshot(
    settings: Settings,
    *,
    granted_scope: str | None,
    connected: bool,
    requested_scopes_override: str | None = None,
) -> ConnectionPermissionSnapshot:
    requested_raw = (
        requested_scopes_override
        if requested_scopes_override is not None
        else (
            settings.slack_bot_scopes.strip()
            or "channels:read,chat:write,users:read,users:read.email"
        )
    )
    requested = parse_comma_scopes(requested_raw)
    granted_list = parse_comma_scopes(granted_scope)
    granted_set = set(granted_list) if connected else None
    recommended = sorted(SLACK_RECOMMENDED_INGEST_SCOPES)
    missing_requested, missing_recommended, extra_granted, health, note = _scope_diff(
        requested=set(requested),
        granted=granted_set,
        recommended=SLACK_RECOMMENDED_INGEST_SCOPES,
    )
    if not connected:
        health = "not_connected"
        note = None
    return ConnectionPermissionSnapshot(
        permission_model="oauth_scopes",
        requested=requested,
        granted=granted_list if connected else None,
        recommended_for_ingestion=recommended,
        missing_requested=missing_requested,
        missing_recommended=missing_recommended,
        extra_granted=extra_granted,
        ingest_health=health,
        notes=note,
    )


def linear_permission_snapshot(*, connected: bool) -> ConnectionPermissionSnapshot:
    requested = ["read"]
    granted = requested if connected else None
    missing_requested, missing_recommended, extra_granted, health, note = _scope_diff(
        requested=set(requested),
        granted=set(granted) if granted else None,
        recommended=set(requested),
    )
    if not connected:
        health = "not_connected"
    return ConnectionPermissionSnapshot(
        permission_model="oauth_scope_single",
        requested=requested,
        granted=granted,
        recommended_for_ingestion=requested,
        missing_requested=missing_requested,
        missing_recommended=missing_recommended,
        extra_granted=extra_granted,
        ingest_health=health,
        notes=note,
    )


def calls_permission_snapshot(*, connected: bool) -> ConnectionPermissionSnapshot:
    requested = parse_comma_scopes(
        "openid email profile https://www.googleapis.com/auth/calendar.readonly",
    )
    granted = requested if connected else None
    missing_requested, missing_recommended, extra_granted, health, note = _scope_diff(
        requested=set(requested),
        granted=set(granted) if granted else None,
        recommended=set(requested),
    )
    if not connected:
        health = "not_connected"
    return ConnectionPermissionSnapshot(
        permission_model="google_oauth",
        requested=requested,
        granted=granted,
        recommended_for_ingestion=requested,
        missing_requested=missing_requested,
        missing_recommended=missing_recommended,
        extra_granted=extra_granted,
        ingest_health=health,
        notes=note,
    )


def notion_permission_snapshot(*, connected: bool) -> ConnectionPermissionSnapshot:
    requested = [
        "integration (pages/databases selected during Notion OAuth)",
    ]
    return ConnectionPermissionSnapshot(
        permission_model="notion_integration",
        requested=requested,
        granted=["connected"] if connected else None,
        recommended_for_ingestion=requested,
        missing_requested=[],
        missing_recommended=[],
        extra_granted=[],
        ingest_health="ok" if connected else "not_connected",
        notes=(
            "Notion does not return a machine-readable scope list on connect. "
            "Verify shared pages/databases in the Notion integration settings."
            if connected
            else None
        ),
    )


def github_permission_snapshot_from_installation(
    installation: dict[str, Any] | None,
    *,
    connected: bool,
    app_slug: str,
) -> ConnectionPermissionSnapshot:
    if not connected:
        return ConnectionPermissionSnapshot(
            permission_model="github_app",
            requested=[f"GitHub App “{app_slug}” manifest permissions"],
            granted=None,
            recommended_for_ingestion=None,
            missing_requested=[],
            missing_recommended=[],
            extra_granted=[],
            ingest_health="not_connected",
            notes=None,
        )

    perms = installation.get("permissions") if isinstance(installation, dict) else None
    repo_sel = installation.get("repository_selection") if isinstance(installation, dict) else None
    granted_lines: list[str] = []
    if isinstance(perms, dict):
        for kind in ("contents", "metadata", "pull_requests", "issues", "actions", "deployments"):
            level = perms.get(kind)
            if isinstance(level, str) and level.strip():
                granted_lines.append(f"{kind}:{level.strip()}")
        for key, level in sorted(perms.items()):
            if key in ("contents", "metadata", "pull_requests", "issues", "actions", "deployments"):
                continue
            if isinstance(level, str) and level.strip():
                granted_lines.append(f"{key}:{level.strip()}")
    if isinstance(repo_sel, str) and repo_sel.strip():
        granted_lines.insert(0, f"repository_selection:{repo_sel.strip()}")

    return ConnectionPermissionSnapshot(
        permission_model="github_app",
        requested=[f"GitHub App “{app_slug}” manifest permissions"],
        granted=granted_lines or None,
        recommended_for_ingestion=["contents:read", "metadata:read", "pull_requests:read"],
        missing_requested=[],
        missing_recommended=[],
        extra_granted=[],
        ingest_health="ok" if granted_lines else "unknown",
        notes=(
            "Installation permissions from GitHub API (live). "
            "Compare with your App registration if ingest is incomplete."
            if granted_lines
            else "Could not read installation permissions from GitHub."
        ),
    )
