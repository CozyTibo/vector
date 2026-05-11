"""Deterministic cross-tool organizational recurrence surface (Phase 04 mock substrate).

Adds bounded, replay-safe evidence density so continuity rules see the same human across
Slack / GitHub / Linear without introducing fuzzy matching or RNG (seed drives ids only).

Normative: continuity evidence != identity truth — these rows are raw observations only.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, Final

_RECURRENCE_SCHEMA: Final[str] = "p04_org_recurrence_topology_v1"


def _u(seed: int, *parts: str) -> str:
    h = hashlib.sha256((f"{seed}:" + ":".join(parts)).encode()).hexdigest()
    b = h[:32]
    return f"{b[:8]}-{b[8:12]}-{b[12:16]}-{b[16:20]}-{b[20:32]}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _user_by_login(users: list[dict[str, Any]], login: str) -> dict[str, Any] | None:
    for u in users:
        if str(u.get("login") or "") == login:
            return u
    return None


def _gh_user_blob(u: dict[str, Any], *, name_override: str | None = None) -> dict[str, Any]:
    raw_name = (u.get("name") or "").strip()
    gh_name: str | None = name_override if name_override is not None else (raw_name if raw_name else None)
    if u.get("github_profile_name_empty") and name_override is None:
        gh_name = None
    return {
        "login": u["login"],
        "id": u["github_id"],
        "type": u["type"],
        "avatar_url": u["avatar_url"],
        "html_url": f"https://github.com/{u['login']}",
        "name": gh_name,
    }


def apply_org_recurrence_cross_tool_surface(
    *,
    seed: int,
    users: list[dict[str, Any]],
    github: dict[str, Any],
    linear: dict[str, Any],
    slack_events: list[dict[str, Any]],
    t0: datetime,
) -> dict[str, Any]:
    """Mutate ``github``, ``linear``, ``slack_events`` in place; return deterministic summary stats."""
    u = _user_by_login(users, "akim")
    if u is None or not u.get("has_github", True):
        return {
            "schema_version": _RECURRENCE_SCHEMA,
            "applied": False,
            "reason": "anchor_user_akim_not_found_or_linear_only",
        }

    repos = github.get("repos") or []
    if not repos:
        return {"schema_version": _RECURRENCE_SCHEMA, "applied": False, "reason": "no_github_repos"}

    repo = repos[0]
    repo_fn = str(repo.get("full_name") or "nexora/api")
    email = str(u.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return {"schema_version": _RECURRENCE_SCHEMA, "applied": False, "reason": "anchor_user_missing_email"}

    workspace_id = None
    for ev in slack_events:
        if isinstance(ev, dict) and isinstance(ev.get("workspace_id"), str) and ev["workspace_id"].strip():
            workspace_id = ev["workspace_id"].strip()
            break
    if workspace_id is None:
        workspace_id = f"T{seed % 10_000:04d}NEXORA"

    channel_id = "CENGCORE01"
    channel = "#eng-core"
    slack_uid = "UAKIM001"
    display_variants = ("Alex", "alex", "A. Kim", "Alex Kim", "Alex (mobile)", "Alex K.")

    base = t0 + timedelta(days=11, hours=4)
    slack_added = 0
    for i, dn in enumerate(display_variants):
        ts = base + timedelta(days=i, hours=i * 3)
        slack_events.append(
            {
                "id": _u(seed, "slack", "p04rec", str(i)),
                "workspace_id": workspace_id,
                "event_type": "message",
                "channel_id": channel_id,
                "channel": channel,
                "thread_ts": None,
                "parent_ts": None,
                "text": f"[P04 recurrence] core execution shard {i} — same Slack id, display drift mock.",
                "ts": _iso(ts),
                "created_at": _iso(ts),
                "updated_at": _iso(ts),
                "deleted_at": None,
                "user_email": email,
                "user_id": slack_uid,
                "display_name": dn,
                "linear_issue_id": None,
                "pattern": "p04_org_recurrence",
                "reactions": [{"name": "white_check_mark", "count": 1}],
                "metadata": {
                    "scenario": "p04_org_recurrence_topology",
                    "source": "org_recurrence_surface",
                    "continuity_fixture": {
                        "cluster_key": f"p04md_org_recurrence_akim_{seed % 10009:05d}",
                        "family": "P04MD-R01",
                    },
                },
            }
        )
        slack_added += 1

    commits = github.setdefault("commits", [])
    commit_em = email
    name_variants = ("Alex Kim", "alex kim", "A Kim", "Alex", "Alexandra Kim")
    commits_added = 0
    for i, nm in enumerate(name_variants):
        c_at = base + timedelta(hours=40 + i * 11)
        sha = hashlib.sha1(f"{seed}:p04rec:commit:{i}".encode()).hexdigest()
        cobj = {
            "sha": sha,
            "commit": {
                "message": f"p04 recurrence commit {i}\n",
                "author": {"name": nm, "email": commit_em, "date": _iso(c_at)},
                "committer": {"name": nm, "email": commit_em, "date": _iso(c_at)},
            },
            "author": _gh_user_blob(u, name_override=nm),
            "_repo": repo_fn,
            "_pr": None,
        }
        commits.append(cobj)
        commits_added += 1

    issues = linear.get("issues") or []
    comments = linear.setdefault("comments", [])
    linear_comments_added = 0
    if issues:
        iss = issues[min(12, len(issues) - 1)]
        ic = datetime.fromisoformat(str(iss["createdAt"]).replace("Z", "+00:00"))
        person = {
            "id": u["linear_user_id"],
            "name": (u.get("name") or u["login"]).strip(),
            "displayName": "Alex Kim",
            "email": u["email"],
            "avatarUrl": u.get("avatar_url"),
        }
        for j in range(4):
            c_at = ic + timedelta(hours=6 + j * 30)
            comments.append(
                {
                    "id": _u(seed, "comment", "p04rec", str(j)),
                    "body": f"[P04 recurrence] threaded execution note {j} on {iss.get('identifier', '')}.",
                    "createdAt": _iso(c_at),
                    "updatedAt": _iso(c_at),
                    "user": person,
                    "issueId": iss["id"],
                    "issue": {"id": iss["id"], "identifier": iss.get("identifier")},
                    "metadata": {"scenario": "p04_org_recurrence_topology", "story_slug": "p04_recurrence"},
                }
            )
            linear_comments_added += 1

    return {
        "schema_version": _RECURRENCE_SCHEMA,
        "applied": True,
        "anchor_login": "akim",
        "shared_email_norm": email,
        "slack_rows_added": slack_added,
        "github_commits_added": commits_added,
        "linear_comments_added": linear_comments_added,
        "slack_user_id": slack_uid,
        "github_repo": repo_fn,
    }
