"""Realistic product copy for Nexora mock Linear/GitHub data (deterministic)."""

from __future__ import annotations

from typing import Any

# -----------------------------------------------------------------------------
# Company + customers (B2B workspace / ops platform)
# -----------------------------------------------------------------------------

NEXORA_BLURB = (
    "Nexora sells a connected workspace for mid-market companies: projects, customer "
    "pipelines, and cross-tool automations. EU + US footprint; SOC2 in flight; heavy "
    "integrations (Slack, GitHub, CRM). Core bet: reduce tool sprawl for 200–2k employee orgs."
)

CUSTOMERS: tuple[str, ...] = (
    "Acme Logistics GmbH",
    "Bluecrest Retail",
    "Kite Health EU",
    "Northwind Manufacturing",
    "Contoso Field Ops",
    "Fabrikam Bank (pilot)",
    "Tailwind Education",
    "Coho Fisheries",
)

# One initiative per project slot (index 0 .. 11)
PROJECT_BLUEPRINTS: tuple[dict[str, str], ...] = (
    {
        "name": "Activation & first workspace value",
        "slug": "activation-ttfv",
        "summary": "Cut time-to-first-value after signup; guided setup; role defaults.",
        "description": (
            "PMF lever: teams abandon us in week one if connectors feel empty. "
            "Ship checklist UX, sample data opt-in, and completion telemetry to Amplitude."
        ),
    },
    {
        "name": "Reliability: SLOs, paging, incident hygiene",
        "slug": "reliability-slos",
        "summary": "Error budget policy, on-call runbooks, customer-facing status cues.",
        "description": (
            "Align CORE/PLAT on SLOs for API p99 and webhook success rate. "
            "Reduce noisy pages; add burn-rate alerts; document customer comms templates."
        ),
    },
    {
        "name": "Trust & access: SOC2 + enterprise SSO",
        "slug": "trust-soc2-sso",
        "summary": "Evidence collection, SCIM rough cut, SSO edge cases.",
        "description": (
            "Security review asks for joiner/leaver story. Partner with Legal on DPA wording; "
            "don't promise SCIM GA until INT validates Okta + Entra paths."
        ),
    },
    {
        "name": "Integrations throughput & partner health",
        "slug": "integrations-health",
        "summary": "Connector quotas, degraded modes, partner-facing error surfaces.",
        "description": (
            "Large customers run nightly batches. Need fair queuing, visible retry policy, "
            "and a 'partner incident' playbook when their API shape drifts."
        ),
    },
    {
        "name": "Web app: performance & information density",
        "slug": "web-perf-density",
        "summary": "LCP, table virtualization, saved views, keyboard flows.",
        "description": (
            "RevOps users live in wide tables. Ship virtualized lists without breaking "
            "screen-reader labels; measure bundle impact of the new charting lib."
        ),
    },
    {
        "name": "Mobile: offline, push, and session refresh",
        "slug": "mobile-offline-push",
        "summary": "Resilient mobile clients for frontline managers.",
        "description": (
            "Offline read cache for last-synced boards; push for @mentions; "
            "handle refresh token rotation without silent logout loops."
        ),
    },
    {
        "name": "Billing & usage metering accuracy",
        "slug": "billing-metering",
        "summary": "Seat sync, overage previews, invoice line-item audit trail.",
        "description": (
            "Finance found a 3% seat drift vs Salesforce. Trace idempotency keys end-to-end; "
            "add reconciliation job and customer-facing usage export."
        ),
    },
    {
        "name": "Data platform: events, warehouse, GDPR deletes",
        "slug": "data-events-gdpr",
        "summary": "Event schema v2, PII classification, delete propagation.",
        "description": (
            "Unify on protobuf-ish JSON schema; document which events carry emails; "
            "wire GDPR delete to downstream projections with explicit SLAs."
        ),
    },
    {
        "name": "Platform: cost, scale, and deploy safety",
        "slug": "platform-cost-scale",
        "summary": "K8s rightsizing, progressive rollout, config drift detection.",
        "description": (
            "EU cluster creeping on cost. Add HPA guardrails; canary analysis for API; "
            "stop 'hotfix straight to prod' except via break-glass policy."
        ),
    },
    {
        "name": "API public surface & partnership keys",
        "slug": "api-partnerships",
        "summary": "Versioning, deprecation calendar, scoped OAuth for ISVs.",
        "description": (
            "Two ISVs need stable webhooks + granular scopes. Publish deprecation policy; "
            "avoid breaking Kite Health's sandbox this quarter."
        ),
    },
    {
        "name": "Core services: auth, sessions, org model",
        "slug": "core-auth-orgs",
        "summary": "Session fixation hardening, org switching, audit logs.",
        "description": (
            "Pen test flagged cookie edge cases. Tighten SameSite story; "
            "make org switch explicit in audit trail for enterprise buyers."
        ),
    },
    {
        "name": "Design system: tokens, a11y, content guidelines",
        "slug": "design-system-tokens",
        "summary": "Figma ↔ code drift, focus order, error copy tone.",
        "description": (
            "Marketing shipped off-brand modals. Lock token pipeline; "
            "add Storybook a11y checks and a short 'voice & tone' for errors."
        ),
    },
)

# (title fragment, description markdown template with placeholders)
# Placeholders: {ident}, {repo}, {customer}, {project}, {epic}
ISSUE_SCENARIOS: dict[str, tuple[tuple[str, str], ...]] = {
    "CORE": (
        (
            "API: idempotent task create returns 409 on replay with same key",
            "## Context\n"
            "{customer} retries creates on flaky wifi. We return 500 instead of stable 409.\n\n"
            "## Acceptance\n"
            "- [ ] Same `Idempotency-Key` → same response body\n"
            "- [ ] Metrics: `api.idempotent_replay_total`\n\n"
            "Repo: `{repo}`",
        ),
        (
            "Webhook delivery: backoff + DLQ when partner returns 429",
            "Batch jobs from **{customer}** hammer us at 02:00 UTC. "
            "Need jittered backoff and a visible DLQ in admin.\n\n"
            "Depends on **{project}** rollout for quotas.",
        ),
        (
            "Session refresh: race leaves user on blank shell after org switch",
            "Repro: switch org mid-request → `/me` 401 → client clears cache aggressively. "
            "See screen recording in thread.\n\n"
            "Link draft RFC in `auth-service`.",
        ),
        (
            "Rate limits: document burst vs sustained for partnership tier",
            "Sales promised **{customer}** 'higher limits' without a number. "
            "PM + CORE align before legal signs amendment.",
        ),
        (
            "GraphQL-ish list cursor leaks internal row order across pages",
            "Security review: stable ordering must not expose insertion timing. "
            "Switch to opaque cursors keyed off `(created_at, id)`.",
        ),
        (
            "Audit log export missing actor IP for enterprise filter",
            "**{customer}** DPA asks for IP on sensitive writes. "
            "We log user id only today.",
        ),
        (
            "POST /v1/import: validate schema before enqueue (fail fast)",
            "Support burns cycles re-running huge CSV jobs that fail at step 7. "
            "Return actionable row errors in <2s.",
        ),
        (
            "Spike: outbox pattern for cross-service domain events",
            "Before we cut **{epic}** over, confirm we won't double-publish on crash recovery.",
        ),
    ),
    "WEB": (
        (
            "Dashboard: saved filters disappear after hard refresh (localStorage race)",
            "RevOps at **{customer}** loses a 12-column filter set. "
            "Persist server-side with optimistic UI; keep offline banner honest.",
        ),
        (
            "Empty state for new workspace promises connectors that are not wired yet",
            "Copy says 'Slack live' before OAuth finishes — feels like a bug. "
            "Coordinate with **{project}** onboarding checklist.",
        ),
        (
            "Table: virtualization breaks keyboard focus order on Firefox",
            "a11y audit blocker. Must not ship **{epic}** marketing page until fixed.",
        ),
        (
            "Banner: incident comms should link to status page, not generic /help",
            "During last Sev2, customers scrolled past the banner. "
            "Add deep link + optional maintenance window id.",
        ),
        (
            "Performance: LCP regression on /projects after chart bundle merge",
            "Lighthouse mobile p75 went from 2.4s → 3.9s. "
            "Split vendor chunk; lazy-load chart when tab selected.",
        ),
        (
            "Bulk actions: confirm modal uses scary 'Delete' for archive",
            "Support ticket #4412 — user archived 200 rows by mistake. "
            "Copy + undo snackbar for 10s.",
        ),
        (
            "Command-K palette: search ranks archived issues too high",
            "PM ask: default to active work; show archived with explicit toggle.",
        ),
        (
            "Web: cross-tab org switch shows stale websocket channel subscriptions",
            "Reproducible on Chrome; likely event bus not tearing down old org room.",
        ),
    ),
    "MOB": (
        (
            "iOS: push notification opens wrong issue when user has two accounts",
            "**{customer}** pilot user hit this during on-call. "
            "Deep link must carry account + org context.",
        ),
        (
            "Android: biometric re-prompt loop after OS update (Samsung)",
            "Sentry spike last week; correlate with Android 14 point release.",
        ),
        (
            "Offline: stale board cache shows completed work as 'In Progress'",
            "Need ETag per column or server-driven sync token.",
        ),
        (
            "Mobile session refresh drops refresh token on airplane mode toggle",
            "User lands 'logged out' at gate — unacceptable for field managers.",
        ),
        (
            "Haptic + sound on mention feels broken in silent mode",
            "Design wants respect DND; still show in-app toast.",
        ),
        (
            "Spike: background fetch budget for large attachment thumbnails",
            "Battery vs UX tradeoff; document decision for **{project}**.",
        ),
        (
            "Tablet layout: split view collapses when keyboard opens",
            "Regression after design token migration.",
        ),
        (
            "Mobile analytics: session start fires twice on cold launch",
            "Inflates activation funnel; fix before QBR charts.",
        ),
    ),
    "PLAT": (
        (
            "Canary analysis ignores 503 spike from single bad pod",
            "Last deploy rolled forward despite customer-visible errors. "
            "Add min pod coverage gate.",
        ),
        (
            "EU cluster: HPA scales up too late for morning traffic ramp",
            "Cost team wants caps; reliability wants headroom — need policy doc.",
        ),
        (
            "Terraform drift: manual security group change not reconciled",
            "Incident follow-up: enforce plan-only in CI + weekly drift report.",
        ),
        (
            "Deploy freeze calendar not visible to on-call engineers",
            "Marketing freeze overlapped with Sev3 fix; comms failure.",
        ),
        (
            "Secrets rotation job skipped staging (config typo)",
            "Add assertion that env label matches cluster.",
        ),
        (
            "Runbook: restore from backup missing RTO for warehouse replica",
            "Audit finding — update before **{customer}** renewal conversation.",
        ),
        (
            "K8s: pod OOM on log shipping sidecar during burst",
            "Correlate with **{project}** metrics cardinality increase.",
        ),
        (
            "Feature flags: kill switch for webhook workers not wired in EU",
            "Parity gap between regions; fix or document exception.",
        ),
    ),
    "INT": (
        (
            "Slack OAuth: workspace install fails when org already linked to another tenant",
            "Edge case for consultancies; need explicit UX + support macro.",
        ),
        (
            "GitHub app: webhook signature mismatch behind corporate SSL inspection",
            "**{customer}** proxy rewrites headers; document required allowlist.",
        ),
        (
            "Linear import: duplicate labels when re-running migration",
            "Idempotency by external id; add dry-run summary.",
        ),
        (
            "CRM sync: opportunity stage mapping wrong for Fabrikam custom fields",
            "CSM escalated; map by stable id not display label.",
        ),
        (
            "Integration health dashboard: 'degraded' without actionable owner",
            "On-call didn't know whether to page CORE or INT.",
        ),
        (
            "Webhook retries: exponential curve too aggressive for flaky partner",
            "Tune per-connector policy; avoid hammering sick endpoints.",
        ),
        (
            "SCIM: group push creates duplicate teams when case differs",
            "Normalize slug; write migration to merge existing dupes.",
        ),
        (
            "Sandbox: rate limits for ISV tests far below prod — false confidence",
            "Align limits or label clearly in developer docs.",
        ),
    ),
    "DATA": (
        (
            "Event schema v2: `workspace_id` optional breaks downstream dbt model",
            "Coordinate cutover with **{project}**; backfill 14 days.",
        ),
        (
            "GDPR delete: projection lag leaves PII in cold storage 36h",
            "Legal wants <24h; propose compaction job + SLO.",
        ),
        (
            "Warehouse: cost spike from unpartitioned join on `events_raw`",
            "Add date partition + guard in CI for full scans.",
        ),
        (
            "PII classifier misses custom field on ticket imports",
            "Customer uploaded CSV with national ID in free-text column.",
        ),
        (
            "Metric: 'active user' definition differs between product and sales",
            "Single source of truth doc + dashboard footnote.",
        ),
        (
            "Streaming job: late events skew funnel conversion window",
            "Document watermark policy; alert on skew > 10m.",
        ),
        (
            "Data quality: duplicate org rows after merge tool beta",
            "Run dedupe script; add constraint where safe.",
        ),
        (
            "Export job emails link expires in 1h — too short for enterprise IT",
            "Extend to 24h with signed token rotation.",
        ),
    ),
}

EPIC_VERBS: tuple[str, ...] = (
    "Ship",
    "Harden",
    "Instrument",
    "Unblock",
    "Reduce",
    "Clarify",
    "Migrate",
    "Scale",
)

EPIC_OUTCOMES: tuple[str, ...] = (
    "webhook reliability under burst",
    "customer-visible incident comms",
    "mobile session trust",
    "billing reconciliation truth",
    "SOC2 evidence trail",
    "saved-view persistence",
    "connector error literacy",
    "API deprecation safety",
    "data delete guarantees",
    "on-call noise budget",
    "cross-team dependency map",
    "design token drift",
)


def customer_for_index(i: int) -> str:
    return CUSTOMERS[i % len(CUSTOMERS)]


def project_blueprint(i: int) -> dict[str, str]:
    return PROJECT_BLUEPRINTS[i % len(PROJECT_BLUEPRINTS)]


def epic_title(i: int, team_key: str, project_name: str) -> str:
    v = EPIC_VERBS[i % len(EPIC_VERBS)]
    o = EPIC_OUTCOMES[i % len(EPIC_OUTCOMES)]
    return f"{v} {o} — {team_key} ({project_name.split(':')[0][:28]})"


def epic_description(i: int, customer: str) -> str:
    return (
        f"## Why\nDrive outcomes for **{customer}** and similar mid-market rollouts.\n\n"
        f"## Success\n- [ ] Scoped milestones with explicit owners\n"
        f"- [ ] Risk register updated weekly\n"
        f"- [ ] Demo recording attached before marking Done\n\n"
        f"## Links\nDraft PRD in Notion; engineering RFC in GitHub."
    )


def issue_title_and_body(
    team_key: str,
    issue_index: int,
    *,
    identifier: str,
    repo_full: str,
    customer: str,
    project_name: str,
    epic_ident: str | None,
) -> tuple[str, str]:
    scenarios = ISSUE_SCENARIOS.get(team_key) or ISSUE_SCENARIOS["CORE"]
    title_tmpl, desc_tmpl = scenarios[issue_index % len(scenarios)]
    epic = epic_ident or "NEX roadmap (unparented)"
    desc = desc_tmpl.format(
        ident=identifier,
        repo=repo_full,
        customer=customer,
        project=project_name,
        epic=epic,
    )
    # Light hygiene noise (deterministic) — keeps "real company mess"
    if issue_index % 17 == 3:
        title_tmpl = title_tmpl.replace("API", "api", 1)
    if issue_index % 19 == 5 and "Acceptance" in desc:
        desc = desc.replace("Acceptance", "Acceptence", 1)
    if issue_index % 23 == 7:
        desc += "\n\n_Note: customer thread forwarded from Slack — links may be stale._"
    if issue_index % 29 == 11:
        desc += "\n\n<!-- TODO: attach Loom after design review -->"
    prefix = ""
    if issue_index % 13 == 2:
        prefix = "[Spike] "
    if issue_index % 11 == 0:
        return f"{identifier} — Untitled / missing triage title", ""
    return f"{identifier} — {prefix}{title_tmpl}", desc


# Comment arcs: (role, body_template). Roles include pm, assignee, eng, design, support, …
# Placeholders: ident, title_short, repo, customer, project, epic, a_first, c_first, pm_first.

COMMENT_ARCS: tuple[tuple[tuple[str, str], ...], ...] = (
    (
        (
            "pm",
            "Re-read the scope on **{title_short}**: are we committing to **soft-delete** "
            "for audit, or hard-delete with tombstone only? Legal pinged and I don't want to "
            "promise the wrong thing before the **{customer}** renewal.",
        ),
        (
            "assignee",
            "Soft-delete with `deleted_at` + retained history for 90d, then archival job. "
            "Hard delete only via break-glass admin tool with extra logging. I'll update the "
            "ticket + link the schema draft in `{repo}`.",
        ),
        (
            "pm",
            "Perfect — I'll mirror that in the customer-facing FAQ and flag Sales.",
        ),
    ),
    (
        (
            "support",
            "**{customer}** says the UI shows 'connected' for Slack but DMs never arrive. "
            "I don't see errors on their tenant — can someone confirm whether webhooks are "
            "firing for org `…7f2a`?",
        ),
        (
            "eng",
            "I see intermittent 401 refresh on our side — likely clock skew on their IdP. "
            "I'll add a metric for `oauth_refresh_failed` and ask them to check NTP.",
        ),
        (
            "assignee",
            "Shipped a tighter error surface: users now see 'reconnect Slack' instead of silent "
            "failure. @{c_first} can you verify with the customer tomorrow?",
        ),
    ),
    (
        (
            "creator",
            "Before we cut **{ident}**, can we align on **p95 vs p99** for this endpoint? "
            "Marketing copy mentions 'real-time' and I'm worried we're over-promising.",
        ),
        (
            "assignee",
            "Proposal: claim 'near real-time' externally; internally target p99 < 5s under "
            "normal load. I'll add an SLO panel stub under **{project}**.",
        ),
        (
            "pm",
            "Works for me. Please add a footnote in the deck I'm sending to **{customer}**.",
        ),
    ),
    (
        (
            "design",
            "The destructive action pattern here doesn't match the new modal guidelines — "
            "can we swap to the two-step confirm with typed project name?",
        ),
        (
            "assignee",
            "Agree. That's an extra half-day because we reuse the bulk-action modal — I'll "
            "split the component so mobile doesn't inherit desktop copy.",
        ),
        (
            "design",
            "Thanks. Drop screenshots in Figma comment thread #744 when ready.",
        ),
    ),
    (
        (
            "eng",
            "I'm blocked on **{ident}** until the API schema for `workspace.settings` lands — "
            "right now mobile crashes on null `notifications.mute_mentions`.",
        ),
        (
            "assignee",
            "Schema PR is up in `{repo}` — null means 'inherit org default'. "
            "I'll ping you on the review; shouldn't be more than a day.",
        ),
        (
            "eng",
            "Pulled latest — unblocked. I'll adjust the client fallback and mark this done "
            "after QA on a physical device.",
        ),
    ),
    (
        (
            "contractor",
            "Quick question: should the CSV import reject unknown columns or ignore them? "
            "**{customer}** sent a file with extra HR fields and the job partially succeeded "
            "— feels scary.",
        ),
        (
            "pm",
            "Ignore-with-warning in v1; reject in v2 behind a flag. Document the behavior in "
            "the runbook so Support doesn't interpret it as data loss.",
        ),
        (
            "assignee",
            "Implemented warn + summary row in the import report UI. "
            "Screenshot attached — @{pm_first} okay to ship?",
        ),
    ),
    (
        (
            "pm",
            "Customer QBR on Thursday: can we demo **{title_short}** end-to-end, or should I "
            "fallback to slides only?",
        ),
        (
            "assignee",
            "Demo is possible on staging if we freeze `integrations` branch after lunch. "
            "Risk: flaky partner sandbox — I'll have a recorded Loom as backup.",
        ),
        (
            "support",
            "I'll join 10m early to validate **{customer}** test user still has the right "
            "feature flags.",
        ),
    ),
    (
        (
            "intern",
            "I can't reproduce the bug on simulator — only on device. "
            "Any known gotchas with push + low power mode?",
        ),
        (
            "eng",
            "Yes — defer push handling when battery saver kills background refresh. "
            "See issue cross-linked from **{epic}** notes.",
        ),
        (
            "intern",
            "Got it, thanks. I'll document in `/mobile/docs/push.md` and push a small FAQ entry.",
        ),
    ),
    (
        (
            "creator",
            "Scope creep ask from **{customer}**: they want per-row audit on exports. "
            "That's not in **{project}** — do we split a follow-up ticket?",
        ),
        (
            "pm",
            "Yes — carve `NEX-export-audit` follow-up; keep this ticket strictly for the CSV "
            "performance work. I'll negotiate timeline with CS.",
        ),
        (
            "assignee",
            "Sounds good. I'll land the perf fix here and link the new ticket in the description.",
        ),
    ),
    (
        (
            "assignee",
            "Rollout plan: feature flag `workspace.saved_views` at 5% → 25% → 100% with burn "
            "alert on error rate. Any objections?",
        ),
        (
            "eng",
            "Add a kill switch note in runbook — last time PLAT missed the flag name in EU.",
        ),
        (
            "bot",
            "Scheduled canary: `deploy/web@sha:9f2c` to `eu-west` — auto-rollback enabled.",
        ),
    ),
    (
        (
            "support",
            "User insists the incident banner lied — downtime was 22m but banner said 'degraded'. "
            "Can we align copy with status page truth?",
        ),
        (
            "pm",
            "Agree — wording came from old template. I'll pair with WEB on a severity → copy "
            "matrix; please don't edit strings in prod without design review.",
        ),
        (
            "design",
            "Draft matrix in Figma 'Incidents v2' — comments open until Friday.",
        ),
    ),
    (
        (
            "pm",
            "Do we need GDPR delete to cover derived aggregates in `{repo}` jobs? "
            "Data thinks yes; Legal is fuzzy.",
        ),
        (
            "assignee",
            "I'll schedule a 30m with DATA + Legal. Until then, mark exports as best-effort "
            "and log manual tickets for stricter customers.",
        ),
        (
            "eng",
            "Added a TODO in the warehouse dbt model header pointing to this thread.",
        ),
    ),
    (
        (
            "eng",
            "Flaky integration test in CI — `webhook_retry_spec` fails 1/20. "
            "Not sure if clock or port race.",
        ),
        (
            "assignee",
            "Saw it — switched to frozen clock helper in branch `fix/flaky-webhook-spec`. "
            "Please rebase.",
        ),
        (
            "eng",
            "Green on 5 reruns. Not merging until someone from INT sanity-checks the mock server.",
        ),
    ),
    (
        (
            "design",
            "Accessibility: focus trap escapes the modal when browser zoom is 125%.",
        ),
        (
            "assignee",
            "Tracked to old portal implementation — porting fix from design-system package v3. "
            "ETA two days; blocks marketing landing tweak.",
        ),
        (
            "pm",
            "Marketing can slip a week — prioritize a11y for **{customer}** pilot contract.",
        ),
    ),
    (
        (
            "creator",
            "Can we get a written decision on **pagination caps** for the public API? "
            "Partners keep opening tickets expecting unlimited export.",
        ),
        (
            "pm",
            "Cap stays 100/page with cursor; offer async export for larger pulls — document in "
            "developer portal v1.2.",
        ),
        (
            "assignee",
            "I'll add 429 hints + `Retry-After` when partners ignore caps; already spec'd in "
            "**{project}**.",
        ),
    ),
    (
        (
            "support",
            "**{customer}** hit '403' saving a view — looks like RBAC mismatch for 'viewer' role.",
        ),
        (
            "assignee",
            "Confirmed — viewers shouldn't hit that mutation; UI should hide action. "
            "Fix in web; API returns clearer error code `VIEWER_MUTATION_DENIED`.",
        ),
        (
            "support",
            "Validated on staging with their sandbox user — please cherry-pick for hotfix train.",
        ),
    ),
    (
        (
            "pm",
            "Risk: **{epic}** depends on billing meter accuracy — are we comfortable tying "
            "launch comms to this milestone?",
        ),
        (
            "assignee",
            "Soft dependency only — launch comms if meter within 1% on shadow mode for 48h. "
            "DATA signed off yesterday evening.",
        ),
        (
            "pm",
            "Great — I'll update the exec summary and remove the yellow flag.",
        ),
    ),
    (
        (
            "eng",
            "Nit: error copy says 'try again' but the failure is permanent without admin action — "
            "misleading for admins.",
        ),
        (
            "design",
            "Proposed strings in doc — please use `E-1042` pattern for support lookup.",
        ),
        (
            "assignee",
            "Merged copy + added analytics event `error_surface_shown` with code.",
        ),
    ),
    (
        (
            "assignee",
            "Perf note: the join on `events_raw` is scanning 48h — can we tighten to 6h for "
            "this dashboard?",
        ),
        (
            "eng",
            "Yes but product wants week view — compromise: 7d with partition pruning + "
            "pre-agg for 'last 30d' tile.",
        ),
        (
            "pm",
            "Document the tradeoff in PR description; I'll communicate to **{customer}** CSM.",
        ),
    ),
    (
        (
            "creator",
            "Security asked whether we log request bodies on failed webhook deliveries — "
            "sounds like PII risk.",
        ),
        (
            "assignee",
            "We log headers + status only; bodies truncated to 2kb in debug mode for 24h. "
            "I'll link the retention policy PDF.",
        ),
        (
            "pm",
            "Please add that to the SOC2 evidence folder before Friday.",
        ),
    ),
    (
        (
            "support",
            "Customer wants an ETA for **{ident}** — they're blocked on go-live Monday.",
        ),
        (
            "assignee",
            "Best case: merge Thursday, deploy Friday AM EU; worst case slip to Monday if "
            "review drags. I'll post hourly updates in #customer-{customer_short}.",
        ),
        (
            "pm",
            "I'll manage expectations on the call — thanks for the transparency.",
        ),
    ),
    (
        (
            "eng",
            "LGTM on approach — one concern: we're caching org switch in memory too long.",
        ),
        (
            "assignee",
            "Reduced TTL to 5m + explicit invalidation on role change webhook.",
        ),
        (
            "eng",
            "Nice — ship it.",
        ),
    ),
)


def _short(s: str, n: int = 52) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _team_humans(users: list[dict[str, Any]], team_key: str) -> list[dict[str, Any]]:
    return sorted(
        [
            u
            for u in users
            if u.get("team_key") == team_key and "bot" not in u["login"].lower()
        ],
        key=lambda u: u["login"],
    )


def _pick_user(
    role: str,
    team_key: str,
    users: list[dict[str, Any]],
    *,
    assignee: dict[str, Any] | None,
    creator: dict[str, Any] | None,
    eng_pool: list[dict[str, Any]],
    pm_pool: list[dict[str, Any]],
    issue_index: int,
) -> dict[str, Any]:
    def by_login(login: str) -> dict[str, Any] | None:
        return next((u for u in users if u["login"] == login), None)

    if role == "assignee" and assignee:
        return assignee
    if role == "creator" and creator:
        return creator
    if role == "pm" and pm_pool:
        return pm_pool[issue_index % len(pm_pool)]
    if role == "design":
        u = by_login("rdesign")
        if u and u.get("team_key") == team_key:
            return u
    if role == "support":
        u = by_login("ssupport")
        if u and u.get("team_key") == team_key:
            return u
        sup = [x for x in _team_humans(users, team_key) if x.get("role") == "support"]
        if sup:
            return sup[issue_index % len(sup)]
    if role == "contractor":
        u = by_login("pfreelance")
        if u:
            return u
    if role == "intern":
        u = by_login("jintern")
        if u:
            return u
    if role == "bot":
        u = by_login("nexora-bot")
        if u:
            return u
    if role == "eng":
        pool = [u for u in eng_pool if not assignee or u["login"] != assignee["login"]]
        if pool:
            return pool[issue_index % len(pool)]
    if assignee:
        return assignee
    if eng_pool:
        return eng_pool[issue_index % len(eng_pool)]
    tm = _team_humans(users, team_key)
    return tm[issue_index % len(tm)] if tm else users[0]


def format_comment_arc(
    arc: tuple[tuple[str, str], ...],
    *,
    issue: dict[str, Any],
    users: list[dict[str, Any]],
    eng_pool: list[dict[str, Any]],
    pm_pool: list[dict[str, Any]],
    assignee: dict[str, Any] | None,
    creator: dict[str, Any] | None,
    issue_index: int,
    customer: str,
    repo: str,
) -> list[tuple[dict[str, Any], str]]:
    """Return list of (author_user, body) for one thread."""
    team_key = str(issue["team"]["key"])
    parent = issue.get("parent") or {}
    epic_ident = parent.get("identifier") if isinstance(parent, dict) else None
    epic = epic_ident or "NEX roadmap"
    proj = issue.get("project") or {}
    project_name = proj.get("name", "Roadmap") if isinstance(proj, dict) else "Roadmap"
    ident = issue["identifier"]
    title = issue.get("title") or ""
    a_first = (
        _issue_actor_first(assignee)
        if assignee
        else "team"
    )
    c_first = _issue_actor_first(creator) if creator else "all"
    pm_first = _issue_actor_first(pm_pool[0]) if pm_pool else "PMs"

    customer_short = customer.split()[0].lower()
    out: list[tuple[dict[str, Any], str]] = []
    for line_i, (role, tmpl) in enumerate(arc):
        author = _pick_user(
            role,
            team_key,
            users,
            assignee=assignee,
            creator=creator,
            eng_pool=eng_pool,
            pm_pool=pm_pool,
            issue_index=issue_index + line_i,
        )
        body = tmpl.format(
            ident=ident,
            title_short=_short(title.replace(f"{ident} — ", ""), 56),
            repo=repo,
            customer=customer,
            customer_short=customer_short,
            project=project_name,
            epic=epic,
            a_first=a_first,
            c_first=c_first,
            pm_first=pm_first,
        )
        out.append((author, body))
    return out


def _issue_actor_first(u: dict[str, Any] | None) -> str:
    if not u:
        return "there"
    dn = u.get("linear_display_name")
    if isinstance(dn, str) and dn.strip():
        return dn.split()[0]
    name = (u.get("name") or "").strip()
    if name:
        return name.split()[0]
    return u.get("login") or "there"


def comment_distribution(num_issues: int, target_comments: int) -> list[int]:
    """Comments per issue; sums exactly to ``target_comments`` (spread remainder round-robin)."""
    if num_issues <= 0:
        return []
    base, rem = divmod(target_comments, num_issues)
    return [base + (1 if i < rem else 0) for i in range(num_issues)]


# Short follow-ups when an arc is shorter than the slot budget for that issue.
COMMENT_PAD: tuple[tuple[str, str], ...] = (
    (
        "eng",
        "Anything still blocking **{ident}** on your side? Happy to pair for 15m if useful.",
    ),
    (
        "assignee",
        "No blockers — waiting on review. I'll nudge in `#eng-core` if it sits >24h.",
    ),
    (
        "pm",
        "Thanks everyone. I'll summarize decisions in the **{project}** doc and link here.",
    ),
    (
        "creator",
        "Recording **{customer}** call notes in the wiki — @channel shout if I mis-captured "
        "the API promise.",
    ),
    (
        "support",
        "Ticket updated: customer aware of workaround until this ships. No Sev1 pressure.",
    ),
)


def arc_lines_for_count(
    arc: tuple[tuple[str, str], ...],
    n_wanted: int,
) -> tuple[tuple[str, str], ...]:
    """Take first lines from ``arc``, pad with ``COMMENT_PAD`` if we need more messages."""
    if n_wanted <= 0:
        return ()
    if len(arc) >= n_wanted:
        return arc[:n_wanted]
    extra: list[tuple[str, str]] = list(arc)
    p = 0
    while len(extra) < n_wanted:
        extra.append(COMMENT_PAD[p % len(COMMENT_PAD)])
        p += 1
    return tuple(extra)
