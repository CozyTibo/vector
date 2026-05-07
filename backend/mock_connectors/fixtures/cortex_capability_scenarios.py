"""Story-driven mock overlays for Cortex capability validation (local dev / ingestion demos).

Dominant cross-tool threads (blocked release, billing retry noise, fragmented parallel work,
healthy delivery control path, untracked deploy risk) so organizational cognition scenarios
have realistic evidence density—not an evenly distributed toy dataset.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from mock_connectors.fixtures.execution_stories import (
    ExecutionBundle,
    PRSpec,
)

# Linear identifiers use index+1 → NEX-105 is issue index 104, NEX-201..NEX-210 are 200..209.
IDX_NEX_105 = 104
IDX_FRAGMENT_START = 200
IDX_FRAGMENT_END = 210  # exclusive → NEX-201..NEX-210
IDX_NEX_300 = 299


def _u(seed: int, *parts: str) -> str:
    h = hashlib.sha256((f"{seed}:cc:" + ":".join(parts)).encode()).hexdigest()
    b = h[:32]
    return f"{b[:8]}-{b[8:12]}-{b[12:16]}-{b[16:20]}-{b[20:32]}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_blocked_release(bundle: ExecutionBundle) -> None:
    """Scenario 1: NEX-105 release blocked on InfoSec; no PR; dominant comms tokens."""
    p105 = bundle.issue_plans[IDX_NEX_105]
    p105.pr = None
    p105.state_name = "In Progress"
    p105.story_slug = "blocked_release"
    p105.metadata = {"scenario": "blocked_release"}
    p105.updated_at = p105.created_at + timedelta(days=14)

    anchor105 = bundle.issue_plans[IDX_NEX_105].created_at
    texts_105 = [
        (
            "Release train: NEX-105 is blocked — waiting on InfoSec approval "
            "for outbound domain allowlist."
        ),
        "Ping on NEX-105: still no owner on InfoSec approval; outbound domain is the gate.",
        (
            "NEX-105 cannot ship until InfoSec approval clears; "
            "who is driving the InfoSec approval thread?"
        ),
        "Customer escalation references NEX-105; InfoSec approval still pending — blocked.",
    ]
    for si, txt in enumerate(texts_105):
        bundle.extra_slack.append(
            {
                "channel": "#release-war-room",
                "text": txt,
                "ts_offset_days": float(2 + si * 2),
                "anchor": anchor105,
                "user_email": "thibault.hagler@gmail.com",
                "linear_issue_id": None,
                "pattern": "blocked_release",
                "metadata": {"scenario": "blocked_release"},
            }
        )


def build_discussion_without_work(bundle: ExecutionBundle) -> None:
    """Scenario 2: billing retry / retry logic / retry system — no Linear link in Slack extras."""
    anchor_bill = bundle.issue_plans[IDX_NEX_105].created_at + timedelta(days=7)
    billing_msgs = [
        (
            "We should fix the billing retry logic before next invoice run — "
            "seeing timeouts in retry system."
        ),
        (
            "Retry logic for billing keeps flaking; "
            "can we align on the billing retry approach this week?"
        ),
        "Customer thread: billing retry path looks unstable; retry system needs an owner.",
        "Another incident on billing retry — same retry logic issue as last sprint.",
    ]
    for bi, btxt in enumerate(billing_msgs):
        bundle.extra_slack.append(
            {
                "channel": "#eng-payments",
                "text": btxt,
                "ts_offset_days": float(1 + bi * 1.5),
                "anchor": anchor_bill,
                "user_email": "alex.kim@nexora.dev",
                "linear_issue_id": None,
                "pattern": "discussion_without_work",
                "metadata": {"scenario": "discussion_without_work"},
            }
        )


def build_fragmented_execution(bundle: ExecutionBundle) -> None:
    """Scenario 3: many active issues (NEX-201..NEX-210), different topics, PRs stripped."""
    for i in range(IDX_FRAGMENT_START, IDX_FRAGMENT_END):
        pl = bundle.issue_plans[i]
        pl.pr = None
        pl.state_name = "In Progress"
        pl.story_slug = "fragmented_parallel"
        prev = (pl.metadata or {}).get("scenario")
        pl.metadata = {
            **(pl.metadata or {}),
            "scenario": "fragmented_execution",
            "execution_story": prev or "initiative_soc2",
        }
        pl.updated_at = pl.created_at + timedelta(days=4 + (i % 5))


def build_healthy_delivery(bundle: ExecutionBundle) -> None:
    """Scenario 4: NEX-300 done with merged PR (body_closes)."""
    pl300 = bundle.issue_plans[IDX_NEX_300]
    ic = pl300.created_at
    pr_open = ic + timedelta(days=1, hours=6)
    merged = ic + timedelta(days=4)
    pl300.pr = PRSpec(
        repo_index=0,
        link_style="body_closes",
        created_offset_h=(pr_open - ic).total_seconds() / 3600.0,
        updated_offset_h=(merged - ic).total_seconds() / 3600.0 + 2.0,
        merged_offset_h=(merged - ic).total_seconds() / 3600.0,
        last_commit_offset_h=(merged - ic).total_seconds() / 3600.0 - 1.0,
    )
    pl300.state_name = "Done"
    pl300.story_slug = "healthy_delivery"
    pl300.metadata = {**(pl300.metadata or {}), "scenario": "healthy_delivery"}
    pl300.updated_at = merged + timedelta(days=1)


def build_untracked_blocker(_bundle: ExecutionBundle) -> None:
    """Scenario 5: contract-test deploy blocker lives only in calls (see extend_calls_package)."""


def patch_execution_bundle_for_cortex_capabilities(bundle: ExecutionBundle) -> None:
    """Mutate execution plans after PR budget trim: dominant failures + control path."""
    build_blocked_release(bundle)
    build_discussion_without_work(bundle)
    build_fragmented_execution(bundle)
    build_healthy_delivery(bundle)
    build_untracked_blocker(bundle)


def decorate_linear_issues_and_comments(
    issues: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    *,
    seed: int,
    users: list[dict[str, Any]],
) -> None:
    """Overwrite titles/descriptions and append blocker comments for scenario detection."""
    if len(issues) <= IDX_NEX_300:
        return

    u_eng = next((u for u in users if u.get("login") == "akim"), users[0] if users else None)
    if not u_eng:
        return

    blob = {
        "id": u_eng["linear_user_id"],
        "name": u_eng.get("name") or u_eng["login"],
        "displayName": (u_eng.get("name") or u_eng["login"]).split()[0],
        "email": u_eng["email"],
    }

    iss105 = issues[IDX_NEX_105]
    iss105["title"] = "NEX-105 — Release blocked on InfoSec outbound domain approval"
    iss105["description"] = (
        "Cannot release until InfoSec approves outbound domain allowlist for production.\n"
        "NEX-105 depends on InfoSec approval; no owner assigned for the security review.\n"
        "Status: blocked on external dependency (InfoSec)."
    )
    iss105["metadata"] = {**(iss105.get("metadata") or {}), "scenario": "blocked_release"}

    c105 = issues[IDX_NEX_105]["createdAt"].replace("Z", "+00:00")
    t105 = datetime.fromisoformat(c105) + timedelta(hours=30)
    comments.append(
        {
            "id": _u(seed, "cc-comment-nex105-blocker"),
            "body": (
                "Blocker: Cannot release until InfoSec approves outbound domain — "
                "NEX-105 is blocked with no InfoSec owner assigned."
            ),
            "createdAt": _iso(t105),
            "updatedAt": _iso(t105),
            "user": blob,
            "issueId": iss105["id"],
            "issue": {"id": iss105["id"], "identifier": iss105["identifier"]},
            "metadata": {"scenario": "blocked_release"},
        }
    )

    topics = [
        ("NEX-201", "metrics", "Telemetry batch export backlog"),
        ("NEX-202", "auth", "Session refresh edge cases"),
        ("NEX-203", "infra", "Canary rollout guardrails"),
        ("NEX-204", "data", "Warehouse compaction tuning"),
        ("NEX-205", "mobile", "Offline cache invalidation"),
        ("NEX-206", "web", "Command palette performance"),
        ("NEX-207", "api", "GraphQL pagination limits"),
        ("NEX-208", "platform", "Feature flag drift audit"),
        ("NEX-209", "integrations", "Partner webhook retries"),
        ("NEX-210", "core", "Idempotency key collision handling"),
    ]
    for i in range(IDX_FRAGMENT_START, IDX_FRAGMENT_END):
        ident, area, title_suffix = topics[i - IDX_FRAGMENT_START]
        issues[i]["title"] = f"{ident} — {area}: {title_suffix}"
        issues[i]["description"] = (
            f"{ident} is active work on {area}; low coupling to other NEX-20x items this week."
        )
        issues[i]["metadata"] = {
            **(issues[i].get("metadata") or {}),
            "scenario": "fragmented_execution",
            "execution_story": "initiative_soc2",
        }

    iss300 = issues[IDX_NEX_300]
    iss300["title"] = "NEX-300 — Ship billing reliability hardening (done)"
    iss300["description"] = (
        "Completed: merged PR closes NEX-300; production verified. "
        "Slack announcement posted in #eng-core."
    )
    iss300["metadata"] = {**(iss300.get("metadata") or {}), "scenario": "healthy_delivery"}


def extend_slack_events(
    slack_events: list[dict[str, Any]],
    *,
    seed: int,
    t0: datetime,
    linear_nex105_id: str | None,
) -> None:
    """Append dominant Slack lines (NEX-105 + billing); thread_ts must be unique."""
    base = t0 + timedelta(days=10)
    extra = [
        {
            "id": _u(seed, "cc-slack", "nex105-a"),
            "channel": "#incident-review",
            "text": "Incident notes tie back to NEX-105 — InfoSec approval still blocking release.",
            "ts": _iso(base + timedelta(hours=2)),
            "user_email": "victoire.charlet@edu.escp.eu",
            "linear_issue_id": linear_nex105_id,
            "pattern": "blocked_release",
            "metadata": {"scenario": "blocked_release"},
        },
        {
            "id": _u(seed, "cc-slack", "nex105-b"),
            "channel": "#customer-success",
            "text": (
                "Customer asks daily about NEX-105; InfoSec approval is the blocker — no owner."
            ),
            "ts": _iso(base + timedelta(days=1, hours=5)),
            "user_email": "design@nexora.dev",
            "linear_issue_id": linear_nex105_id,
            "pattern": "blocked_release",
            "metadata": {"scenario": "blocked_release"},
        },
    ]
    slack_events.extend(extra)


def extend_slack_cortex_capability_signals(
    slack_events: list[dict[str, Any]],
    *,
    seed: int,
    t0: datetime,
    linear_nex105_id: str | None,
) -> None:
    """Incident / rollback / decision vocabulary for organizational cognition scenarios."""
    base = t0 + timedelta(days=11)
    extra = [
        {
            "id": _u(seed, "cc-slack", "inc-pm"),
            "channel": "#incidents",
            "text": (
                "INC-2048 customer-visible errors traced to NEX-105 train slip — "
                "drafting postmortem; rollback plan is hold traffic + freeze promo flags "
                "until InfoSec approval lands."
            ),
            "ts": _iso(base + timedelta(hours=4)),
            "user_email": "manager@nexora.dev",
            "linear_issue_id": linear_nex105_id,
            "pattern": "incident_trace",
            "metadata": {"scenario": "incident_analysis", "cortex_lane": "incident_analysis"},
        },
        {
            "id": _u(seed, "cc-slack", "decision"),
            "channel": "#eng-leads",
            "text": (
                "Decision record: we will not bypass the outbound domain review — agreed to accept "
                "schedule slip vs. policy exception; link decision log in Notion."
            ),
            "ts": _iso(base + timedelta(days=1, hours=2)),
            "user_email": "thibault.hagler@gmail.com",
            "linear_issue_id": linear_nex105_id,
            "pattern": "decision_lineage",
            "metadata": {"scenario": "decision_lineage", "cortex_lane": "decision_lineage"},
        },
        {
            "id": _u(seed, "cc-slack", "init-alias"),
            "channel": "#product-web",
            "text": (
                "Initiative alias check: Northstar billing reliability in roadmap deck matches "
                "NEX-300 scope in Linear — keep naming consistent for exec readouts."
            ),
            "ts": _iso(t0 + timedelta(days=88, hours=2)),
            "user_email": "victoire.charlet@edu.escp.eu",
            "linear_issue_id": None,
            "pattern": "initiative_continuity",
            "metadata": {
                "scenario": "initiative_continuity",
                "cortex_lane": "initiative_continuity",
            },
        },
    ]
    slack_events.extend(extra)


def extend_calls_package(
    calls_pkg: dict[str, Any],
    *,
    seed: int,
    t0: datetime,
) -> None:
    """Scenario 1 (NEX-105), 2 (billing), 5 (contract tests) call transcripts."""
    sampled = calls_pkg.get("sampled_events")
    main_events = calls_pkg.get("events")
    if not isinstance(sampled, list):
        return
    base = t0 + timedelta(days=12)
    appended: list[dict[str, Any]] = [
        {
            "calendar_id": "release@nexora.dev",
            "id": _u(seed, "cc-call", "nex105-war"),
            "summary": "NEX-105 release readiness",
            "description": (
                "War room: NEX-105 is blocked on InfoSec approval for outbound domain; "
                "release is blocked until approval lands; still no owner for InfoSec thread."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-nex105-a-{seed % 10000:04d}",
            "organizer_email": "thibault.hagler@gmail.com",
            "created": _iso(base - timedelta(days=1, hours=2)),
            "updated": _iso(base - timedelta(hours=2)),
            "start": _iso(base - timedelta(days=1)),
            "end": _iso(base - timedelta(days=1) + timedelta(minutes=45)),
            "metadata": {"scenario": "blocked_release"},
        },
        {
            "calendar_id": "release@nexora.dev",
            "id": _u(seed, "cc-call", "nex105-infosec"),
            "summary": "InfoSec gate for NEX-105",
            "description": (
                "Discussion: InfoSec approval is the only blocker for NEX-105; "
                "team agrees outbound domain review is blocked without security sponsor."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-nex105-b-{seed % 10000:04d}",
            "organizer_email": "manager@nexora.dev",
            "created": _iso(base + timedelta(days=2) - timedelta(hours=3)),
            "updated": _iso(base + timedelta(days=2) - timedelta(hours=1)),
            "start": _iso(base + timedelta(days=2)),
            "end": _iso(base + timedelta(days=2) + timedelta(minutes=30)),
            "metadata": {"scenario": "blocked_release"},
        },
        {
            "calendar_id": "customer@nexora.dev",
            "id": _u(seed, "cc-call", "nex105-esc"),
            "summary": "Customer escalation — NEX-105",
            "description": (
                "Customer escalation call: they need NEX-105 shipped; we explain InfoSec approval "
                "is blocking and the release train is blocked until it clears."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-nex105-c-{seed % 10000:04d}",
            "organizer_email": "victoire.charlet@edu.escp.eu",
            "created": _iso(base + timedelta(days=4) - timedelta(hours=2)),
            "updated": _iso(base + timedelta(days=4) - timedelta(hours=1)),
            "start": _iso(base + timedelta(days=4)),
            "end": _iso(base + timedelta(days=4) + timedelta(minutes=40)),
            "metadata": {"scenario": "blocked_release"},
        },
        {
            "calendar_id": "eng-team@nexora.dev",
            "id": _u(seed, "cc-call", "billing-a"),
            "summary": "Billing retry logic sync",
            "description": (
                "Agenda: billing retry failures in production; align on retry logic and "
                "retry system ownership. No Linear ticket yet — tracking in notes."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-bill-a-{seed % 10000:04d}",
            "organizer_email": "thibault.hagler@gmail.com",
            "created": _iso(base - timedelta(hours=4)),
            "updated": _iso(base - timedelta(hours=1)),
            "start": _iso(base),
            "end": _iso(base + timedelta(minutes=40)),
            "metadata": {"scenario": "discussion_without_work"},
        },
        {
            "calendar_id": "eng-team@nexora.dev",
            "id": _u(seed, "cc-call", "billing-b"),
            "summary": "Follow-up: billing retry system",
            "description": (
                "Deep dive on billing retry logic again — same retry system instability; "
                "still no issue filed in Linear."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-bill-b-{seed % 10000:04d}",
            "organizer_email": "alex.kim@nexora.dev",
            "created": _iso(base + timedelta(days=3) - timedelta(hours=2)),
            "updated": _iso(base + timedelta(days=3) - timedelta(hours=1)),
            "start": _iso(base + timedelta(days=3)),
            "end": _iso(base + timedelta(days=3) + timedelta(minutes=35)),
            "metadata": {"scenario": "discussion_without_work"},
        },
        {
            "calendar_id": "incident@nexora.dev",
            "id": _u(seed, "cc-call", "contract-blocker"),
            "summary": "Deploy risk review",
            "description": (
                "We cannot deploy because contract tests fail intermittently in CI — "
                "no tracked issue opened yet; need owner."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-contract-{seed % 10000:04d}",
            "organizer_email": "manager@nexora.dev",
            "created": _iso(base + timedelta(days=6) - timedelta(hours=3)),
            "updated": _iso(base + timedelta(days=6) - timedelta(hours=1)),
            "start": _iso(base + timedelta(days=6)),
            "end": _iso(base + timedelta(days=6) + timedelta(minutes=50)),
            "metadata": {"scenario": "untracked_blocker"},
        },
        {
            "calendar_id": "incident@nexora.dev",
            "id": _u(seed, "cc-call", "postmortem"),
            "summary": "INC-2048 postmortem review",
            "description": (
                "Review customer-visible errors; confirm rollback completed; capture action items "
                "for release governance and InfoSec gate ownership."
            ),
            "status": "confirmed",
            "html_link": f"https://meet.google.com/cc-pm-{seed % 10000:04d}",
            "organizer_email": "manager@nexora.dev",
            "created": _iso(base + timedelta(days=7) - timedelta(hours=2)),
            "updated": _iso(base + timedelta(days=7) - timedelta(hours=1)),
            "start": _iso(base + timedelta(days=7)),
            "end": _iso(base + timedelta(days=7) + timedelta(minutes=55)),
            "metadata": {"scenario": "incident_analysis", "cortex_lane": "incident_analysis"},
        },
    ]
    sampled.extend(appended)
    if isinstance(main_events, list):
        main_events.extend(appended)


def extend_slack_for_nex300_completion(
    slack_events: list[dict[str, Any]],
    *,
    seed: int,
    t0: datetime,
) -> None:
    slack_events.append(
        {
            "id": _u(seed, "cc-slack", "nex300-done"),
            "channel": "#eng-core",
            "text": (
                "NEX-300 shipped — merged PR is live; "
                "nice work closing the billing reliability hardening."
            ),
            "ts": _iso(t0 + timedelta(days=90, hours=4)),
            "user_email": "thibault.hagler@gmail.com",
            "linear_issue_id": None,
            "pattern": "healthy_delivery",
            "metadata": {"scenario": "healthy_delivery"},
        }
    )


def extend_notion_for_cortex_capabilities(
    notion_pkg: dict[str, Any],
    linear_pkg: dict[str, Any],
    *,
    seed: int,
    t0: datetime,
) -> None:
    """Add a decision/incident/initiative database with explicit cross-tool traces."""
    databases = notion_pkg.setdefault("databases", {})
    rows = notion_pkg.setdefault("database_rows", [])
    comments = notion_pkg.setdefault("comments", [])
    relations = notion_pkg.setdefault("relations", [])
    issues = linear_pkg.get("issues") if isinstance(linear_pkg.get("issues"), list) else []
    nex105 = next((x for x in issues if x.get("identifier") == "NEX-105"), None)
    nex300 = next((x for x in issues if x.get("identifier") == "NEX-300"), None)

    db_id = _u(seed, "notion", "cortex-cap-db")
    databases[db_id] = {
        "id": db_id,
        "title": "Org cognition — decisions, incidents, initiatives",
        "description": (
            "Architectural capability anchors: decision lineage, incident traces, "
            "initiative aliases."
        ),
        "url": f"https://www.notion.so/nexora/{db_id.replace('-', '')}",
        "created_time": _iso(t0),
        "last_edited_time": _iso(t0 + timedelta(days=2)),
        "archived": False,
        "properties": {
            "Name": {"type": "title"},
            "Record Type": {
                "type": "select",
                "options": ["Decision", "Incident note", "Initiative alias", "Dependency risk"],
            },
            "Severity": {"type": "select", "options": ["S0", "S1", "S2", "S3"]},
            "Linked Linear": {"type": "rich_text"},
            "Summary": {"type": "rich_text"},
            "Related Row": {"type": "relation", "target": "self"},
        },
    }

    row_specs: list[dict[str, Any]] = [
        {
            "title": "Decision — no bypass for outbound domain review",
            "record_type": "Decision",
            "severity": "S1",
            "linear_key": "NEX-105",
            "summary": (
                "Exec decision: accept schedule slip; do not ship without InfoSec approval. "
                "Consequence: release train blocked until gate clears."
            ),
            "tags": ["decision_lineage", "strategic_analysis", "execution_intelligence"],
        },
        {
            "title": "Incident note — INC-2048 customer-visible errors",
            "record_type": "Incident note",
            "severity": "S1",
            "linear_key": "NEX-105",
            "summary": (
                "Customer-visible errors during promo; correlated with delayed NEX-105. "
                "Rollback executed; postmortem owner assigned."
            ),
            "tags": ["incident_analysis", "operational_debugging", "replay_driven_analysis"],
        },
        {
            "title": "Initiative alias — Northstar billing reliability",
            "record_type": "Initiative alias",
            "severity": "S3",
            "linear_key": "NEX-300",
            "summary": (
                "Roadmap name maps to NEX-300 delivery thread; align deck and Linear identifier "
                "for exec reporting."
            ),
            "tags": [
                "initiative_continuity",
                "onboarding_intelligence",
                "organizational_search",
            ],
        },
        {
            "title": "Dependency risk — billing retry system instability",
            "record_type": "Dependency risk",
            "severity": "S2",
            "linear_key": "",
            "summary": (
                "Repeated billing retry failures without a durable Linear umbrella issue — "
                "coordination gap across Slack and calls."
            ),
            "tags": [
                "dependency_intelligence",
                "discussion_without_work",
                "ambiguity_investigation",
            ],
        },
        {
            "title": "Decision — defer bulk retry refactor",
            "record_type": "Decision",
            "severity": "S2",
            "linear_key": "",
            "summary": (
                "Team agreed to patch hot paths first; "
                "large refactor deferred to next quarter."
            ),
            "tags": ["decision_lineage", "delivery_reconstruction"],
        },
        {
            "title": "Incident note — contract tests flaky in CI",
            "record_type": "Incident note",
            "severity": "S2",
            "linear_key": "",
            "summary": (
                "Deploy blocked until contract tests stable; "
                "risk discussed only in meetings initially."
            ),
            "tags": [
                "incident_analysis",
                "untracked_blocker",
                "operational_debugging",
            ],
        },
    ]

    new_row_ids: list[str] = []
    for i, spec in enumerate(row_specs):
        row_id = _u(seed, "notion", "cortex-row", str(i))
        new_row_ids.append(row_id)
        lid = ""
        if spec["linear_key"] == "NEX-105" and nex105:
            lid = str(nex105.get("id") or "")
        elif spec["linear_key"] == "NEX-300" and nex300:
            lid = str(nex300.get("id") or "")
        rows.append(
            {
                "id": row_id,
                "database_id": db_id,
                "url": f"https://www.notion.so/nexora/{row_id.replace('-', '')}",
                "created_time": _iso(t0 + timedelta(days=i)),
                "last_edited_time": _iso(t0 + timedelta(days=i, hours=3)),
                "archived": False,
                "properties": {
                    "Name": spec["title"],
                    "Record Type": spec["record_type"],
                    "Severity": spec["severity"],
                    "Linked Linear": spec["linear_key"] or "—",
                    "Summary": spec["summary"],
                },
                "source_refs": {
                    "linear_issue_id": lid or None,
                    "linear_issue_identifier": spec["linear_key"] or None,
                    "cortex_capability_tags": spec["tags"],
                },
            }
        )
        comments.append(
            {
                "id": _u(seed, "notion", "cortex-comment", str(i)),
                "row_id": row_id,
                "database_id": db_id,
                "created_time": _iso(t0 + timedelta(days=i, hours=1)),
                "last_edited_time": _iso(t0 + timedelta(days=i, hours=2)),
                "author_email": "manager@nexora.dev",
                "author_name": "Engineering Manager",
                "text": (
                    f"Verified trace for {spec['record_type']}: "
                    "see Slack #incidents and linked Linear context."
                ),
            }
        )

    for i in range(len(new_row_ids) - 1):
        relations.append(
            {
                "id": _u(seed, "notion", "cortex-rel", str(i)),
                "from_row_id": new_row_ids[i],
                "to_row_id": new_row_ids[i + 1],
                "kind": "narrative_chain",
                "created_time": _iso(t0 + timedelta(days=i)),
            }
        )

    # Populate Related Row relation on first row pointing to second (deterministic)
    if len(new_row_ids) >= 2:
        for r in rows:
            if r.get("id") == new_row_ids[0]:
                r["properties"]["Related Row"] = new_row_ids[1]
                break

    src = notion_pkg.setdefault("source_counts", {})
    if isinstance(src, dict):
        src["cortex_capability_rows"] = len(row_specs)


def _count_token(haystack: str, needle: str) -> int:
    return len(re.findall(re.escape(needle), haystack, flags=re.I))


def _notion_cortex_row_count(notion: dict[str, Any] | None) -> int:
    if not notion:
        return 0
    rows = notion.get("database_rows") if isinstance(notion.get("database_rows"), list) else []
    n = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        refs = row.get("source_refs") if isinstance(row.get("source_refs"), dict) else {}
        tags = refs.get("cortex_capability_tags")
        if isinstance(tags, list) and tags:
            n += 1
    return n


def cortex_capability_evidence(
    linear: dict[str, Any],
    github: dict[str, Any],
    slack_events: list[dict[str, Any]],
    calls_pkg: dict[str, Any],
    notion_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact counts for /admin/dataset/full — proves dominant patterns exist."""
    slack_txt = " ".join(str(x.get("text", "")) for x in slack_events if isinstance(x, dict))
    se = calls_pkg.get("sampled_events")
    calls = se if isinstance(se, list) else []
    call_blob = " ".join(
        f"{x.get('summary', '')} {x.get('description', '')}" for x in calls if isinstance(x, dict)
    )
    notion_blob = ""
    rows = notion_pkg.get("database_rows") if isinstance(notion_pkg, dict) else None
    if isinstance(rows, list):
        notion_blob = " ".join(
            f"{x.get('properties', {}).get('Name', '')} "
            f"{x.get('properties', {}).get('Summary', '')}"
            for x in rows
            if isinstance(x, dict)
        )
    hay = f"{slack_txt} {call_blob}"
    billing_slack = sum(
        1
        for x in slack_events
        if isinstance(x, dict)
        and (
            (x.get("metadata") or {}).get("scenario") == "discussion_without_work"
            or re.search(r"billing\s+retry", str(x.get("text", "")), re.I)
        )
    )
    blocked_slack_calls = _count_token(hay, "blocked") + _count_token(hay, "blocker")
    cognition_hay = f"{slack_txt} {call_blob} {notion_blob}"
    return {
        "nex105_mentions_slack_calls": _count_token(hay, "NEX-105"),
        "infosec_approval_mentions": _count_token(hay, "InfoSec approval"),
        "billing_retry_slack_rows": billing_slack,
        "billing_retry_token_hits": _count_token(hay, "billing retry")
        + _count_token(hay, "retry logic")
        + _count_token(hay, "retry system"),
        "contract_tests_mentions": _count_token(hay, "contract tests"),
        "blocked_language_hits": blocked_slack_calls,
        "postmortem_rollback_mentions": _count_token(cognition_hay, "postmortem")
        + _count_token(cognition_hay, "rollback"),
        "notion_cortex_tagged_rows": _notion_cortex_row_count(notion_pkg),
        "linear_issue_count": len(linear.get("issues") or []),
        "github_pr_count": len(github.get("pull_requests") or []),
        "slack_event_count": len(slack_events),
        "call_event_count": len(calls),
    }


def validate_cortex_capability_dataset_strength(
    linear: dict[str, Any],
    github: dict[str, Any],
    slack_events: list[dict[str, Any]],
    calls_pkg: dict[str, Any],
    notion_pkg: dict[str, Any] | None = None,
) -> list[str]:
    """Fail fast if dominant patterns are missing (deterministic CI)."""
    errs: list[str] = []
    issues = linear.get("issues") if isinstance(linear.get("issues"), list) else []
    idents = {str(x.get("identifier")) for x in issues if isinstance(x, dict)}
    for need in ("NEX-105", "NEX-201", "NEX-210", "NEX-300"):
        if need not in idents:
            errs.append(f"missing Linear identifier {need}")

    hay = " ".join(
        str(x.get("text", ""))
        for x in slack_events
        if isinstance(x, dict)
    )
    sampled = calls_pkg.get("sampled_events")
    calls = sampled if isinstance(sampled, list) else []
    hay += " " + " ".join(str(x.get("description", "")) for x in calls if isinstance(x, dict))

    if _count_token(hay, "NEX-105") < 8:
        errs.append("NEX-105 must dominate comms (>=8 mentions Slack+calls combined)")

    if _count_token(hay, "InfoSec approval") < 5:
        errs.append("InfoSec approval token must repeat (>=5) for blocked_release linking")

    billing_hits = (
        _count_token(hay, "billing retry")
        + _count_token(hay, "retry logic")
        + _count_token(hay, "retry system")
    )
    if billing_hits < 10:
        errs.append("billing/retry tokens must be strongly repeated (>=10) across Slack+calls")

    billing_slack_rows = sum(
        1
        for x in slack_events
        if isinstance(x, dict)
        and (
            (x.get("metadata") or {}).get("scenario") == "discussion_without_work"
            or re.search(r"billing\s+retry", str(x.get("text", "")), re.I)
        )
    )
    if billing_slack_rows < 4:
        errs.append("billing retry topic needs >=4 Slack rows")

    if _count_token(hay, "contract tests") < 1:
        errs.append("contract tests must appear in calls (untracked_blocker scenario)")

    prs = github.get("pull_requests") if isinstance(github.get("pull_requests"), list) else []
    nex105_pr = False
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        blob = f"{pr.get('title', '')} {pr.get('body', '')}"
        if re.search(r"NEX-105\b", blob, re.I):
            nex105_pr = True
            break
    if nex105_pr:
        errs.append("NEX-105 must not have a GitHub PR reference (blocked release scenario)")

    notion_rows = _notion_cortex_row_count(notion_pkg)
    if notion_rows < 6:
        errs.append("notion cortex_capability_tags rows too low (<6)")

    slack_txt = " ".join(str(x.get("text", "")) for x in slack_events if isinstance(x, dict))
    call_blob = " ".join(
        f"{x.get('summary', '')} {x.get('description', '')}"
        for x in calls
        if isinstance(x, dict)
    )
    cog = f"{slack_txt} {call_blob}"
    if _count_token(cog, "postmortem") + _count_token(cog, "rollback") < 2:
        errs.append(
            "incident vocabulary (postmortem/rollback) too sparse for incident_analysis lane"
        )

    return errs


def cortex_capability_scenario_tags() -> list[str]:
    return [
        "blocked_release",
        "discussion_without_work",
        "fragmented_execution",
        "healthy_delivery",
        "untracked_blocker",
        "decision_lineage",
        "incident_analysis",
        "initiative_continuity",
    ]
