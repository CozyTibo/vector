"""Cross-tool execution chaos for local mock data — contradictions, gaps, messy humans.

Not for production. Mutates Linear/GitHub/Slack/Notion/calls payloads in place.
"""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from mock_connectors.fixtures import seed_config as sc

# Fixed issue indices (0-based) → NEX-{i+1}. Kept away from MI golden slots (104, 199–209, 299).
IDX_MISALIGN = 13  # NEX-14
IDX_FAKE_PROGRESS = 51  # NEX-52
IDX_OWNERSHIP = 71  # NEX-72
IDX_BLOCKED_SILENT = 94  # NEX-95
IDX_PRIORITY = 88  # NEX-89
IDX_REVIEW_STUCK = 29  # NEX-30
IDX_SCOPE_DRIFT = 112  # NEX-113
IDX_MULTI_SOURCE = 76  # NEX-77
IDX_TEMPORAL = 118  # NEX-119


def _u(seed: int, *parts: str) -> str:
    h = hashlib.sha256((f"{seed}:chaos:" + ":".join(parts)).encode()).hexdigest()
    b = h[:32]
    return f"{b[:8]}-{b[8:12]}-{b[12:16]}-{b[16:20]}-{b[20:32]}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _user_blob(users: list[dict[str, Any]], login: str) -> dict[str, Any] | None:
    for u in users:
        if u.get("login") == login:
            return {
                "id": u["linear_user_id"],
                "name": (u.get("name") or "").strip() or login,
                "displayName": (u.get("linear_display_name") or u.get("name") or login).split()[0],
                "email": u.get("email") or "",
            }
    return None


def _append_comment(
    comments: list[dict[str, Any]],
    *,
    seed: int,
    seq: int,
    issue_id: str,
    ident: str,
    body: str,
    at: datetime,
    user: dict[str, Any],
    chaos_tags: list[str],
) -> None:
    comments.append(
        {
            "id": _u(seed, "chaos-cmt", str(seq)),
            "body": body,
            "createdAt": _iso(at),
            "updatedAt": _iso(at),
            "user": user,
            "issueId": issue_id,
            "issue": {"id": issue_id, "identifier": ident},
            "metadata": {"chaos_tags": chaos_tags},
        }
    )


def apply_execution_chaos(
    seed: int,
    t0: datetime,
    _end: datetime,
    users: list[dict[str, Any]],
    linear_pkg: dict[str, Any],
    gh_pkg: dict[str, Any],
    slack_events: list[dict[str, Any]],
    notion_pkg: dict[str, Any],
    calls_pkg: dict[str, Any],
) -> list[str]:
    """Inject messy coordination narratives. Returns tags for pattern_coverage."""
    rng = random.Random(seed + 90210)
    tags: list[str] = []
    issues: list[dict[str, Any]] = list(linear_pkg.get("issues") or [])
    comments: list[dict[str, Any]] = list(linear_pkg.get("comments") or [])

    c_seq = 900000

    def add_slack(
        ch: str,
        text: str,
        ts: datetime,
        email: str,
        *,
        linear_id: str | None = None,
        pattern: str,
        chaos: list[str],
    ) -> None:
        slack_events.append(
            {
                "id": _u(seed, "slack-chaos", str(len(slack_events))),
                "channel": ch,
                "text": text,
                "ts": _iso(ts),
                "user_email": email,
                "linear_issue_id": linear_id,
                "pattern": pattern,
                "metadata": {"chaos_tags": chaos, "scenario": pattern},
            }
        )

    # --- 1. Misaligned execution (Slack done vs Linear vs PR) ---
    if len(issues) > IDX_MISALIGN:
        iss = issues[IDX_MISALIGN]
        ident = str(iss.get("identifier") or f"{sc.LINEAR_KEY_PREFIX}-{IDX_MISALIGN + 1}")
        iid = str(iss.get("id") or "")
        st = iss.get("state") or {}
        if isinstance(st, dict):
            st["name"] = "In Progress"
            st["type"] = "started"
            iss["state"] = st
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = list(dict.fromkeys([*(meta.get("chaos_tags") or []), "misaligned_execution"]))
        iss["metadata"] = meta

        add_slack(
            "#eng-core",
            f"🎉 {ident} is done — shipped to prodution yesterday, customer unblocked",
            t0 + timedelta(days=2, hours=4),
            "sam.rivera@nexora.dev",
            linear_id=iid or None,
            pattern="chaos_misaligned_slack_done",
            chaos=["misaligned_execution"],
        )
        add_slack(
            "#product-web",
            f"wait what — {ident} still shows In Progress in Linear? and the spec page says MySQL but we're on Postgres in code 😅",
            t0 + timedelta(days=2, hours=7),
            "design@nexora.dev",
            linear_id=None,
            pattern="chaos_misaligned_spec",
            chaos=["misaligned_execution", "cross_tool_inconsistency"],
        )
        add_slack(
            "#eng-core",
            "not sure what's going on with that thread — maybe related to auth?",
            t0 + timedelta(days=2, hours=8),
            "alex.kim@nexora.dev",
            pattern="chaos_human_ambiguity",
            chaos=["human_ambiguity"],
        )
        pr_num = iss.get("github_pr_number")
        if isinstance(pr_num, int):
            for pr in gh_pkg.get("pull_requests") or []:
                if not isinstance(pr, dict):
                    continue
                if pr.get("number") == pr_num:
                    pr["state"] = "open"
                    pr["draft"] = True
                    pr["merged_at"] = None
                    pr["closed_at"] = None
                    body = str(pr.get("body") or "")
                    pr["body"] = (
                        body
                        + "\n\n<!-- CI 🔴 -->\n"
                        "checks failing silently in GH — no one commented yet. "
                        "Draft because we're 'almost there' for 4 days.\n"
                    )
                    pmd = dict(pr.get("metadata") or {})
                    pmd["chaos_tags"] = ["misaligned_execution", "fake_progress"]
                    pr["metadata"] = pmd
                    break
        tags.extend(["misaligned_execution", "cross_tool_inconsistency"])

    # --- 2. Shadow work (Slack / PR with no ticket trail) ---
    add_slack(
        "#eng-random",
        "pushed a quick fix lol — on my laptop only, no ticket, will backfill *eventually*",
        t0 + timedelta(days=6, hours=2),
        "jordan.lee@nexora.dev",
        pattern="chaos_shadow_slack",
        chaos=["shadow_work"],
    )
    add_slack(
        "#eng-random",
        "fixed locally on branch `hotfix/cache` — not linked to anything sorry 🙃",
        t0 + timedelta(days=6, hours=3),
        "morgan.blake@nexora.dev",
        pattern="chaos_shadow_local",
        chaos=["shadow_work", "missing_ownership"],
    )
    tags.append("shadow_work")

    # --- 3. Fake progress (comments + issue bumps) ---
    if len(issues) > IDX_FAKE_PROGRESS:
        iss = issues[IDX_FAKE_PROGRESS]
        iid = str(iss.get("id") or "")
        ident = str(iss.get("identifier") or "")
        u_eng = _user_blob(users, "akim")
        u_pm = _user_blob(users, "vcharlet")
        if u_eng:
            base = datetime.fromisoformat(str(iss.get("createdAt", _iso(t0))).replace("Z", "+00:00"))
            for day, line in [
                (1, "almost there — just one last thing on my side"),
                (4, "almost there still 😅 one more blokcer in CI"),
                (9, "just one last thing™ — pinged platform again"),
            ]:
                _append_comment(
                    comments,
                    seed=seed,
                    seq=c_seq,
                    issue_id=iid,
                    ident=ident,
                    body=line,
                    at=base + timedelta(days=day, hours=rng.randint(1, 8)),
                    user=u_eng,
                    chaos_tags=["fake_progress", "stale_information"],
                )
                c_seq += 1
        if u_pm:
            base = datetime.fromisoformat(str(iss.get("createdAt", _iso(t0))).replace("Z", "+00:00"))
            _append_comment(
                comments,
                seed=seed,
                seq=c_seq,
                issue_id=iid,
                ident=ident,
                body="Acme is waiting on this — we need this today or renewal gets shaky",
                at=base + timedelta(days=3),
                user=u_pm,
                chaos_tags=["customer_pressure", "priority_conflict"],
            )
            c_seq += 1
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = list(dict.fromkeys([*(meta.get("chaos_tags") or []), "fake_progress"]))
        iss["metadata"] = meta
        # Bump updatedAt without state change
        ua = datetime.fromisoformat(str(iss.get("updatedAt", _iso(t0))).replace("Z", "+00:00"))
        iss["updatedAt"] = _iso(ua + timedelta(hours=2))
        tags.append("fake_progress")

    # --- 4. Ownership confusion ---
    if len(issues) > IDX_OWNERSHIP:
        iss = issues[IDX_OWNERSHIP]
        iss["assignee"] = None
        iid = str(iss.get("id") or "")
        ident = str(iss.get("identifier") or "")
        for login, line, day in [
            ("tmoss", "who owns this? I thought platform was picking it up", 2),
            ("rchen", "is this on me or PLAT? cc @channel", 3),
            ("scollins", "Can someone claim ownership — customer thread is heating up", 5),
        ]:
            u = _user_blob(users, login)
            if u:
                base = datetime.fromisoformat(str(iss.get("createdAt", _iso(t0))).replace("Z", "+00:00"))
                _append_comment(
                    comments,
                    seed=seed,
                    seq=c_seq,
                    issue_id=iid,
                    ident=ident,
                    body=line,
                    at=base + timedelta(days=day),
                    user=u,
                    chaos_tags=["ownership_confusion", "missing_ownership"],
                )
                c_seq += 1
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = ["ownership_confusion"]
        iss["metadata"] = meta
        tags.append("ownership_confusion")

    # --- 5. Blocked but silent ---
    if len(issues) > IDX_BLOCKED_SILENT:
        iss = issues[IDX_BLOCKED_SILENT]
        ident = str(iss.get("identifier") or "")
        iid = str(iss.get("id") or "")
        pr_num = iss.get("github_pr_number")
        if isinstance(pr_num, int):
            for pr in gh_pkg.get("pull_requests") or []:
                if isinstance(pr, dict) and pr.get("number") == pr_num:
                    pr["body"] = (
                        str(pr.get("body") or "")
                        + "\n\nCI red on contract_tests — no thread follow-up\n"
                    )
                    break
        add_slack(
            "#eng-core",
            f"👀 pretty sure {ident} PR is red — anyone looking? not sure what's going on",
            t0 + timedelta(days=8, hours=1),
            "riley.chen@nexora.dev",
            pattern="chaos_blocked_silent",
            chaos=["blocked_but_silent"],
        )
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = ["blocked_but_silent"]
        iss["metadata"] = meta
        tags.append("blocked_but_silent")

    # --- 6. Priority conflict ---
    add_slack(
        "#customer-success",
        "🔥 Sales promised CSV export for Acme THIS WEEK — we need this today",
        t0 + timedelta(days=1, hours=9),
        "victoire.charlet@edu.escp.eu",
        pattern="chaos_pm_urgency",
        chaos=["priority_conflict", "customer_pressure"],
    )
    add_slack(
        "#eng-core",
        "gonna be honest this is not priority for me right now — infra fire drill",
        t0 + timedelta(days=1, hours=11),
        "taylor.moss@nexora.dev",
        pattern="chaos_eng_pushback",
        chaos=["priority_conflict", "contradiction"],
    )
    if len(issues) > IDX_PRIORITY:
        iss = issues[IDX_PRIORITY]
        other = issues[(IDX_PRIORITY + 17) % len(issues)]
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = ["priority_conflict"]
        meta["note"] = "Lower activity here while sibling issue hots — ambiguous triage"
        iss["metadata"] = meta
        meta_o = dict(other.get("metadata") or {})
        meta_o["chaos_tags"] = list(dict.fromkeys([*(meta_o.get("chaos_tags") or []), "priority_competition"]))
        other["metadata"] = meta_o
    tags.append("priority_conflict")

    # --- 7. Review bottleneck ---
    if len(issues) > IDX_REVIEW_STUCK:
        iss = issues[IDX_REVIEW_STUCK]
        pr_num = iss.get("github_pr_number")
        if isinstance(pr_num, int):
            for pr in gh_pkg.get("pull_requests") or []:
                if isinstance(pr, dict) and pr.get("number") == pr_num:
                    pr["state"] = "open"
                    pr["merged_at"] = None
                    pr["body"] = (
                        str(pr.get("body") or "")
                        + "\n\n@scollins LGTM from last week — still waiting on second reviewer? "
                        "requested changes from WEB and no follow-up 🚨"
                    )
                    pmd = dict(pr.get("metadata") or {})
                    pmd["chaos_tags"] = ["review_bottleneck"]
                    pr["metadata"] = pmd
                    break
        tags.append("review_bottleneck_chaos")

    # --- 8. Cross-team dependency break ---
    add_slack(
        "#eng-core",
        "blocked on platform for rate limit knob — nex-105 vs NEX-105 vs Nex-105 in threads 😵‍💫",
        t0 + timedelta(days=5, hours=2),
        "thibault.hagler@gmail.com",
        pattern="chaos_cross_team_typo",
        chaos=["cross_team_dependency", "data_hygiene"],
    )
    add_slack(
        "#eng-core",
        "still waiting on platform — no ticket on their board afaict",
        t0 + timedelta(days=5, hours=6),
        "alex.kim@nexora.dev",
        pattern="chaos_waiting_platform",
        chaos=["cross_team_dependency", "missing_ownership"],
    )
    tags.extend(["cross_team_dependency", "data_hygiene"])

    # --- 9. Incident chaos (Slack war room, no Linear issue) ---
    base_inc = t0 + timedelta(days=11, hours=10)
    war = [
        "🚨 sev-ish: checkout API spiking — war room here",
        "maybe related to auth? not sure",
        "could be redis. could be deploy. could be sunspots",
        "this again... we already fixed this last week",
        "👍 rolling back canary — someone write this up? (no ticket yet)",
    ]
    for i, txt in enumerate(war):
        add_slack(
            "#incident-war-room",
            txt,
            base_inc + timedelta(minutes=15 * i),
            ["alex.kim@nexora.dev", "sam.rivera@nexora.dev", "thibault.hagler@gmail.com"][i % 3],
            pattern="chaos_incident_warroom",
            chaos=["incident_chaos", "missing_ownership"],
        )
    tags.append("incident_chaos")

    # --- 10. Scope drift ---
    if len(issues) > IDX_SCOPE_DRIFT:
        iss = issues[IDX_SCOPE_DRIFT]
        iid = str(iss.get("id") or "")
        ident = str(iss.get("identifier") or "")
        u = _user_blob(users, "vcharlet")
        if u:
            base = datetime.fromisoformat(str(iss.get("createdAt", _iso(t0))).replace("Z", "+00:00"))
            _append_comment(
                comments,
                seed=seed,
                seq=c_seq,
                issue_id=iid,
                ident=ident,
                body=(
                    "Actually Legal wants **bulk admin delete** too now — same ticket? "
                    "no re-estimate from me sorry, customer escalated"
                ),
                at=base + timedelta(days=6),
                user=u,
                chaos_tags=["scope_drift", "customer_pressure"],
            )
            c_seq += 1
        desc = str(iss.get("description") or "")
        iss["description"] = desc + "\n\n<!-- scope creep: see thread -->"
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = ["scope_drift"]
        iss["metadata"] = meta
        tags.append("scope_drift")

    # --- 11. Duplicate + hygiene slack ---
    dup_txt = "hey can someone look at the webhook retries for Bluecrest — customer is blocked"
    add_slack("#customer-success", dup_txt, t0 + timedelta(days=7, hours=1), "support@nexora.dev", pattern="chaos_dup_a", chaos=["data_hygiene"])
    add_slack("#customer-success", dup_txt, t0 + timedelta(days=7, hours=1, minutes=3), "support@nexora.dev", pattern="chaos_dup_b", chaos=["data_hygiene", "duplicate_message"])

    # --- 12. Multi-source narrative (NEX-77) ---
    if len(issues) > IDX_MULTI_SOURCE:
        iss = issues[IDX_MULTI_SOURCE]
        ident = str(iss.get("identifier") or "NEX-77")
        iid = str(iss.get("id") or "")
        u = _user_blob(users, "srivera")
        if u:
            base = datetime.fromisoformat(str(iss.get("createdAt", _iso(t0))).replace("Z", "+00:00"))
            _append_comment(
                comments,
                seed=seed,
                seq=c_seq,
                issue_id=iid,
                ident=ident,
                body="Implementation is GraphQL batching — ignore the Notion spec that still says REST only",
                at=base + timedelta(days=4),
                user=u,
                chaos_tags=["multi_source_narrative", "contradiction"],
            )
            c_seq += 1
        meta = dict(iss.get("metadata") or {})
        meta["chaos_tags"] = ["multi_source_narrative"]
        iss["metadata"] = meta
    tags.append("multi_source_narrative")

    # --- 13. Temporal inconsistency ---
    if len(issues) > IDX_TEMPORAL and len(issues) > IDX_MISALIGN:
        # Meeting "before" issue existed (synthetic)
        early = t0 - timedelta(days=2)
        evl = calls_pkg.setdefault("sampled_events", [])
        if isinstance(evl, list):
            evl.append(
                {
                    "calendar_id": "product-sync@nexora.dev",
                    "id": _u(seed, "chaos-call-early"),
                    "summary": "Pre-mortem: export pipeline (no ticket yet)",
                    "description": "We talked about export risks before NEX-119 existed — notes only here.",
                    "status": "confirmed",
                    "html_link": f"https://meet.google.com/early-{seed % 10000:04d}",
                    "organizer_email": "victoire.charlet@edu.escp.eu",
                    "created": _iso(early),
                    "updated": _iso(early + timedelta(hours=1)),
                    "start": _iso(early + timedelta(hours=2)),
                    "end": _iso(early + timedelta(hours=2, minutes=30)),
                    "metadata": {"chaos_tags": ["temporal_inconsistency"]},
                }
            )
        # PR updated after issue marked done — pick healthy_delivery index 299 if exists
        if len(issues) > 299:
            done_iss = issues[299]
            if str((done_iss.get("metadata") or {}).get("scenario")) == "healthy_delivery":
                dn = done_iss.get("github_pr_number")
                if isinstance(dn, int):
                    for pr in gh_pkg.get("pull_requests") or []:
                        if isinstance(pr, dict) and pr.get("number") == dn:
                            pr["updated_at"] = _iso(
                                datetime.fromisoformat(
                                    str(done_iss.get("updatedAt", _iso(t0))).replace("Z", "+00:00")
                                )
                                + timedelta(days=2)
                            )
                            pmd = dict(pr.get("metadata") or {})
                            pmd["chaos_tags"] = list(
                                dict.fromkeys([*(pmd.get("chaos_tags") or []), "temporal_inconsistency"])
                            )
                            pr["metadata"] = pmd
                            break
    tags.append("temporal_inconsistency")

    linear_pkg["comments"] = comments
    linear_pkg["issues"] = issues

    # --- Notion databases (structured + mismatched vs Linear) ---
    _build_chaos_notion_databases(seed, t0, users, issues, notion_pkg, rng)

    return sorted(set(tags))


def _build_chaos_notion_databases(
    seed: int,
    t0: datetime,
    users: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    notion_pkg: dict[str, Any],
    rng: random.Random,
) -> None:
    """Add TODO / specs / incident DBs with intentional drift from Linear."""
    mis = issues[IDX_MISALIGN] if len(issues) > IDX_MISALIGN else None
    mis_ident = str(mis.get("identifier") or "NEX-14") if mis else "NEX-14"
    mis_state = str((mis or {}).get("state", {}).get("name") or "In Progress")

    todo_rows: list[dict[str, Any]] = [
        {
            "id": _u(seed, "db-todo", "1"),
            "title": "Customer export hardening",
            "column": "done",
            "linear_identifier": mis_ident,
            "linear_truth": mis_state,
            "mismatch": f"Notion says **done** but Linear is **{mis_state}**",
            "chaos_tags": ["misaligned_execution", "notion_database"],
        },
        {
            "id": _u(seed, "db-todo", "2"),
            "title": "Webhook retry backoff",
            "column": "doing",
            "linear_identifier": "NEX-52",
            "linear_truth": "In Progress",
            "mismatch": "Board says doing; Slack says 'almost there' for a week",
            "chaos_tags": ["fake_progress", "notion_database"],
        },
        {
            "id": _u(seed, "db-todo", "3"),
            "title": "Mystery hotfix (no ticket)",
            "column": "doing",
            "linear_identifier": None,
            "linear_truth": None,
            "mismatch": "Shadow work — only exists in Slack",
            "chaos_tags": ["shadow_work", "notion_database"],
        },
    ]

    spec_rows: list[dict[str, Any]] = [
        {
            "id": _u(seed, "db-spec", "1"),
            "title": "PRD: Export API v1",
            "status": "Approved",
            "spec_says": "Use MySQL read replica for export cursor; REST pagination only",
            "implementation_truth": "Team shipped Postgres + GraphQL batching — spec never updated",
            "last_reviewed": _iso(t0 - timedelta(days=60)),
            "chaos_tags": ["misaligned_execution", "stale_information", "notion_database"],
        },
        {
            "id": _u(seed, "db-spec", "2"),
            "title": "Feature: Org switcher",
            "status": "Draft",
            "spec_says": "Single org per session",
            "implementation_truth": "Multi-org already in prod behind flag",
            "last_reviewed": _iso(t0 - timedelta(days=120)),
            "chaos_tags": ["stale_information", "notion_database"],
        },
    ]

    inc_rows: list[dict[str, Any]] = [
        {
            "id": _u(seed, "db-inc", "1"),
            "title": "2025-10-12 checkout spikes",
            "summary": "Hypotheses: redis, deploy, auth — **no Linear incident** created",
            "linked_issue": None,
            "chaos_tags": ["incident_chaos", "notion_database"],
        },
        {
            "id": _u(seed, "db-inc", "2"),
            "title": "Sev-ish notes (informal)",
            "summary": "War room in Slack only; this page copied from thread",
            "linked_issue": None,
            "chaos_tags": ["incident_chaos", "blocked_but_silent", "notion_database"],
        },
    ]

    notion_pkg["databases"] = {
        "todo_board": {
            "name": "Engineering TODO",
            "columns": ["backlog", "doing", "blocked", "done"],
            "rows": todo_rows,
        },
        "product_specs": {
            "name": "Product specs (canonical lol)",
            "rows": spec_rows,
        },
        "incident_notes": {
            "name": "Incident scratchpad",
            "rows": inc_rows,
        },
    }

    # Flatten into sampled_pages for legacy readers
    extra_pages: list[dict[str, Any]] = []
    for row in todo_rows:
        extra_pages.append(
            {
                "id": row["id"],
                "url": f"https://www.notion.so/nexora/{row['id'].replace('-', '')}",
                "title": f"[TODO / {row['column']}] {row['title']}",
                "owner": (
                    users[rng.randint(0, len(users) - 1)].get("name", "Team")
                    if users
                    else "Team"
                ),
                "last_edited_time": _iso(t0 + timedelta(days=rng.randint(1, 5))),
                "snippet": f"{row.get('mismatch', '')} | linear: {row.get('linear_identifier')}",
                "metadata": {"chaos_tags": row.get("chaos_tags", []), "database": "todo_board"},
            }
        )
    for row in spec_rows:
        extra_pages.append(
            {
                "id": row["id"],
                "url": f"https://www.notion.so/nexora/{row['id'].replace('-', '')}",
                "title": f"[SPEC] {row['title']}",
                "owner": "Victoire Charlet",
                "last_edited_time": row["last_reviewed"],
                "snippet": f"Spec: {row['spec_says'][:120]}… Reality: {row['implementation_truth'][:120]}",
                "metadata": {"chaos_tags": row.get("chaos_tags", []), "database": "product_specs"},
            }
        )
    for row in inc_rows:
        extra_pages.append(
            {
                "id": row["id"],
                "url": f"https://www.notion.so/nexora/{row['id'].replace('-', '')}",
                "title": f"[INCIDENT NOTE] {row['title']}",
                "owner": "oncall@nexora.dev",
                "last_edited_time": _iso(t0 + timedelta(days=3)),
                "snippet": row.get("summary", "")[:220],
                "metadata": {"chaos_tags": row.get("chaos_tags", []), "database": "incident_notes"},
            }
        )

    base_pages = notion_pkg.get("sampled_pages")
    if not isinstance(base_pages, list):
        base_pages = []
    # Prepend so bounded Step-1 payloads keep Notion DB rows (legacy path is sampled_pages[:30]).
    notion_pkg["sampled_pages"] = (extra_pages + base_pages)[:45]
    notion_pkg["search_result_count"] = len(notion_pkg["sampled_pages"])
    notion_pkg["has_more"] = len(notion_pkg["sampled_pages"]) > 30
    sc_slack = notion_pkg.get("source_counts")
    if isinstance(sc_slack, dict):
        sc_slack["notion_databases"] = len(extra_pages)
        notion_pkg["source_counts"] = sc_slack
