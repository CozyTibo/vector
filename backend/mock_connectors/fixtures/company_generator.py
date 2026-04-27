"""Deterministic Nexora dataset for full mock company connectors (local dev only)."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from mock_connectors.fixtures import execution_stories as ex
from mock_connectors.fixtures import nexora_content as nx
from mock_connectors.fixtures import seed_config as sc


def _u(seed: int, *parts: str) -> str:
    h = hashlib.sha256((f"{seed}:" + ":".join(parts)).encode()).hexdigest()
    b = h[:32]
    return f"{b[:8]}-{b[8:12]}-{b[12:16]}-{b[16:20]}-{b[20:32]}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_bot_login(login: str) -> bool:
    return "bot" in login.lower()


def _team_member_users(users: list[dict[str, Any]], team_key: str) -> list[dict[str, Any]]:
    """Humans on a Linear team (excludes bots); deterministic order."""
    m = [
        u
        for u in users
        if u.get("team_key") == team_key and not _is_bot_login(u["login"])
    ]
    return sorted(m, key=lambda u: u["login"])


def _non_bot_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [u for u in users if not _is_bot_login(u["login"])],
        key=lambda u: u["login"],
    )


def _linear_person_blob(u: dict[str, Any]) -> dict[str, Any]:
    b = _issue_actor_blob(u)
    return {"id": b["id"], "name": b["name"], "email": b["email"], "displayName": b["displayName"]}


def _user_by_linear_id(users: list[dict[str, Any]], uid: str) -> dict[str, Any] | None:
    for u in users:
        if u["linear_user_id"] == uid:
            return u
    return None


def _github_actor_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """GitHub-visible users (eng + bots). Omits Linear-only PM/design/support."""
    return [u for u in users if u.get("has_github", True)]


def _eng_assignable(users: list[dict[str, Any]], team_key: str | None) -> list[dict[str, Any]]:
    """ICs who get engineering work assigned (excludes bots)."""
    if not team_key:
        return []
    roles = ("engineering", "contractor", "intern")
    return sorted(
        [
            u
            for u in users
            if u.get("team_key") == team_key
            and u.get("role") in roles
            and not _is_bot_login(u["login"])
        ],
        key=lambda u: u["login"],
    )


def _pm_style_users(users: list[dict[str, Any]], team_key: str | None) -> list[dict[str, Any]]:
    """Product / design / support — active on Linear, often not in the GitHub org."""
    if not team_key:
        return []
    roles = ("product", "design", "support")
    return sorted(
        [u for u in users if u.get("team_key") == team_key and u.get("role") in roles],
        key=lambda u: u["login"],
    )


def _em_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [u for u in users if u.get("role") == "engineering_manager"]


def _user_by_login(users: list[dict[str, Any]], login: str) -> dict[str, Any] | None:
    for u in users:
        if u["login"] == login:
            return u
    return None


def _issue_actor_blob(u: dict[str, Any]) -> dict[str, Any]:
    """Linear issue assignee/creator shape (supports messy display names)."""
    name = (u.get("name") or "").strip() or u["login"]
    dn = u.get("linear_display_name")
    if not dn:
        dn = name.split()[0] if name else u["login"]
    return {
        "id": u["linear_user_id"],
        "name": name,
        "displayName": dn,
        "email": u["email"],
    }


def _apply_user_hygiene(users: list[dict[str, Any]]) -> None:
    """Real-world identity drift: duplicate nicknames, empty GH names, stale emails, casing."""
    by = {u["login"]: u for u in users}
    vc = by.get("vcharlet")
    if vc:
        vc["linear_display_name"] = "V.Charlet"
    sr = by.get("srivera")
    if sr:
        sr["linear_display_name"] = "Alex"
    ak = by.get("akim")
    if ak:
        ak["linear_display_name"] = "Alex"
    jl = by.get("jlee")
    if jl:
        jl["email"] = jl["email"].upper()
    mb = by.get("mblake")
    if mb:
        mb["github_profile_name_empty"] = True
    cn = by.get("cnguyen")
    if cn:
        cn["email"] = "casey_nguyen@nexora.dev"
        cn["name"] = "Casey Nguyen"
    th = by.get("thagler")
    if th and th.get("name"):
        th["name"] = f" {th['name']} "
    su = by.get("ssupport")
    if su:
        su["email"] = "sam.support@nexora.dev"


def _assert_no_github_activity_for_linear_only_users(
    users: list[dict[str, Any]], gh_pkg: dict[str, Any]
) -> None:
    skip = {u["login"] for u in users if not u.get("has_github", True)}
    for pr in gh_pkg["pull_requests"]:
        login = pr.get("user", {}).get("login")
        if login in skip:
            msg = f"linear-only user {login} must not author PRs"
            raise AssertionError(msg)
    for c in gh_pkg["commits"]:
        login = c.get("author", {}).get("login")
        if login in skip:
            msg = f"linear-only user {login} must not author commits"
            raise AssertionError(msg)
    for iss in gh_pkg["issues"]:
        login = iss.get("user", {}).get("login")
        if login in skip:
            msg = f"linear-only user {login} must not open GitHub issues"
            raise AssertionError(msg)


@dataclass
class MockDataset:
    seed: int
    generated_at: str
    github: dict[str, Any]
    linear: dict[str, Any]
    slack_events: list[dict[str, Any]]
    notion: dict[str, Any]
    calls: dict[str, Any]
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
    _assert_no_github_activity_for_linear_only_users(users, gh_pkg)
    slack_events = _build_slack(seed, linear_pkg, t0, end)
    notion_pkg = _build_notion(seed, users, linear_pkg, slack_events, t0, end)
    calls_pkg = _build_calls(seed, users, linear_pkg, slack_events, t0, end)
    edges = _build_edges(linear_pkg, gh_pkg, users)
    patterns = _verify_patterns(linear_pkg, gh_pkg, slack_events)

    return MockDataset(
        seed=seed,
        generated_at=_iso(datetime.now(tz=UTC)),
        github=gh_pkg,
        linear=linear_pkg,
        slack_events=slack_events,
        notion=notion_pkg,
        calls=calls_pkg,
        edges=edges,
        pattern_coverage=patterns,
        meta={
            "org": sc.ORG_NAME,
            "github_org": sc.GITHUB_ORG,
            "linear_org_id": linear_pkg["organization"]["id"],
            "product": nx.NEXORA_BLURB,
        },
    )


def dataset_to_json_dict(ds: MockDataset) -> dict[str, Any]:
    linear = dict(ds.linear)
    linear.pop("_execution_bundle", None)
    return {
        "seed": ds.seed,
        "generated_at": ds.generated_at,
        "github": ds.github,
        "linear": linear,
        "slack_events": ds.slack_events,
        "notion": ds.notion,
        "calls": ds.calls,
        "edges": ds.edges,
        "pattern_coverage": ds.pattern_coverage,
        "meta": ds.meta,
    }


# Role + GitHub presence: PM/design/support often live in Linear only; engineers ship in GitHub.
_RAW_USER_SPECS: list[dict[str, Any]] = [
    {
        "email": "thibault.hagler@gmail.com",
        "name": "Thibault Hagler",
        "login": "thagler",
        "team_key": "CORE",
        "commit_email": "thibault@oldcompany.com",
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "victoire.charlet@edu.escp.eu",
        "name": "Victoire Charlet",
        "login": "vcharlet",
        "team_key": "WEB",
        "commit_email": None,
        "role": "product",
        "has_github": False,
    },
    {
        "email": "alex.kim@nexora.dev",
        "name": "Alex Kim",
        "login": "akim",
        "team_key": "CORE",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "sam.rivera@nexora.dev",
        "name": "Sam Rivera",
        "login": "srivera",
        "team_key": "WEB",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "jordan.lee@nexora.dev",
        "name": "Jordan Lee",
        "login": "jlee",
        "team_key": "MOB",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "taylor.moss@nexora.dev",
        "name": "Taylor Moss",
        "login": "tmoss",
        "team_key": "PLAT",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "riley.chen@nexora.dev",
        "name": "Riley Chen",
        "login": "rchen",
        "team_key": "INT",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "casey.nguyen@nexora.dev",
        "name": "Casey Nguyen",
        "login": "cnguyen",
        "team_key": "DATA",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "morgan.blake@nexora.dev",
        "name": "Morgan Blake",
        "login": "mblake",
        "team_key": "CORE",
        "commit_email": None,
        "role": "engineering",
        "has_github": True,
    },
    {
        "email": "sara.collins@nexora.dev",
        "name": "Sara Collins",
        "login": "scollins",
        "team_key": "CORE",
        "commit_email": None,
        "role": "engineering_manager",
        "has_github": True,
    },
    {
        "email": "dev.bot@nexora.dev",
        "name": "Nexora Bot",
        "login": "nexora-bot",
        "team_key": "PLAT",
        "commit_email": "bot@nexora.dev",
        "role": "bot",
        "has_github": True,
    },
    {
        "email": "contractor@freelance.dev",
        "name": "Pat Freelance",
        "login": "pfreelance",
        "team_key": "WEB",
        "commit_email": "pat@gmail.com",
        "role": "contractor",
        "has_github": True,
    },
    {
        "email": "intern@school.edu",
        "name": "Jamie Intern",
        "login": "jintern",
        "team_key": "MOB",
        "commit_email": None,
        "role": "intern",
        "has_github": True,
    },
    {
        "email": "support@nexora.dev",
        "name": "Sam Support",
        "login": "ssupport",
        "team_key": "INT",
        "commit_email": None,
        "role": "support",
        "has_github": False,
    },
    {
        "email": "design@nexora.dev",
        "name": "Riley Design",
        "login": "rdesign",
        "team_key": "WEB",
        "commit_email": None,
        "role": "design",
        "has_github": False,
    },
    {
        "email": "slack-only@nexora.dev",
        "name": "Slack Only",
        "login": "slackonly",
        "team_key": None,
        "commit_email": None,
        "role": "other",
        "has_github": False,
    },
]


def _build_users(
    seed: int, rng: random.Random, t0: datetime, end: datetime
) -> list[dict[str, Any]]:
    del rng, t0, end
    out: list[dict[str, Any]] = []
    for i, spec in enumerate(_RAW_USER_SPECS[: sc.TARGET_USERS]):
        gh_id = 9100000 + i
        login = spec["login"]
        lu = _u(seed, "linear-user", login)
        out.append(
            {
                "github_id": gh_id,
                "login": login,
                "name": spec["name"],
                "email": spec["email"],
                "linear_user_id": lu,
                "team_key": spec["team_key"],
                "commit_email_override": spec.get("commit_email"),
                "avatar_url": f"https://avatars.githubusercontent.com/u/{gh_id}?v=4",
                "type": "Bot" if spec.get("role") == "bot" else "User",
                "role": spec["role"],
                "has_github": bool(spec.get("has_github", True)),
                "linear_display_name": spec.get("linear_display_name"),
                "github_profile_name_empty": False,
            },
        )
    _apply_user_hygiene(out)
    return out


def _build_repos(seed: int, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    owner = sc.GITHUB_ORG
    gh_users = _github_actor_users(users)
    out: list[dict[str, Any]] = []
    for i, name in enumerate(sc.REPO_NAMES[: sc.TARGET_REPOSITORIES]):
        rid = 880000 + i
        maintainer = gh_users[i % len(gh_users)]
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
        teams.append(
            {
                "id": tid,
                "key": key,
                "name": name,
                "description": f"{name} — product engineering",
                "private": i % 4 == 0,
            },
        )

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
        team = teams[i % len(teams)]
        tm = _team_member_users(users, team["key"])
        if not tm:
            tm = _non_bot_users(users)
        pm = _pm_style_users(users, team["key"])
        eng = _eng_assignable(users, team["key"])
        if pm and i % 2 == 0:
            lead_u = pm[i % len(pm)]
        elif eng:
            lead_u = eng[i % len(eng)]
        else:
            lead_u = tm[i % len(tm)]
        bp = nx.project_blueprint(i)
        projects.append(
            {
                "id": pid,
                "name": bp["name"],
                "slug": bp["slug"],
                "description": bp["description"],
                "summary": bp["summary"],
                "startDate": t0.date().isoformat(),
                "targetDate": end.date().isoformat(),
                "state": "started",
                "team": {"id": team["id"], "key": team["key"], "name": team["name"]},
                "lead": _linear_person_blob(lead_u),
            },
        )

    epics: list[dict[str, Any]] = []
    for i in range(sc.TARGET_EPICS):
        eid = _u(seed, "epic", str(i))
        team = teams[i % len(teams)]
        proj = projects[i % len(projects)]
        created = t0 + timedelta(days=rng.randint(0, 5))
        tm = _team_member_users(users, team["key"])
        if not tm:
            tm = _non_bot_users(users)
        pm = _pm_style_users(users, team["key"])
        eng = _eng_assignable(users, team["key"])
        if pm and i % 3 != 0:
            epic_lead = pm[i % len(pm)]
        elif eng:
            epic_lead = eng[i % len(eng)]
        else:
            epic_lead = tm[i % len(tm)]
        epic_ident = f"{sc.LINEAR_KEY_PREFIX}-{200 + i}"
        cust = nx.customer_for_index(i)
        epic_title = nx.epic_title(i, team["key"], proj["name"])
        epic_desc = "" if i % 7 == 0 else nx.epic_description(i, cust)
        epics.append(
            {
                "id": eid,
                "identifier": epic_ident,
                "title": epic_title,
                "description": epic_desc,
                "team": team,
                "project": proj,
                "lead": _linear_person_blob(epic_lead),
                "state": {"name": "In Progress" if i != 5 else "Done"},
                "createdAt": _iso(created),
                "labels": {
                    "nodes": [{"id": _u(seed, "lab", "epic"), "name": "epic", "color": "#BB6BD9"}],
                },
                "_stale_open": i == 5,
            },
        )

    epics_by_team: dict[str, list[dict[str, Any]]] = {}
    for e in epics:
        epics_by_team.setdefault(e["team"]["id"], []).append(e)

    bundle = ex.build_execution_bundle(seed, t0, end, sc.TARGET_ISSUES)
    ed_idx = bundle.epic_drift_epic_index
    if ed_idx is not None and 0 <= ed_idx < len(epics):
        epics[ed_idx]["state"] = {"name": "In Progress"}
        epics[ed_idx]["_stale_open"] = True

    epics_by_proj: dict[str, list[dict[str, Any]]] = {}
    for e in epics:
        epics_by_proj.setdefault(e["project"]["id"], []).append(e)

    # Sprint cycles per team (before issues so issues can reference a cycle when needed).
    cycles: list[dict[str, Any]] = []
    period_days = 14
    for team in teams:
        for cnum in range(8):
            cstart = t0 + timedelta(days=cnum * period_days)
            cend = cstart + timedelta(days=period_days - 1)
            cycles.append(
                {
                    "id": _u(seed, "cycle", team["id"], str(cnum)),
                    "number": cnum + 1,
                    "name": f"{team['key']}-{cnum + 1}",
                    "startsAt": _iso(cstart),
                    "endsAt": _iso(cend),
                    "completedAt": _iso(cend) if cnum < 6 else None,
                    "progress": 1.0 if cnum < 6 else 0.35,
                    "team": {
                        "id": team["id"],
                        "key": team["key"],
                        "name": team["name"],
                    },
                },
            )
    cycles_by_team: dict[str, list[dict[str, Any]]] = {t["id"]: [] for t in teams}
    for c in cycles:
        cycles_by_team[c["team"]["id"]].append(c)

    bug_label_id = _u(seed, "label", "bug")

    issues: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    team_by_key = {t["key"]: t for t in teams}
    em_users_list = _em_users(users)
    em_lead = em_users_list[0] if em_users_list else None

    desired_comment_lens = [
        max(2, len(bundle.issue_plans[i].comment_offsets_h)) for i in range(sc.TARGET_ISSUES)
    ]
    s_cl = sum(desired_comment_lens)
    scale_c = sc.TARGET_COMMENTS / max(s_cl, 1)
    per_issue_counts = [
        max(2, min(10, int(round(desired_comment_lens[i] * scale_c))))
        for i in range(sc.TARGET_ISSUES)
    ]
    adj_c = sc.TARGET_COMMENTS - sum(per_issue_counts)
    step_c = 0
    while adj_c != 0 and step_c < sc.TARGET_ISSUES * 25:
        idx = step_c % sc.TARGET_ISSUES
        if adj_c > 0 and per_issue_counts[idx] < 10:
            per_issue_counts[idx] += 1
            adj_c -= 1
        elif adj_c < 0 and per_issue_counts[idx] > 2:
            per_issue_counts[idx] -= 1
            adj_c += 1
        step_c += 1

    for i in range(sc.TARGET_ISSUES):
        plan = bundle.issue_plans[i]
        iid = _u(seed, "issue", str(i))
        team = team_by_key[plan.team_key]
        tk = team["key"]
        tm = _team_member_users(users, tk)
        if not tm:
            tm = _non_bot_users(users)
        eng_pool = _eng_assignable(users, tk) or [
            u for u in tm if not _is_bot_login(u["login"])
        ]
        pm_pool = _pm_style_users(users, tk)
        assignee_u = eng_pool[i % len(eng_pool)] if i % 5 else None
        if plan.final_assignee_override_login:
            ou = _user_by_login(users, plan.final_assignee_override_login)
            if ou:
                assignee_u = ou
        if pm_pool and (i % 3 == 0 or i % 7 in (2, 5)):
            creator_u = pm_pool[i % len(pm_pool)]
        else:
            creator_u = eng_pool[(i + 1) % len(eng_pool)]
        if (
            assignee_u
            and creator_u["linear_user_id"] == assignee_u["linear_user_id"]
            and len(eng_pool) > 1
        ):
            creator_u = eng_pool[(i + 2) % len(eng_pool)]
        priority = rng.choice([0, 1, 2, 3, 4])
        estimate = None if i % 4 == 0 else rng.choice([1, 2, 3, 5, 8])
        identifier = f"{sc.LINEAR_KEY_PREFIX}-{i + 1}"

        parent_epic = None
        if 200 <= i <= 209:
            proj = projects[2]
            pe_list = epics_by_proj.get(proj["id"], [])
            parent_epic = pe_list[i % len(pe_list)] if pe_list else epics[2]
        elif 210 <= i <= 217:
            proj = projects[5]
            pe_list = epics_by_proj.get(proj["id"], [])
            parent_epic = pe_list[i % len(pe_list)] if pe_list else epics[5]
        elif 218 <= i <= 227 and ed_idx is not None:
            proj = epics[ed_idx]["project"]
            parent_epic = epics[ed_idx]
        else:
            proj = projects[i % len(projects)]
            same_team_epics = epics_by_team.get(team["id"], [])
            if same_team_epics and i % 3 == 0:
                parent_epic = same_team_epics[i % len(same_team_epics)]

        repo_full = repos[i % len(repos)]["full_name"]
        cust = nx.customer_for_index(i)
        proj_name = proj["name"]
        epic_ident_str = parent_epic["identifier"] if parent_epic else None
        title, desc = nx.issue_title_and_body(
            tk,
            i,
            identifier=identifier,
            repo_full=repo_full,
            customer=cust,
            project_name=proj_name,
            epic_ident=epic_ident_str,
        )
        if i == 42 and desc:
            desc += "\n\nWrong link: https://github.com/nexora/wrong-repo/pull/1"
        if i % 23 == 1 and desc:
            desc = f"{desc}  "
        if i % 29 == 2 and desc:
            desc += "\n\ndcoument owner:TBD (template never updated)"
        if i % 31 == 4 and desc:
            desc += "\n\n<!-- pasted from Notion, formatting broken -->"
        team_cycles = cycles_by_team.get(team["id"], [])
        cycle_ref = None
        if team_cycles and i % 5 == 0:
            cy = team_cycles[(i // 5) % len(team_cycles)]
            cycle_ref = {"id": cy["id"], "name": cy["name"], "number": cy["number"]}
        if i % 19 == 3 and "Feature" in title:
            title = title.replace("Feature", "Featuer", 1)
        if i % 17 == 5:
            title = title.replace("—", "-", 1)

        st_blob = ex.workflow_state_for_team(workflow_states, team["id"], plan.state_name)
        meta = {
            "scenario": plan.metadata.get("scenario", plan.story_slug),
            "story_slug": plan.story_slug,
        }
        if plan.initiative:
            meta["initiative"] = plan.initiative

        issue = {
            "id": iid,
            "identifier": identifier,
            "title": title,
            "description": desc,
            "priority": priority,
            "estimate": estimate,
            "createdAt": _iso(plan.created_at),
            "updatedAt": _iso(plan.updated_at),
            "state": {"id": st_blob["id"], "name": st_blob["name"], "type": st_blob["type"]},
            "team": {"id": team["id"], "key": team["key"], "name": team["name"]},
            "assignee": _issue_actor_blob(assignee_u) if assignee_u else None,
            "creator": _issue_actor_blob(creator_u),
            "project": proj,
            "parent": {
                "id": parent_epic["id"],
                "identifier": parent_epic["identifier"],
                "title": parent_epic["title"],
                "lead": parent_epic["lead"],
            }
            if parent_epic
            else None,
            "cycle": cycle_ref,
            "labels": {
                "nodes": [{"name": "Bug", "id": bug_label_id, "color": "#F2994A"}],
            }
            if i % 6 == 0
            else {"nodes": []},
            "metadata": meta,
            "github_pr_number": None,
            "_pattern_flags": [],
            "_issue_index": i,
        }
        issues.append(issue)

    id_to_ident_preview = {x["id"]: x["identifier"] for x in issues}

    def _rel_row(rid: str, rtype: str, src: str, tgt: str) -> dict[str, Any]:
        return {
            "id": rid,
            "type": rtype,
            "issue": {"id": src, "identifier": id_to_ident_preview.get(src, "")},
            "relatedIssue": {"id": tgt, "identifier": id_to_ident_preview.get(tgt, "")},
        }

    rel_keys: set[tuple[str, str, str]] = set()

    def _add_rel(rid: str, rtype: str, src: str, tgt: str) -> None:
        if src == tgt:
            return
        key_r = (src, tgt, rtype)
        if key_r in rel_keys:
            return
        rel_keys.add(key_r)
        relations.append(_rel_row(rid, rtype, src, tgt))

    for plan in bundle.issue_plans:
        ia = issues[plan.issue_index]["id"]
        if plan.duplicate_partner_index is not None:
            j = plan.duplicate_partner_index
            if plan.issue_index < j:
                _add_rel(
                    _u(seed, "rel", "dup-story", str(plan.issue_index)),
                    "duplicate",
                    ia,
                    issues[j]["id"],
                )
        if plan.blocked_by_index is not None:
            blocker = issues[plan.blocked_by_index]["id"]
            _add_rel(
                _u(seed, "rel", "blk-by", str(plan.issue_index)),
                "blocks",
                blocker,
                ia,
            )
        if plan.blocks_next_index is not None:
            tgt = issues[plan.blocks_next_index]["id"]
            _add_rel(
                _u(seed, "rel", "blk-next", str(plan.issue_index)),
                "blocks",
                ia,
                tgt,
            )

    api_kw = (
        "API",
        "api",
        "webhook",
        "endpoint",
        "session",
        "schema",
        "OAuth",
        "GraphQL",
        "rate limit",
        "idempotent",
        "audit log",
    )
    ui_kw = (
        "Dashboard",
        "UI",
        "Web",
        "modal",
        "table",
        "banner",
        "empty state",
        "LCP",
        "Command-K",
        "virtualization",
    )
    data_kw = ("Warehouse", "GDPR", "event schema", "dbt", "partition", "PII", "export job")

    def _title_hit(iss: dict[str, Any], kws: tuple[str, ...]) -> bool:
        t = iss.get("title") or ""
        return any(k in t for k in kws)

    api_issues = [x for x in issues if _title_hit(x, api_kw)]
    ui_issues = [x for x in issues if _title_hit(x, ui_kw)]
    data_issues = [x for x in issues if _title_hit(x, data_kw)]
    core_issues = [x for x in issues if x["team"]["key"] == "CORE"]

    for j in range(min(len(api_issues), len(ui_issues), 52)):
        _add_rel(
            _u(seed, "rel", "api-ui", str(j)),
            "blocks",
            api_issues[j]["id"],
            ui_issues[j]["id"],
        )

    for j in range(min(len(data_issues), len(core_issues), 28)):
        _add_rel(
            _u(seed, "rel", "data-core", str(j)),
            "related",
            data_issues[j]["id"],
            core_issues[j]["id"],
        )

    for step_i in range(0, len(issues) - 5, 10):
        a, b = issues[step_i]["id"], issues[step_i + 5]["id"]
        if issues[step_i]["team"]["id"] == issues[step_i + 5]["team"]["id"]:
            _add_rel(
                _u(seed, "rel", "dup-pair", str(step_i)),
                "duplicate",
                a,
                b,
            )

    # Same-team duplicates: index and index+6 share team (i % 6).
    for base in range(0, min(120, len(issues) - 6), 12):
        _add_rel(
            _u(seed, "rel", "dup-stagger", str(base)),
            "duplicate",
            issues[base]["id"],
            issues[base + 6]["id"],
        )

    for step_i in range(0, min(len(issues) - 2, 110), 7):
        aa, cc = issues[step_i]["id"], issues[step_i + 2]["id"]
        _add_rel(_u(seed, "rel", "blk", aa, cc), "blocks", aa, cc)

    c_seq = 0
    for issue_idx, iss in enumerate(issues):
        plan = bundle.issue_plans[issue_idx]
        tk_c = iss["team"]["key"]
        assignee_blob = iss.get("assignee")
        creator_blob = iss.get("creator")
        assignee_u = (
            _user_by_linear_id(users, str(assignee_blob["id"]))
            if isinstance(assignee_blob, dict)
            else None
        )
        creator_u = (
            _user_by_linear_id(users, str(creator_blob["id"]))
            if isinstance(creator_blob, dict)
            else None
        )
        eng_pool_c = _eng_assignable(users, tk_c) or [
            u for u in _team_member_users(users, tk_c) if not _is_bot_login(u["login"])
        ]
        pm_pool_c = _pm_style_users(users, tk_c)
        n_here = per_issue_counts[issue_idx]
        arc = nx.COMMENT_ARCS[issue_idx % len(nx.COMMENT_ARCS)]
        line_tpls = nx.arc_lines_for_count(arc, n_here)
        thread = nx.format_comment_arc(
            line_tpls,
            issue=iss,
            users=users,
            eng_pool=eng_pool_c,
            pm_pool=pm_pool_c,
            assignee=assignee_u,
            creator=creator_u,
            issue_index=issue_idx,
            customer=nx.customer_for_index(issue_idx),
            repo=repos[issue_idx % len(repos)]["full_name"],
        )
        ic_raw = iss["createdAt"].replace("Z", "+00:00")
        ic = datetime.fromisoformat(ic_raw)
        off = plan.comment_offsets_h
        for t_i, (author, body) in enumerate(thread):
            hours = off[t_i] if t_i < len(off) else float(2 + t_i * 24)
            c_at = ic + timedelta(hours=hours, minutes=(c_seq * 17) % 55)
            ucap = datetime.fromisoformat(iss["updatedAt"].replace("Z", "+00:00"))
            if c_at > ucap:
                c_at = ucap - timedelta(minutes=min(59, t_i + 1))
            use_em = bool(
                t_i < len(plan.comment_em_mask) and plan.comment_em_mask[t_i]
            )
            if use_em and em_lead:
                author = em_lead
                short_t = (iss.get("title") or "")[:72]
                body = (
                    "[People management] Can we get a concrete ETA on **"
                    f"{iss.get('identifier', '')}** — {short_t}? "
                    "Customer comms are asking for a slip timeline."
                )
            c_iso = _iso(c_at)
            meta_c = {
                "scenario": plan.metadata.get("scenario", plan.story_slug),
                "story_slug": plan.story_slug,
            }
            comments.append(
                {
                    "id": _u(seed, "comment", str(c_seq)),
                    "body": body,
                    "createdAt": c_iso,
                    "updatedAt": c_iso,
                    "user": _linear_person_blob(author),
                    "issueId": iss["id"],
                    "issue": {"id": iss["id"], "identifier": iss["identifier"]},
                    "metadata": meta_c,
                },
            )
            c_seq += 1

    # IssueLabel nodes (workspace defaults + per-issue labels)
    label_pool: list[dict[str, Any]] = [
        {"id": _u(seed, "label", "bug"), "name": "Bug", "color": "#F2994A", "team": None},
        {"id": _u(seed, "label", "feature"), "name": "Feature", "color": "#2D9CDB", "team": None},
        {"id": _u(seed, "label", "debt"), "name": "Tech debt", "color": "#9B51E0", "team": None},
        {"id": _u(seed, "label", "customer"), "name": "Customer", "color": "#EB5757", "team": None},
    ]
    labels: list[dict[str, Any]] = list(label_pool)
    seen_label_ids = {lb["id"] for lb in labels}
    for iss in issues:
        team_ref = {"id": iss["team"]["id"], "name": iss["team"]["name"]}
        for ln in iss.get("labels", {}).get("nodes", []):
            lid = ln["id"]
            if lid in seen_label_ids:
                continue
            seen_label_ids.add(lid)
            labels.append(
                {
                    "id": lid,
                    "name": ln["name"],
                    "color": ln.get("color", "#828282"),
                    "team": team_ref,
                },
            )

    # Initiatives (Linear Initiative — mapped from epics / parent themes)
    initiatives: list[dict[str, Any]] = []
    for epic in epics:
        initiatives.append(
            {
                "id": epic["id"],
                "name": epic["title"],
                "description": epic.get("description") or "",
                "targetDate": epic["project"].get("targetDate"),
                "status": {"name": epic["state"]["name"]},
                "owner": epic["lead"],
                "lead": epic["lead"],
                "projects": {
                    "nodes": [
                        {"id": epic["project"]["id"], "name": epic["project"]["name"]},
                    ],
                },
                "teams": {
                    "nodes": [
                        {
                            "id": epic["team"]["id"],
                            "key": epic["team"]["key"],
                            "name": epic["team"]["name"],
                        },
                    ],
                },
            },
        )

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
        "cycles": cycles,
        "labels": labels,
        "initiatives": initiatives,
        "users": [
            {
                "id": u["linear_user_id"],
                "name": _issue_actor_blob(u)["name"],
                "displayName": _issue_actor_blob(u)["displayName"],
                "email": u["email"],
                "avatarUrl": u["avatar_url"],
                "active": True,
                "guest": "contractor" in u["email"] or "intern" in u["email"],
                "admin": u["login"] in ("thagler", "vcharlet"),
            }
            for u in users
        ],
        "_execution_bundle": bundle,
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
    del rng, end
    bundle = linear_pkg.get("_execution_bundle")
    if bundle is None:
        msg = "linear package missing _execution_bundle"
        raise RuntimeError(msg)

    prs: list[dict[str, Any]] = []
    issues_gh: list[dict[str, Any]] = []
    commits_out: list[dict[str, Any]] = []
    pr_commits_map: dict[str, list[dict[str, Any]]] = {}

    linear_issues = linear_pkg["issues"]
    gh_users = _github_actor_users(users)
    if not gh_users:
        msg = "mock dataset needs at least one GitHub-visible user"
        raise ValueError(msg)

    em_gh = next((u for u in gh_users if u.get("role") == "engineering_manager"), None)
    coders = [u for u in gh_users if u.get("role") != "engineering_manager"] or gh_users

    def gh_user_blob(u: dict[str, Any]) -> dict[str, Any]:
        raw_name = (u.get("name") or "").strip()
        gh_name: str | None = raw_name if raw_name else None
        if u.get("github_profile_name_empty"):
            gh_name = None
        return {
            "login": u["login"],
            "id": u["github_id"],
            "type": u["type"],
            "avatar_url": u["avatar_url"],
            "html_url": f"https://github.com/{u['login']}",
            "name": gh_name,
        }

    pending: list[dict[str, Any]] = []
    for opp in bundle.orphan_prs:
        pending.append({"sort": opp.created_at, "kind": "orphan", "opp": opp})

    for i, iss in enumerate(linear_issues):
        plan = bundle.issue_plans[i]
        if plan.pr is None or plan.shadow_pr_global_index is not None:
            continue
        ps = plan.pr
        ic = datetime.fromisoformat(iss["createdAt"].replace("Z", "+00:00"))
        pr_created = ic + timedelta(hours=ps.created_offset_h)
        pr_updated = ic + timedelta(hours=ps.updated_offset_h)
        merged_at = (
            ic + timedelta(hours=ps.merged_offset_h) if ps.merged_offset_h is not None else None
        )
        last_commit = pr_created
        if ps.last_commit_offset_h is not None:
            last_commit = ic + timedelta(hours=ps.last_commit_offset_h)
        elif merged_at is not None:
            last_commit = merged_at - timedelta(hours=1)
        pending.append(
            {
                "sort": pr_created,
                "kind": "issue",
                "issue_index": i,
                "iss": iss,
                "plan": plan,
                "ps": ps,
                "pr_created": pr_created,
                "pr_updated": pr_updated,
                "merged_at": merged_at,
                "last_commit": last_commit,
            },
        )

    pending.sort(key=lambda x: x["sort"])

    pr_num = 1
    c_idx = 0
    orphan_pr_numbers: list[int] = []

    def append_commits_for_pr(
        repo: dict[str, Any],
        author: dict[str, Any],
        pr_n: int,
        t_start: datetime,
        t_end: datetime,
        label: str,
    ) -> None:
        nonlocal c_idx
        span_h = max(1.0, (t_end - t_start).total_seconds() / 3600.0)
        n_commits = max(1, min(8, int(span_h // 6) + 1))
        pcm: list[dict[str, Any]] = []
        for k in range(n_commits):
            frac = k / max(1, n_commits - 1) if n_commits > 1 else 0.0
            c_at = t_start + timedelta(seconds=frac * (t_end - t_start).total_seconds())
            sha = hashlib.sha1(f"{seed}:pr:{pr_n}:{k}".encode()).hexdigest()
            commit_email = author.get("commit_email_override") or author["email"]
            cobj = {
                "sha": sha,
                "commit": {
                    "message": f"{label}: commit {k}\n",
                    "author": {
                        "name": author["name"],
                        "email": commit_email,
                        "date": _iso(c_at),
                    },
                    "committer": {
                        "name": author["name"],
                        "email": commit_email,
                        "date": _iso(c_at),
                    },
                },
                "author": gh_user_blob(author),
            }
            commits_out.append({**cobj, "_repo": repo["full_name"], "_pr": pr_n})
            pcm.append(cobj)
            c_idx += 1
        pr_commits_map[f"{repo['full_name']}#{pr_n}"] = pcm

    for item in pending:
        if item["kind"] == "orphan":
            opp = item["opp"]
            repo = repos[opp.repo_index % len(repos)]
            author = coders[pr_num % len(coders)]
            created = opp.created_at
            updated = opp.updated_at
            merged_at = opp.merged_at
            merged = merged_at is not None
            pr = {
                "id": 700000 + pr_num,
                "number": pr_num,
                "node_id": f"PR_kwDO{700000 + pr_num}",
                "title": "fix: cache invalidation for session store",
                "body": nx.enrich_github_pr_body_for_manager_insight(
                    pr_num, "Shadow path — ticket backfill pending."
                ),
                "state": "closed" if merged else "open",
                "draft": False,
                "user": gh_user_blob(author),
                "html_url": f"https://github.com/{repo['full_name']}/pull/{pr_num}",
                "created_at": _iso(created),
                "updated_at": _iso(updated),
                "closed_at": _iso(merged_at) if merged_at else None,
                "merged_at": _iso(merged_at) if merged_at else None,
                "base": {
                    "ref": repo["default_branch"],
                    "sha": f"base{pr_num:04x}",
                    "repo": {"id": repo["id"], "full_name": repo["full_name"]},
                },
                "head": {"ref": f"feature/pr-{pr_num}", "sha": f"head{pr_num:04x}"},
                "_repo_full": repo["full_name"],
                "_pr_num": pr_num,
                "metadata": {**opp.metadata, "link_style": "none"},
            }
            if em_gh:
                pr["_mock_pr_reviews"] = [
                    {
                        "user": gh_user_blob(em_gh),
                        "body": (
                            "Noted — please open the tracking ticket before next deploy window."
                        ),
                        "submitted_at": _iso(created + timedelta(hours=18)),
                    },
                ]
            prs.append(pr)
            append_commits_for_pr(
                repo, author, pr_num, created, opp.last_commit_at, "shadow"
            )
            orphan_pr_numbers.append(pr_num)
            pr_num += 1
            continue

        iss = item["iss"]
        plan = item["plan"]
        ps = item["ps"]
        i = item["issue_index"]
        repo = repos[ps.repo_index % len(repos)]
        author = coders[(i + seed) % len(coders)]
        ident = iss["identifier"]
        link = ps.link_style
        if link == "title_ref":
            title = f"[{ident}] fix implementation"
            body = "n/a"
        elif link == "body_closes":
            title = f"Implement rollout for {ident}"
            body = f"Closes {ident}"
        elif link == "issue_field_only":
            title = "Harden retry path and backoff"
            body = "Scope tracked in Linear (linked issue field)."
        else:
            title = "drive-by rename internal helper"
            body = ""
        body = nx.enrich_github_pr_body_for_manager_insight(i, body)
        merged = ps.merged_offset_h is not None and not ps.abandoned
        pr = {
            "id": 700000 + pr_num,
            "number": pr_num,
            "node_id": f"PR_kwDO{700000 + pr_num}",
            "title": title,
            "body": body,
            "state": "closed" if merged else "open",
            "draft": i in (19, 88) or (seed + i) % 61 == 0,
            "user": gh_user_blob(author),
            "html_url": f"https://github.com/{repo['full_name']}/pull/{pr_num}",
            "created_at": _iso(item["pr_created"]),
            "updated_at": _iso(item["pr_updated"]),
            "closed_at": _iso(item["merged_at"]) if item["merged_at"] else None,
            "merged_at": _iso(item["merged_at"]) if item["merged_at"] else None,
            "base": {
                "ref": repo["default_branch"],
                "sha": f"base{pr_num:04x}",
                "repo": {"id": repo["id"], "full_name": repo["full_name"]},
            },
            "head": {"ref": f"feature/pr-{pr_num}", "sha": f"head{pr_num:04x}"},
            "_repo_full": repo["full_name"],
            "_pr_num": pr_num,
            "metadata": {
                "scenario": plan.metadata.get("scenario", plan.story_slug),
                "link_style": link,
            },
        }
        if em_gh and i in (1, 2, 7, 160, 200):
            pr["_mock_pr_reviews"] = [
                {
                    "user": gh_user_blob(em_gh),
                    "body": "LGTM with nits — ship after CI green.",
                    "submitted_at": _iso(item["pr_updated"] - timedelta(hours=4)),
                },
            ]
        prs.append(pr)
        if link in ("title_ref", "body_closes", "issue_field_only"):
            iss["github_pr_number"] = pr_num
        append_commits_for_pr(
            repo,
            author,
            pr_num,
            item["pr_created"],
            item["last_commit"],
            ident,
        )
        pr_num += 1

    for pl in bundle.issue_plans:
        if pl.shadow_pr_global_index is None:
            continue
        slot = pl.shadow_pr_global_index
        if slot < len(orphan_pr_numbers):
            lix = pl.issue_index
            n = orphan_pr_numbers[slot]
            linear_issues[lix]["github_pr_number"] = n
            desc = linear_issues[lix].get("description") or ""
            linear_issues[lix]["description"] = f"{desc}\n\nTracked in PR #{n} on GitHub."

    fpad = 0
    while len(prs) < sc.TARGET_PRS - 2:
        repo = repos[fpad % len(repos)]
        author = gh_users[fpad % len(gh_users)]
        created = t0 + timedelta(days=10 + (fpad % 80), hours=fpad % 12)
        updated = created + timedelta(days=3)
        pr = {
            "id": 710000 + fpad,
            "number": pr_num,
            "node_id": f"PR_fill_{fpad}",
            "title": "chore: filler PR without ticket reference",
            "body": "",
            "state": "open" if fpad % 4 == 0 else "closed",
            "draft": False,
            "user": gh_user_blob(author),
            "html_url": f"https://github.com/{repo['full_name']}/pull/{pr_num}",
            "created_at": _iso(created),
            "updated_at": _iso(updated),
            "closed_at": _iso(updated + timedelta(days=1)) if fpad % 4 != 0 else None,
            "merged_at": _iso(updated + timedelta(days=1)) if fpad % 4 != 0 else None,
            "base": {
                "ref": repo["default_branch"],
                "sha": f"base{pr_num:04x}",
                "repo": {"id": repo["id"], "full_name": repo["full_name"]},
            },
            "head": {"ref": f"feature/fill-{pr_num}", "sha": f"head{pr_num:04x}"},
            "_repo_full": repo["full_name"],
            "_pr_num": pr_num,
            "metadata": {"scenario": "filler_untracked", "link_style": "none"},
        }
        prs.append(pr)
        append_commits_for_pr(repo, author, pr_num, created, updated, "filler")
        pr_num += 1
        fpad += 1

    # Fill remaining commits on default branch
    while c_idx < sc.TARGET_COMMITS:
        repo = repos[c_idx % len(repos)]
        author = gh_users[c_idx % len(gh_users)]
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
                "user": gh_user_blob(gh_users[g % len(gh_users)]),
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
                    "user": gh_user_blob(gh_users[0]),
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
        "users": {u["login"]: u for u in gh_users},
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
    """Synthetic Slack — eng drift + PM ping + execution-story extras."""
    del end
    bundle = linear_pkg.get("_execution_bundle")
    out: list[dict[str, Any]] = [
        {
            "id": _u(seed, "slack", "1"),
            "channel": "#eng-random",
            "text": "We should fix the cache invalidation thing ASAP",
            "ts": _iso(t0 + timedelta(days=4, hours=3)),
            "user_email": "alex.kim@nexora.dev",
            "linear_issue_id": None,
            "pattern": "discussion_drift",
            "metadata": {"scenario": "discussion_drift"},
        },
        {
            "id": _u(seed, "slack", "2"),
            "channel": "#product-web",
            "text": (
                "Can someone drop the NEX-* link for the rollout? "
                "Victoire asked in the customer channel and I only have the GH PR."
            ),
            "ts": _iso(t0 + timedelta(days=5, hours=1)),
            "user_email": "design@nexora.dev",
            "linear_issue_id": None,
            "pattern": "cross_tool_ping",
            "metadata": {"scenario": "cross_tool_ping"},
        },
    ]
    if bundle:
        for si, raw in enumerate(bundle.extra_slack):
            anchor = raw.get("anchor")
            if isinstance(anchor, datetime):
                ts_dt = anchor + timedelta(days=float(raw.get("ts_offset_days", 0)))
            else:
                ts_dt = t0 + timedelta(days=6 + si)
            row = {
                "id": _u(seed, "slack", "story", str(si)),
                "channel": raw["channel"],
                "text": raw["text"],
                "ts": _iso(ts_dt),
                "user_email": raw.get("user_email", ""),
                "linear_issue_id": raw.get("linear_issue_id"),
                "pattern": raw.get("pattern", "story"),
                "metadata": raw.get("metadata", {}),
            }
            out.append(row)
    return out


def _build_edges(
    linear_pkg: dict[str, Any], gh_pkg: dict[str, Any], users: list[dict[str, Any]]
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for rel in linear_pkg["issueRelations"]:
        src = rel["issue"]["id"]
        tgt = rel["relatedIssue"]["id"]
        edges.append({"from": src, "to": tgt, "kind": rel["type"]})
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


def _build_notion(
    seed: int,
    users: list[dict[str, Any]],
    linear_pkg: dict[str, Any],
    slack_events: list[dict[str, Any]],
    t0: datetime,
    end: datetime,
) -> dict[str, Any]:
    del t0, end
    pages: list[dict[str, Any]] = []
    issues = linear_pkg.get("issues", [])
    comments = linear_pkg.get("comments", [])
    for i, issue in enumerate(issues[:24]):
        owner = users[i % len(users)]
        title = f"{issue.get('identifier', 'NEX')} - {issue.get('title', 'Execution note')}"
        snippet = (
            f"Spec sync for {issue.get('project', {}).get('name', 'core')}. "
            f"Status: {issue.get('state', {}).get('name', 'unknown')}. "
            f"Track in {issue.get('identifier', 'NEX')} and related PRs."
        )
        edited = issue.get("updatedAt")
        pages.append(
            {
                "id": _u(seed, "notion", "page", str(i)),
                "url": f"https://www.notion.so/nexora/{_u(seed, 'notion-url', str(i)).replace('-', '')}",
                "title": title,
                "owner": owner.get("name") or owner.get("login"),
                "last_edited_time": edited if isinstance(edited, str) else _iso(datetime.now(tz=UTC)),
                "snippet": snippet,
            }
        )
    for j, ev in enumerate(slack_events[:8]):
        title = f"Slack follow-up {j + 1}: {ev.get('channel', '#channel')}"
        pages.append(
            {
                "id": _u(seed, "notion", "slack-page", str(j)),
                "url": f"https://www.notion.so/nexora/{_u(seed, 'notion-slack', str(j)).replace('-', '')}",
                "title": title,
                "owner": ev.get("user_email") or "team@nexora.dev",
                "last_edited_time": ev.get("ts") if isinstance(ev.get("ts"), str) else _iso(datetime.now(tz=UTC)),
                "snippet": f"Thread summary: {str(ev.get('text', ''))[:180]}",
            }
        )
    return {
        "search_result_count": len(pages),
        "has_more": len(pages) > 20,
        "users_me_ok": True,
        "sampled_pages": pages[:30],
        "source_counts": {"issues": min(len(issues), 24), "slack": min(len(slack_events), 8), "comments": len(comments)},
    }


def _build_calls(
    seed: int,
    users: list[dict[str, Any]],
    linear_pkg: dict[str, Any],
    slack_events: list[dict[str, Any]],
    t0: datetime,
    end: datetime,
) -> dict[str, Any]:
    del end
    calendars = [
        {"id": "eng-team@nexora.dev", "summary": "Engineering Team"},
        {"id": "product-sync@nexora.dev", "summary": "Product Sync"},
        {"id": "incident@nexora.dev", "summary": "Incident"},
    ]
    issues = linear_pkg.get("issues", [])
    events: list[dict[str, Any]] = []
    for i, issue in enumerate(issues[:18]):
        cal = calendars[i % len(calendars)]
        owner = users[(i + 2) % len(users)]
        start = datetime.fromisoformat(str(issue.get("createdAt", _iso(t0))).replace("Z", "+00:00")) + timedelta(days=1)
        end_dt = start + timedelta(minutes=45 + (i % 3) * 15)
        events.append(
            {
                "calendar_id": cal["id"],
                "id": _u(seed, "calls", "event", str(i)),
                "summary": f"{issue.get('identifier', 'NEX')} discussion - {issue.get('title', 'Execution topic')}",
                "description": (
                    f"Agenda: blockers, ownership, and follow-up for {issue.get('identifier', 'NEX')}. "
                    "Capture next actions and links to issue/PR."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/{_u(seed, 'meet', str(i))[:10]}",
                "organizer_email": owner.get("email") or "manager@nexora.dev",
                "created": _iso(start - timedelta(hours=6)),
                "updated": _iso(start - timedelta(hours=2)),
                "start": _iso(start),
                "end": _iso(end_dt),
            }
        )
    for j, ev in enumerate(slack_events[:6]):
        start = datetime.fromisoformat(str(ev.get("ts", _iso(t0))).replace("Z", "+00:00")) + timedelta(hours=4)
        events.append(
            {
                "calendar_id": calendars[j % len(calendars)]["id"],
                "id": _u(seed, "calls", "slack-followup", str(j)),
                "summary": f"Follow-up on {ev.get('channel', '#discussion')}",
                "description": str(ev.get("text", ""))[:200],
                "status": "confirmed",
                "html_link": f"https://meet.google.com/{_u(seed, 'meet-slack', str(j))[:10]}",
                "organizer_email": str(ev.get("user_email") or "team@nexora.dev"),
                "created": _iso(start - timedelta(hours=3)),
                "updated": _iso(start - timedelta(hours=1)),
                "start": _iso(start),
                "end": _iso(start + timedelta(minutes=30)),
            }
        )
    sampled_calendar_events: list[dict[str, Any]] = []
    for cal in calendars:
        per_cal = [e for e in events if e["calendar_id"] == cal["id"]]
        sampled_calendar_events.append(
            {"calendar_id": cal["id"], "event_count": len(per_cal), "has_more": len(per_cal) > 50}
        )
    return {
        "calendar_count": len(calendars),
        "has_more": False,
        "sampled_calendar_events": sampled_calendar_events,
        "sampled_events": events[:30],
    }


def _verify_patterns(
    linear_pkg: dict[str, Any],
    gh_pkg: dict[str, Any],
    slack_events: list[dict[str, Any]],
) -> list[str]:
    """Document which graph patterns the generator is designed to satisfy (§11)."""
    found: set[str] = {
        "cross_tool_dependency",
        "review_bottleneck",
        "untracked_work",
        "misaligned_completion",
        "cross_team_dependency",
        "duplicate_work",
        "stale_epic",
        "discussion_drift",
        "cross_tool_ping",
        "abandoned_branch",
        "multi_repo_change",
    }
    for iss in linear_pkg.get("issues", []):
        scn = (iss.get("metadata") or {}).get("scenario")
        if scn:
            found.add(str(scn))
    for pr in gh_pkg.get("pull_requests", []):
        scn = (pr.get("metadata") or {}).get("scenario")
        if scn:
            found.add(str(scn))
    for e in slack_events:
        pat = e.get("pattern")
        if pat:
            found.add(str(pat))
        sm = (e.get("metadata") or {}).get("scenario")
        if sm:
            found.add(str(sm))
    return sorted(found)
