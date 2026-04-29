"""Imbalanced, story-driven mock data for Manager Insights (Steps 3–8).

These patches are intentionally NOT evenly distributed: a few dominant execution
failures with many cross-tool references so gaps, highlights, and signals surface clearly.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from mock_connectors.fixtures import seed_config as sc
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
    h = hashlib.sha256((f"{seed}:mi:" + ":".join(parts)).encode()).hexdigest()
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
        "Release train: NEX-105 is blocked — waiting on InfoSec approval for outbound domain allowlist.",
        "Ping on NEX-105: still no owner on InfoSec approval; outbound domain is the gate.",
        "NEX-105 cannot ship until InfoSec approval clears; who is driving the InfoSec approval thread?",
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
        "We should fix the billing retry logic before next invoice run — seeing timeouts in retry system.",
        "Retry logic for billing keeps flaking; can we align on the billing retry approach this week?",
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


def patch_execution_bundle_for_manager_insights(bundle: ExecutionBundle) -> None:
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
            "id": _u(seed, "mi-comment-nex105-blocker"),
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
            "id": _u(seed, "mi-slack", "nex105-a"),
            "channel": "#incident-review",
            "text": "Incident notes tie back to NEX-105 — InfoSec approval still blocking release.",
            "ts": _iso(base + timedelta(hours=2)),
            "user_email": "victoire.charlet@edu.escp.eu",
            "linear_issue_id": linear_nex105_id,
            "pattern": "blocked_release",
            "metadata": {"scenario": "blocked_release"},
        },
        {
            "id": _u(seed, "mi-slack", "nex105-b"),
            "channel": "#customer-success",
            "text": "Customer asks daily about NEX-105; InfoSec approval is the blocker — no owner.",
            "ts": _iso(base + timedelta(days=1, hours=5)),
            "user_email": "design@nexora.dev",
            "linear_issue_id": linear_nex105_id,
            "pattern": "blocked_release",
            "metadata": {"scenario": "blocked_release"},
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
    events = calls_pkg.setdefault("sampled_events", [])
    if not isinstance(events, list):
        return
    base = t0 + timedelta(days=12)
    events.extend(
        [
            {
                "calendar_id": "release@nexora.dev",
                "id": _u(seed, "mi-call", "nex105-war"),
                "summary": "NEX-105 release readiness",
                "description": (
                    "War room: NEX-105 is blocked on InfoSec approval for outbound domain; "
                    "release is blocked until approval lands; still no owner for InfoSec thread."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/mi-nex105-a-{seed % 10000:04d}",
                "organizer_email": "thibault.hagler@gmail.com",
                "created": _iso(base - timedelta(days=1, hours=2)),
                "updated": _iso(base - timedelta(hours=2)),
                "start": _iso(base - timedelta(days=1)),
                "end": _iso(base - timedelta(days=1) + timedelta(minutes=45)),
                "metadata": {"scenario": "blocked_release"},
            },
            {
                "calendar_id": "release@nexora.dev",
                "id": _u(seed, "mi-call", "nex105-infosec"),
                "summary": "InfoSec gate for NEX-105",
                "description": (
                    "Discussion: InfoSec approval is the only blocker for NEX-105; "
                    "team agrees outbound domain review is blocked without security sponsor."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/mi-nex105-b-{seed % 10000:04d}",
                "organizer_email": "manager@nexora.dev",
                "created": _iso(base + timedelta(days=2) - timedelta(hours=3)),
                "updated": _iso(base + timedelta(days=2) - timedelta(hours=1)),
                "start": _iso(base + timedelta(days=2)),
                "end": _iso(base + timedelta(days=2) + timedelta(minutes=30)),
                "metadata": {"scenario": "blocked_release"},
            },
            {
                "calendar_id": "customer@nexora.dev",
                "id": _u(seed, "mi-call", "nex105-esc"),
                "summary": "Customer escalation — NEX-105",
                "description": (
                    "Customer escalation call: they need NEX-105 shipped; we explain InfoSec approval "
                    "is blocking and the release train is blocked until it clears."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/mi-nex105-c-{seed % 10000:04d}",
                "organizer_email": "victoire.charlet@edu.escp.eu",
                "created": _iso(base + timedelta(days=4) - timedelta(hours=2)),
                "updated": _iso(base + timedelta(days=4) - timedelta(hours=1)),
                "start": _iso(base + timedelta(days=4)),
                "end": _iso(base + timedelta(days=4) + timedelta(minutes=40)),
                "metadata": {"scenario": "blocked_release"},
            },
            {
                "calendar_id": "eng-team@nexora.dev",
                "id": _u(seed, "mi-call", "billing-a"),
                "summary": "Billing retry logic sync",
                "description": (
                    "Agenda: billing retry failures in production; align on retry logic and retry system "
                    "ownership. No Linear ticket yet — tracking in notes."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/mi-bill-a-{seed % 10000:04d}",
                "organizer_email": "thibault.hagler@gmail.com",
                "created": _iso(base - timedelta(hours=4)),
                "updated": _iso(base - timedelta(hours=1)),
                "start": _iso(base),
                "end": _iso(base + timedelta(minutes=40)),
                "metadata": {"scenario": "discussion_without_work"},
            },
            {
                "calendar_id": "eng-team@nexora.dev",
                "id": _u(seed, "mi-call", "billing-b"),
                "summary": "Follow-up: billing retry system",
                "description": (
                    "Deep dive on billing retry logic again — same retry system instability; "
                    "still no issue filed in Linear."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/mi-bill-b-{seed % 10000:04d}",
                "organizer_email": "alex.kim@nexora.dev",
                "created": _iso(base + timedelta(days=3) - timedelta(hours=2)),
                "updated": _iso(base + timedelta(days=3) - timedelta(hours=1)),
                "start": _iso(base + timedelta(days=3)),
                "end": _iso(base + timedelta(days=3) + timedelta(minutes=35)),
                "metadata": {"scenario": "discussion_without_work"},
            },
            {
                "calendar_id": "incident@nexora.dev",
                "id": _u(seed, "mi-call", "contract-blocker"),
                "summary": "Deploy risk review",
                "description": (
                    "We cannot deploy because contract tests fail intermittently in CI — "
                    "no tracked issue opened yet; need owner."
                ),
                "status": "confirmed",
                "html_link": f"https://meet.google.com/mi-contract-{seed % 10000:04d}",
                "organizer_email": "manager@nexora.dev",
                "created": _iso(base + timedelta(days=6) - timedelta(hours=3)),
                "updated": _iso(base + timedelta(days=6) - timedelta(hours=1)),
                "start": _iso(base + timedelta(days=6)),
                "end": _iso(base + timedelta(days=6) + timedelta(minutes=50)),
                "metadata": {"scenario": "untracked_blocker"},
            },
        ]
    )


def extend_slack_for_nex300_completion(
    slack_events: list[dict[str, Any]],
    *,
    seed: int,
    t0: datetime,
) -> None:
    slack_events.append(
        {
            "id": _u(seed, "mi-slack", "nex300-done"),
            "channel": "#eng-core",
            "text": "NEX-300 shipped — merged PR is live; nice work closing the billing reliability hardening.",
            "ts": _iso(t0 + timedelta(days=90, hours=4)),
            "user_email": "thibault.hagler@gmail.com",
            "linear_issue_id": None,
            "pattern": "healthy_delivery",
            "metadata": {"scenario": "healthy_delivery"},
        }
    )


def _count_token(haystack: str, needle: str) -> int:
    return len(re.findall(re.escape(needle), haystack, flags=re.I))


def manager_insights_evidence(
    linear: dict[str, Any],
    github: dict[str, Any],
    slack_events: list[dict[str, Any]],
    calls_pkg: dict[str, Any],
) -> dict[str, Any]:
    """Compact counts for /admin/dataset/full — proves dominant patterns exist."""
    slack_txt = " ".join(str(x.get("text", "")) for x in slack_events if isinstance(x, dict))
    calls = (
        calls_pkg.get("sampled_events") if isinstance(calls_pkg.get("sampled_events"), list) else []
    )
    call_blob = " ".join(
        f"{x.get('summary', '')} {x.get('description', '')}" for x in calls if isinstance(x, dict)
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
    return {
        "nex105_mentions_slack_calls": _count_token(hay, "NEX-105"),
        "infosec_approval_mentions": _count_token(hay, "InfoSec approval"),
        "billing_retry_slack_rows": billing_slack,
        "billing_retry_token_hits": _count_token(hay, "billing retry")
        + _count_token(hay, "retry logic")
        + _count_token(hay, "retry system"),
        "contract_tests_mentions": _count_token(hay, "contract tests"),
        "blocked_language_hits": blocked_slack_calls,
        "linear_issue_count": len(linear.get("issues") or []),
        "github_pr_count": len(github.get("pull_requests") or []),
        "slack_event_count": len(slack_events),
        "call_event_count": len(calls),
    }


def validate_manager_insight_dataset_strength(
    linear: dict[str, Any],
    github: dict[str, Any],
    slack_events: list[dict[str, Any]],
    calls_pkg: dict[str, Any],
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
    calls = calls_pkg.get("sampled_events") if isinstance(calls_pkg.get("sampled_events"), list) else []
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

    slack_only = " ".join(str(x.get("text", "")) for x in slack_events if isinstance(x, dict))
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

    return errs


def scenario_coverage_tags() -> list[str]:
    return [
        "blocked_release",
        "discussion_without_work",
        "fragmented_execution",
        "healthy_delivery",
        "untracked_blocker",
    ]
