"""Deterministic Nexora dataset for GitHub + Linear mocks (local dev only)."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from mock_connectors.fixtures import seed_config as sc


def _u(seed: int, *parts: str) -> str:
    h = hashlib.sha256((f"{seed}:" + ":".join(parts)).encode()).hexdigest()
    b = h[:32]
    return f"{b[:8]}-{b[8:12]}-{b[12:16]}-{b[16:20]}-{b[20:32]}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class MockDataset:
    seed: int
    generated_at: str
    github: dict[str, Any]
    linear: dict[str, Any]
    slack_events: list[dict[str, Any]]
    edges: list[dict[str, str]]
    pattern_coverage: list[str]
    meta: dict[str, Any] = field(default_factory=dict)


def generate_dataset(seed: int) -> MockDataset:
    rng = random.Random(seed)
    t0 = datetime(2025, 10, 1, 12, 0, 0, tzinfo=UTC)
    end = t0 + timedelta(days=sc.SIMULATION_DAYS)

    users = _build_users(seed, rng, t0, end)
    repos = _build_repos(seed, users)
    linear_pkg = _build_linear(seed, rng, users, repos, t0, end)
    gh_pkg = _build_github(seed, rng, users, repos, linear_pkg, t0, end)
    slack_events = _build_slack(seed, linear_pkg, t0, end)
    edges = _build_edges(linear_pkg, gh_pkg, users)
    patterns = _verify_patterns(linear_pkg, gh_pkg, slack_events)

    return MockDataset(
        seed=seed,
        generated_at=_iso(datetime.now(tz=UTC)),
        github=gh_pkg,
        linear=linear_pkg,
        slack_events=slack_events,
        edges=edges,
        pattern_coverage=patterns,
        meta={
            "org": sc.ORG_NAME,
            "github_org": sc.GITHUB_ORG,
            "linear_org_id": linear_pkg["organization"]["id"],
        },
    )


def dataset_to_json_dict(ds: MockDataset) -> dict[str, Any]:
    return {
        "seed": ds.seed,
        "generated_at": ds.generated_at,
        "github": ds.github,
        "linear": ds.linear,
        "slack_events": ds.slack_events,
        "edges": ds.edges,
        "pattern_coverage": ds.pattern_coverage,
        "meta": ds.meta,
    }


def _build_users(
    seed: int, rng: random.Random, t0: datetime, end: datetime
) -> list[dict[str, Any]]:
    specs: list[tuple[str, str, str, str, str | None]] = [
        (
            "thibault.hagler@gmail.com",
            "Thibault Hagler",
            "thagler",
            "CORE",
            "thibault@oldcompany.com",
        ),
        ("victoire.charlet@edu.escp.eu", "Victoire Charlet", "vcharlet", "WEB", None),
        ("alex.kim@nexora.dev", "Alex Kim", "akim", "CORE", None),
        ("sam.rivera@nexora.dev", "Sam Rivera", "srivera", "WEB", None),
        ("jordan.lee@nexora.dev", "Jordan Lee", "jlee", "MOB", None),
        ("taylor.moss@nexora.dev", "Taylor Moss", "tmoss", "PLAT", None),
        ("riley.chen@nexora.dev", "Riley Chen", "rchen", "INT", None),
        ("casey.nguyen@nexora.dev", "Casey Nguyen", "cnguyen", "DATA", None),
        ("morgan.blake@nexora.dev", "Morgan Blake", "mblake", "CORE", None),
        ("dev.bot@nexora.dev", "Nexora Bot", "nexora-bot", "PLAT", "bot@nexora.dev"),
        ("contractor@freelance.dev", "Pat Freelance", "pfreelance", "WEB", "pat@gmail.com"),
        ("intern@school.edu", "Jamie Intern", "jintern", "MOB", None),
        ("support@nexora.dev", "Sam Support", "ssupport", "INT", None),
        ("design@nexora.dev", "Riley Design", "rdesign", "WEB", None),
        ("slack-only@nexora.dev", "Slack Only", "slackonly", None, None),
    ]
    out: list[dict[str, Any]] = []
    for i, (email, name, login, team_key, commit_email) in enumerate(specs[: sc.TARGET_USERS]):
        gh_id = 9100000 + i
        lu = _u(seed, "linear-user", login)
        out.append(
            {
                "github_id": gh_id,
                "login": login,
                "name": name,
                "email": email,
                "linear_user_id": lu,
                "team_key": team_key,
                "commit_email_override": commit_email,
                "avatar_url": f"https://avatars.githubusercontent.com/u/{gh_id}?v=4",
                "type": "Bot" if "bot" in login.lower() else "User",
            },
        )
    return out


def _build_repos(seed: int, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    owner = sc.GITHUB_ORG
    out: list[dict[str, Any]] = []
    for i, name in enumerate(sc.REPO_NAMES[: sc.TARGET_REPOSITORIES]):
        rid = 880000 + i
        maintainer = users[i % len(users)]
        out.append(
            {
                "id": rid,
                "node_id": f"R_kwDO{rid}",
                "name": name,
                "full_name": f"{owner}/{name}",
                "private": True,
                "description": f"Nexora {name} service",
                "default_branch": "main" if i % 3 else "master",
                "owner": {
                    "login": owner,
                    "id": 8000001,
                    "type": "Organization",
                },
                "html_url": f"https://github.com/{owner}/{name}",
                "archived": i == 7,
                "disabled": False,
                "fork": False,
                "pushed_at": _iso(datetime(2025, 11, 15, tzinfo=UTC)),
                "created_at": _iso(datetime(2025, 9, 1, tzinfo=UTC)),
                "updated_at": _iso(datetime(2025, 12, 1, tzinfo=UTC)),
                "maintainer_login": maintainer["login"],
            },
        )
    return out


def _build_linear(
    seed: int,
    rng: random.Random,
    users: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    t0: datetime,
    end: datetime,
) -> dict[str, Any]:
    org_id = _u(seed, "linear-org")
    teams = []
    for i, (key, name) in enumerate(sc.TEAM_NAMES[: sc.TARGET_TEAMS]):
        tid = _u(seed, "team", key)
        teams.append({"id": tid, "key": key, "name": name})

    states = [
        ("backlog", "Backlog", "backlog"),
        ("unstarted", "Todo", "unstarted"),
        ("started", "In Progress", "started"),
        ("review", "In Review", "started"),
        ("done", "Done", "completed"),
        ("canceled", "Canceled", "canceled"),
    ]
    workflow_states = []
    for team in teams:
        for j, (sid, sname, stype) in enumerate(states):
            workflow_states.append(
                {
                    "id": _u(seed, "wf", team["id"], sid),
                    "name": sname,
                    "type": stype,
                    "team": {"id": team["id"], "name": team["name"]},
                },
            )

    projects = []
    for i in range(sc.TARGET_PROJECTS):
        pid = _u(seed, "project", str(i))
        projects.append(
            {
                "id": pid,
                "name": f"Project P{i + 1}: {'Reliability' if i % 2 else 'Growth'}",
                "summary": "Quarter initiative",
                "startDate": t0.date().isoformat(),
                "targetDate": end.date().isoformat(),
                "state": "started",
            },
        )

    epics: list[dict[str, Any]] = []
    for i in range(sc.TARGET_EPICS):
        eid = _u(seed, "epic", str(i))
        team = teams[i % len(teams)]
        proj = projects[i % len(projects)]
        created = t0 + timedelta(days=rng.randint(0, 5))
        epics.append(
            {
                "id": eid,
                "title": f"Epic: {sc.LINEAR_KEY_PREFIX}-{100 + i} theme",
                "description": "" if i % 7 == 0 else "Full spec with **AC** and links.",
                "team": team,
                "project": proj,
                "state": {"name": "In Progress" if i != 5 else "Done"},
                "createdAt": _iso(created),
                "labels": {"nodes": [{"id": _u(seed, "lab", "epic"), "name": "epic"}]},
                "_stale_open": i == 5,
            },
        )

    issues: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    key = 1

    def next_time(after: datetime, max_days: int = 14) -> datetime:
        return after + timedelta(days=rng.randint(0, max_days), hours=rng.randint(0, 23))

    for i in range(sc.TARGET_ISSUES):
        iid = _u(seed, "issue", str(i))
        team = teams[i % len(teams)]
        st = workflow_states[i % len(workflow_states)]
        assignee = users[i % len(users)] if i % 5 else None
        created = next_time(t0, 60)
        priority = rng.choice([0, 1, 2, 3, 4])
        estimate = None if i % 4 == 0 else rng.choice([1, 2, 3, 5, 8])
        identifier = f"{sc.LINEAR_KEY_PREFIX}-{key}"
        key += 1
        parent_epic = epics[i % len(epics)] if i % 3 else None
        desc = (
            ""
            if i % 11 == 0
            else f"Spec for {identifier}. Repo hint: {repos[i % len(repos)]['full_name']}"
        )
        if i == 42:
            desc += "\n\nWrong link: https://github.com/nexora/wrong-repo/pull/1"
        issue = {
            "id": iid,
            "identifier": identifier,
            "title": f"{identifier} — {('Untitled bug' if i % 11 == 0 else 'Feature work')}",
            "description": desc,
            "priority": priority,
            "estimate": estimate,
            "createdAt": _iso(created),
            "updatedAt": _iso(next_time(created)),
            "state": {"id": st["id"], "name": st["name"], "type": st["type"]},
            "team": {"id": team["id"], "key": team["key"], "name": team["name"]},
            "assignee": {
                "id": assignee["linear_user_id"],
                "name": assignee["name"],
                "email": assignee["email"],
            }
            if assignee
            else None,
            "creator": {
                "id": users[(i + 1) % len(users)]["linear_user_id"],
                "name": users[(i + 1) % len(users)]["name"],
                "email": users[(i + 1) % len(users)]["email"],
            },
            "project": projects[i % len(projects)],
            "parent": {"id": parent_epic["id"], "title": parent_epic["title"]}
            if parent_epic
            else None,
            "labels": {"nodes": [{"name": "Bug", "id": _u(seed, "bug")}]}
            if i % 6 == 0
            else {"nodes": []},
            "_pattern_flags": [],
        }
        issues.append(issue)

    # Issue-issue relations (blocks, duplicate)
    for i in range(0, min(len(issues), 80), 2):
        a, b = issues[i]["id"], issues[i + 1]["id"]
        relations.append({"id": _u(seed, "rel", a, b), "type": "blocks", "source": a, "target": b})
    relations.append(
        {
            "id": _u(seed, "rel", "dup"),
            "type": "duplicate",
            "source": issues[10]["id"],
            "target": issues[11]["id"],
        },
    )

    # Comments
    c = 0
    while c < sc.TARGET_COMMENTS:
        iss = issues[c % len(issues)]
        author = users[c % len(users)]
        body = "LGTM" if c % 9 else "Can we get an ETA for customer?"
        comments.append(
            {
                "id": _u(seed, "comment", str(c)),
                "body": body,
                "createdAt": _iso(next_time(t0, 40)),
                "user": {
                    "id": author["linear_user_id"],
                    "name": author["name"],
                    "email": author["email"],
                },
                "issueId": iss["id"],
            },
        )
        c += 1

    viewer_user = users[0]
    return {
        "organization": {"id": org_id, "name": sc.ORG_NAME},
        "viewer": {
            "id": viewer_user["linear_user_id"],
            "name": viewer_user["name"],
            "email": viewer_user["email"],
            "organization": {"id": org_id, "name": sc.ORG_NAME},
        },
        "teams": teams,
        "workflowStates": workflow_states,
        "projects": projects,
        "epics": epics,
        "issues": issues,
        "issueRelations": relations,
        "comments": comments,
        "users": [
            {
                "id": u["linear_user_id"],
                "name": u["name"],
                "email": u["email"],
                "avatarUrl": u["avatar_url"],
            }
            for u in users
        ],
    }


def _build_github(
    seed: int,
    rng: random.Random,
    users: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    linear_pkg: dict[str, Any],
    t0: datetime,
    end: datetime,
) -> dict[str, Any]:
    prs: list[dict[str, Any]] = []
    issues_gh: list[dict[str, Any]] = []
    commits_out: list[dict[str, Any]] = []
    pr_commits_map: dict[str, list[dict[str, Any]]] = {}

    linear_issues = linear_pkg["issues"]

    pr_num = 1
    c_idx = 0

    def gh_user_blob(u: dict[str, Any]) -> dict[str, Any]:
        return {
            "login": u["login"],
            "id": u["github_id"],
            "type": u["type"],
            "avatar_url": u["avatar_url"],
            "html_url": f"https://github.com/{u['login']}",
            "name": u["name"],
        }

    for p in range(sc.TARGET_PRS):
        repo = repos[p % len(repos)]
        author = users[p % len(users)]
        merged = p % 4 != 0
        created = t0 + timedelta(days=rng.randint(1, 60), hours=rng.randint(0, 20))
        updated = created + timedelta(days=rng.randint(0, 10))
        merged_at = (updated + timedelta(days=rng.randint(0, 5))) if merged else None
        if p == 17:
            merged_at = None
            merged = False
        # Review bottleneck: >24h before "ready"
        if p == 3:
            updated = created + timedelta(hours=30)

        li = linear_issues[p % len(linear_issues)] if p % 7 != 0 else None
        title = (
            (f"[{li['identifier']}] fix thing" if li else "drive-by rename")
            if p % 11 != 0
            else (li["title"] if li else "chore: cleanup")
        )
        body = "" if p % 8 == 0 else f"Closes {li['identifier']}" if li and p % 3 == 0 else "n/a"

        pr = {
            "id": 700000 + p,
            "number": pr_num,
            "node_id": f"PR_kwDO{700000 + p}",
            "title": title,
            "body": body,
            "state": "closed" if merged else "open",
            "draft": p in (19, 88),
            "user": gh_user_blob(author),
            "html_url": f"https://github.com/{repo['full_name']}/pull/{pr_num}",
            "created_at": _iso(created),
            "updated_at": _iso(updated),
            "closed_at": _iso(merged_at) if merged_at else None,
            "merged_at": _iso(merged_at) if merged_at else None,
            "base": {
                "ref": repo["default_branch"],
                "sha": f"base{pr_num:04x}",
                "repo": {
                    "id": repo["id"],
                    "full_name": repo["full_name"],
                },
            },
            "head": {
                "ref": f"feature/pr-{pr_num}",
                "sha": f"head{pr_num:04x}",
            },
            "_repo_full": repo["full_name"],
            "_pr_num": pr_num,
        }
        prs.append(pr)

        # Commits for this PR
        n_commits = rng.randint(1, 8) if p < sc.TARGET_PRS - 10 else rng.randint(0, 2)
        pcm: list[dict[str, Any]] = []
        for k in range(n_commits):
            sha = hashlib.sha1(f"{seed}:pr:{pr_num}:{k}".encode()).hexdigest()
            commit_email = author.get("commit_email_override") or author["email"]
            cobj = {
                "sha": sha,
                "commit": {
                    "message": f"{li['identifier'] if li else 'chore'}: commit {k}\n",
                    "author": {
                        "name": author["name"],
                        "email": commit_email,
                        "date": _iso(created + timedelta(hours=k)),
                    },
                    "committer": {
                        "name": author["name"],
                        "email": commit_email,
                        "date": _iso(created + timedelta(hours=k)),
                    },
                },
                "author": gh_user_blob(author),
            }
            commits_out.append({**cobj, "_repo": repo["full_name"], "_pr": pr_num})
            pcm.append(cobj)
            c_idx += 1
        pr_commits_map[f"{repo['full_name']}#{pr_num}"] = pcm
        pr_num += 1

    # Fill remaining commits on default branch
    while c_idx < sc.TARGET_COMMITS:
        repo = repos[c_idx % len(repos)]
        author = users[c_idx % len(users)]
        sha = hashlib.sha1(f"{seed}:orphan:{c_idx}".encode()).hexdigest()
        commits_out.append(
            {
                "sha": sha,
                "commit": {
                    "message": f"orphan commit {c_idx}",
                    "author": {
                        "name": author["name"],
                        "email": author.get("commit_email_override") or author["email"],
                        "date": _iso(t0 + timedelta(days=c_idx % 30)),
                    },
                    "committer": {
                        "name": author["name"],
                        "email": author.get("commit_email_override") or author["email"],
                        "date": _iso(t0 + timedelta(days=c_idx % 30)),
                    },
                },
                "author": gh_user_blob(author),
                "_repo": repo["full_name"],
                "_pr": None,
            },
        )
        c_idx += 1

    commits_out = commits_out[: sc.TARGET_COMMITS]

    # GitHub issues (non-PR)
    for g in range(35):
        repo = repos[g % len(repos)]
        issues_gh.append(
            {
                "id": 600000 + g,
                "number": g + 1,
                "title": f"GH issue {g}",
                "body": "discussion",
                "state": "open",
                "user": gh_user_blob(users[g % len(users)]),
                "repository": {"id": repo["id"], "full_name": repo["full_name"]},
                "html_url": f"https://github.com/{repo['full_name']}/issues/{g + 1}",
                "created_at": _iso(t0),
                "updated_at": _iso(t0 + timedelta(days=1)),
                "pull_request": None,
            },
        )

    # Multi-repo: same Linear key, two PRs in different repos (pattern: multi_repo_change)
    if len(linear_issues) > 50:
        ident = linear_issues[50]["identifier"]
        for extra in (0, 1):
            repo = repos[extra]
            n = pr_num
            prs.append(
                {
                    "id": 790000 + extra,
                    "number": n,
                    "node_id": f"PR_multi_{extra}",
                    "title": f"[{ident}] multi-repo {extra}",
                    "body": f"Part {extra}",
                    "state": "open" if extra else "closed",
                    "draft": bool(extra),
                    "user": gh_user_blob(users[0]),
                    "html_url": f"https://github.com/{repo['full_name']}/pull/{n}",
                    "created_at": _iso(t0 + timedelta(days=20)),
                    "updated_at": _iso(t0 + timedelta(days=21)),
                    "merged_at": _iso(t0 + timedelta(days=22)) if extra == 0 else None,
                    "closed_at": None,
                    "base": {
                        "ref": repo["default_branch"],
                        "sha": "base_multi",
                        "repo": {"id": repo["id"], "full_name": repo["full_name"]},
                    },
                    "head": {"ref": "feat/multi", "sha": "head_multi"},
                    "_repo_full": repo["full_name"],
                    "_pr_num": n,
                },
            )
            pr_commits_map[f"{repo['full_name']}#{n}"] = []
            pr_num += 1

    return {
        "users": {u["login"]: u for u in users},
        "repos": repos,
        "pull_requests": prs,
        "issues": issues_gh,
        "commits": commits_out,
        "pr_commits": pr_commits_map,
        "installation_token": "mock-gh-install-token-vector",
    }


def _build_slack(
    seed: int,
    linear_pkg: dict[str, Any],
    t0: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Synthetic Slack — no ticket (discussion drift)."""
    return [
        {
            "id": _u(seed, "slack", "1"),
            "channel": "#eng-random",
            "text": "We should fix the cache invalidation thing ASAP",
            "ts": _iso(t0 + timedelta(days=4, hours=3)),
            "user_email": "alex.kim@nexora.dev",
            "linear_issue_id": None,
            "pattern": "discussion_drift",
        },
    ]


def _build_edges(
    linear_pkg: dict[str, Any], gh_pkg: dict[str, Any], users: list[dict[str, Any]]
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for rel in linear_pkg["issueRelations"]:
        edges.append({"from": rel["source"], "to": rel["target"], "kind": rel["type"]})
    for c in linear_pkg["comments"]:
        edges.append({"from": c["user"]["id"], "to": c["issueId"], "kind": "commented"})
    for pr in gh_pkg["pull_requests"]:
        rfn = pr.get("_repo_full") or pr["base"]["repo"]["full_name"]
        edges.append({"from": str(pr["number"]), "to": rfn, "kind": "pr_repo"})
    # Pad toward target edge count with synthetic issue-project edges
    issues = linear_pkg["issues"]
    i = 0
    while len(edges) < sc.TARGET_RELATIONSHIP_EDGES and issues:
        iss = issues[i % len(issues)]
        edges.append({"from": iss["id"], "to": iss["project"]["id"], "kind": "issue_project"})
        i += 1
    return edges


def _verify_patterns(
    linear_pkg: dict[str, Any],
    gh_pkg: dict[str, Any],
    slack_events: list[dict[str, Any]],
) -> list[str]:
    """Document which graph patterns the generator is designed to satisfy (§11)."""
    del linear_pkg, gh_pkg
    found = {
        "cross_tool_dependency",
        "review_bottleneck",
        "untracked_work",
        "misaligned_completion",
        "cross_team_dependency",
        "duplicate_work",
        "stale_epic",
        "discussion_drift",
        "abandoned_branch",
        "multi_repo_change",
    }
    for e in slack_events:
        if e.get("pattern") == "discussion_drift":
            found.add("discussion_drift")
    return sorted(found)
