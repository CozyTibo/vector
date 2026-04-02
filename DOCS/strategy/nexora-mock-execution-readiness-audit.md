# Nexora mock dataset — execution & insight readiness audit

**Date:** 2026-04-01  
**Method:** Read-only inspection of `company_generator.py`, `nexora_content.py`, `seed_config.py`, and **empirical metrics** from `generate_dataset(42)` (no generator changes).  
**Related:** [`mock-data-seed-audit.md`](./mock-data-seed-audit.md), [`local-mock-connectors-and-fixtures.md`](./local-mock-connectors-and-fixtures.md).

---

## 1. Dataset narrative integrity

### Single coherent company story

**Yes, at the narrative layer.** `NEXORA_BLURB` and [`PROJECT_BLUEPRINTS`](../../backend/mock_connectors/fixtures/nexora_content.py) describe one B2B product (workspace, connectors, SOC2, billing, data platform, mobile, etc.). Per-team [`ISSUE_SCENARIOS`](../../backend/mock_connectors/fixtures/nexora_content.py) keep issue titles and bodies in that domain (API idempotency, webhooks, SSO, mobile push, warehouse/GDPR, design system, and so on). **Comments** use shared templates (customers, legal, rollout, QBR) that read as one company.

### Alignment caveats (important)

| Question | Finding |
|----------|---------|
| Same product surface across issues? | **Mostly yes** in copy; occasional **hygiene** rows (`Untitled / missing triage title`, typos) are intentional noise. |
| Repo names vs narrative? | Repos in `seed_config.REPO_NAMES` (`api`, `auth-service`, `web`, …) **fit** the product story. |
| Linear project ↔ GitHub repo? | **No semantic mapping.** Project names come from `PROJECT_BLUEPRINTS` (12 initiatives), assigned by issue index; they **do not** name a “owning” GitHub repo. A WEB-team issue can sit under project *Billing & usage metering accuracy* while the **linked** PR repo follows index parity (below). |
| Issue index ↔ PR repo? | **Aligned for the default link.** For PR index `p` with `li = linear_issues[p]`, the issue’s index is `p` and `repo_full` in the generator is `repos[p % len(repos)]`, matching the PR’s repo. **Exceptions:** multi-repo extras, PRs with **no** ticket (`p % 7 == 0`), and deliberate wrong links in description (NEX-43). Not every issue template prints `` `nexora/...` `` in the body. |
| Domain themes? | **Strong:** billing, auth/sessions, infra/SLOs, integrations, web perf, mobile, data/GDPR, design system, API partnerships. |

### Five concrete issue → PR → repo flows (seed `42`)

These are **real rows** from the generator. “Looks like real work” on **ticket copy**; **repo alignment** is often arbitrary (see NEX-2).

1. **NEX-7** — *POST /v1/import: validate schema before enqueue (fail fast)* — **Team:** CORE — **Project:** *Billing & usage metering accuracy* (blueprint; not a repo name) — **PR:** `nexora/integrations#7` `[NEX-7] fix thing` — **Commits:** `NEX-7: commit 0`, … — **Reads as:** credible API/support ticket; **PR repo** follows issue index (`repos[6]` → `integrations`).

2. **NEX-10** — *EU cluster: HPA scales up too late for morning traffic ramp* — **PLAT** — **PR:** `nexora/auth-service#10` — Commits `NEX-10: commit 0/1` — **Reads as:** platform narrative; repo is **index-aligned** with the issue, but **product-wise** HPA work living on `auth-service` is a mild story stretch (not a generator bug).

3. **NEX-12** — *Untitled / missing triage title* — **DATA** — **PR:** `nexora/design-tokens#12` with title equal to full Linear title — Commits `NEX-12: commit 0/1` — **Reads as:** triage/hygiene scenario, not polished delivery.

4. **NEX-51** — *Offline: stale board cache shows completed work as …* — **MOB** — **Primary PR:** `nexora/web#51` `[NEX-51] fix thing` — **Plus multi-repo pattern:** `nexora/api#121` `[NEX-51] multi-repo 0` (merged) and `nexora/auth-service#122` `[NEX-51] multi-repo 1` (open/draft) — **Reads as:** strong **one ticket, multiple PRs** example.

5. **NEX-43** — *Session refresh: race leaves user on blank shell after org switch* — **CORE** — **Description** includes a deliberate **wrong** GitHub link (`wrong-repo/pull/1`) — **Many issues have no PR**; NEX-43 is in the **no-PR** set for seed 42 — **Reads as:** good **messy link / shadow planning** narrative; **no** paired PR for graph closure.

**Verdict (§1):** Coherent **product** story; **weak** **Linear project ↔ service/repo** semantics (blueprint vs team vs repo); **strong** **issue↔PR repo** alignment for the default `p`-linked PRs.

---

## 2. Role diversity audit

### Actors in `_RAW_USER_SPECS` (first `TARGET_USERS` = 15)

| Name (login) | Role in data | GitHub | Linear |
|--------------|--------------|--------|--------|
| Thibault Hagler (`thagler`) | engineering | Yes | Yes |
| Victoire Charlet (`vcharlet`) | product | No | Yes |
| Alex Kim (`akim`) | engineering | Yes | Yes |
| Sam Rivera (`srivera`) | engineering | Yes | Yes |
| Jordan Lee (`jlee`) | engineering | Yes | Yes |
| Taylor Moss (`tmoss`) | engineering | Yes | Yes |
| Riley Chen (`rchen`) | engineering | Yes | Yes |
| Casey Nguyen (`cnguyen`) | engineering | Yes | Yes |
| Morgan Blake (`mblake`) | engineering | Yes | Yes |
| Nexora Bot (`nexora-bot`) | bot | Yes | Yes |
| Pat Freelance (`pfreelance`) | contractor | Yes | Yes |
| Jamie Intern (`jintern`) | intern | Yes | Yes |
| Sam Support (`ssupport`) | support | No | Yes |
| Riley Design (`rdesign`) | design | No | Yes |
| Slack Only (`slackonly`) | other | No | Yes |

### Checklist vs your role list

| Role you asked for | Present? | Notes |
|--------------------|----------|--------|
| Engineer | Yes | Multiple; primary GitHub authors. |
| Product manager | **Proxy:** `role: product` (Victoire) — no separate `project_manager` label. |
| Support engineer | Yes (`ssupport`) — **Linear only** on GitHub. |
| Engineering manager | **No dedicated user** — nobody with `engineering_manager` or similar; only generic `engineering`. |
| Project manager | **Not distinct** from product in specs. |
| Design | Yes (`rdesign`) — Linear only. |
| Bot | Yes (`nexora-bot`). |

### System presence (summary)

- **Linear-only (no GitHub activity):** product, support, design, slack-only — enforced by `_assert_no_github_activity_for_linear_only_users`.
- **Contractor / intern:** **GitHub + Linear** (not “GitHub only”).
- **“EM, Linear + GitHub”:** **Not modeled** as a separate persona; pick an engineer if you need a stand-in.

---

## 3. Cross-tool execution paths

Metrics (**seed 42**): **122** PRs; **104** PRs mention a `NEX-*` key in title/body; **18** without; **280** issues; **102** identifiers appear on ≥1 PR; **178** issues have **no** PR.

### Ten examples: Linear issue → GitHub PR → commits

| # | Issue | PR | Sample commits |
|---|-------|----|----------------|
| 1 | NEX-2 — Empty state for new workspace… | `nexora/auth-service#2` | `NEX-2: commit 0`, `NEX-2: commit 1` |
| 2 | NEX-3 — [Spike] Offline: stale board cache… | `nexora/web#3` | `NEX-3: commit 0`, `NEX-3: commit 1` |
| 3 | NEX-4 — Deploy freeze calendar… | `nexora/design-tokens#4` | `NEX-4: commit 0`, … |
| 4 | NEX-5 — Integration health dashboard… | `nexora/mobile#5` | `NEX-5: commit 0`, … |
| 5 | NEX-6 — Streaming job: late events… | `nexora/infra#6` | `NEX-6: commit 0`, … |
| 6 | NEX-7 — POST /v1/import… | `nexora/integrations#7` | `NEX-7: commit 0` |
| 7 | NEX-9 — iOS: push notification… | `nexora/api#9` | `NEX-9: commit 0`, … |
| 8 | NEX-10 — EU cluster: HPA… | `nexora/auth-service#10` | `NEX-10: commit 0`, … |
| 9 | NEX-11 — Linear import: duplicate labels… | `nexora/web#11` | `NEX-11: commit 0`, … |
| 10 | NEX-12 — Untitled / missing triage… | `nexora/design-tokens#12` | `NEX-12: commit 0`, … |

### PR without Linear issue

`p % 7 == 0` drops the Linear pick. Examples: `nexora/api#1` *chore: cleanup*, `nexora/data-pipeline#8` *drive-by rename*, `nexora/integrations#15` *drive-by rename*.

### Linear issue without PR

Any identifier not appearing in any PR title/body — e.g. **NEX-1**, **NEX-8**, **NEX-280** (large set: **178** issues).

### Messy linking

| Pattern | Present? | Example |
|---------|----------|---------|
| Wrong / misleading link in issue body | Yes | **NEX-43** — `wrong-repo/pull/1` ([`company_generator.py`](../../backend/mock_connectors/fixtures/company_generator.py) `i == 42`) |
| Multiple PRs for one issue | Yes | **NEX-51** — `web#51`, `api#121`, `auth-service#122` |
| Issue “implies” one repo, PR another | **Rare for linked PRs** | Same index → same `repos[i%8]`; intentional breaks: **multi-repo**, **no-ticket** PRs, **wrong link** in body |

---

## 4. Timeline realism

**Configured window:** `t0 = 2025-10-01T12:00:00Z`, `end = t0 + SIMULATION_DAYS` (75 days) in [`generate_dataset`](../../backend/mock_connectors/fixtures/company_generator.py).

**Observed span (all issue/comment/epic/PR/commit timestamps, seed 42):**

- **Earliest:** 2025-10-01T12:00:00+00:00  
- **Latest:** 2025-12-14T08:00:00+00:00  
- **Total span:** ~**73.8 days** (matches `SIMULATION_DAYS`).

### What the generator actually models

| Signal | Realistic? | Mechanism |
|--------|------------|-----------|
| Bursts of commits | **Partial** | 1–8 commits per PR, hours apart from PR `created_at`. |
| Quiet periods | **Weak** | No explicit “team idle week”; orphan commits fill to `TARGET_COMMITS`. |
| PR review delay | **One standout** | PR index `p == 3` → `updated_at - created_at` = **30h** ([`company_generator.py`](../../backend/mock_connectors/fixtures/company_generator.py)). |
| Issues idle | **Capped** | `updatedAt = next_time(created)` with **0–14 days** after `createdAt` — **not** weeks of silence. |
| Comments weeks later | **No** | Comments start **1h** after issue creation, then **~6h** steps per message in thread. |

### “Stuck” in a state for a long time?

**Not in the sense of “Todo for 41 days.”** State is `workflow_states[i % len(workflow_states)]` — **independent of age**. `updatedAt - createdAt` is **at most ~14 days** by construction. Examples like “NEX-88, Todo, last updated 41 days ago” **do not exist** unless you change the generator.

**Interpretation:** Good for **volume and variety of states**; **poor** for **dwell-time / aging** execution insights.

---

## 5. Execution failure scenarios

| Scenario | Exists? | Evidence (seed 42) |
|----------|---------|---------------------|
| PR waiting review >24h | **Yes** | PR **#4** (`p==3`): **30h** between `created_at` and `updated_at`. |
| Issue Done but PR open | **Yes** | e.g. **NEX-5** Done + `nexora/mobile#5` open; **9** such pairs found by scanning linked PRs. |
| PR merged but issue still open | **Yes** | **52** cases (e.g. **NEX-2** Todo + merged PR on `auth-service#2`) — common because **Linear state and GitHub merge are not coupled**. |
| Cross-team dependency | **Yes** | All **`blocks`** edges are **cross-team** (see §6): **38** cross-team, **0** same-team. |
| Duplicate issues | **Intended in code, absent in data** | Loop requires **consecutive** issues same team; teams rotate by index → **0** `duplicate` relations emitted. **Bug / design flaw** vs `pattern_coverage` claiming `duplicate_work`. |
| Issue reopened | **No** | No state history; no `reopened` event. |
| PR abandoned | **Partial** | Open PRs with **7–10 days** `updated - created` exist; **no** rule for >7d **inactive** across all open PRs. PR **#17** stuck unmerged is explicit. |
| Epic open after all children closed | **No** | No epic found In Progress with all children Done (for epics with 2+ children); conversely no Done epic with open children in this scan. |
| Work without ticket | **Yes** | **18** PRs with no `NEX-*` in title/body; plus orphan commits (`_pr: None`). |
| Customer bug / support | **Yes** | Support **comment arcs** reference **{customer}**; **Bug** label on `i % 6 == 0` issues. |

---

## 6. Dependency graph depth (Linear `issueRelations`)

**Counts (seed 42):** **38** `blocks`, **20** `related`, **0** `duplicate` — **58** total.

**Longest `blocks` chain (following `issue → relatedIssue` as directed):** length **3**, e.g. **NEX-7 → NEX-8 → NEX-10** (identifiers depend on issue ordering; structure is shallow).

**Cross-team:** Every `blocks` edge connects **different teams** (API/UI pairing and `i`/`i+2` jumps across team rotation).

**Realism:** Matches **handful of dependencies**, not deep critical-path DAGs. Good for **simple cross-team signals**; **not** deep program-management graphs.

---

## 7. Comment realism

**Distribution:** `comment_distribution` → **720** comments / **280** issues → **min 2, max 3, mean ~2.57** comments per issue.

**Thread depth:** Arc templates are **3-turn** dialogues; padding uses [`COMMENT_PAD`](../../backend/mock_connectors/fixtures/nexora_content.py). **Not** deep Slack-style threads.

**Timing:** All comments on an issue sit in the **first ~hours to ~1–2 days** after issue `createdAt` (1h + 6h steps), **not** weeks apart.

**Roles:** Templates include **pm**, **assignee**, **eng**, **design**, **support**, **contractor**, **intern**, **bot**, **creator**. Authors resolved via `_pick_user` (e.g. design → `rdesign` when team matches; support → `ssupport` or team support).

**Examples (archetypes in `COMMENT_ARCS`):**

- **PM / ETA / scope:** e.g. soft-delete vs hard-delete renewal scope (first arc).  
- **Engineer response:** assignee explains schema / TTL.  
- **Escalation-like:** support + PM + design on **incident banner** vs status page truth.  
- **Support + customer:** Slack connectivity / webhook 401 arc.

**Verdict:** **Strong scripted realism** for demos; **synthetic** in timing (compressed) and **shallow** depth.

---

## 8. Graph structure validation

| Canonical structure | In dataset? | Strength |
|--------------------|-------------|----------|
| Actor → Issue | Yes | Assignee/creator on issues. |
| Actor → Comment → Issue | Yes | Comments carry `user`, `issueId`; edges include `commented`. |
| Issue → Epic → Project | **Partial** | **~94/280** issues have `parent` epic; rest unparented. |
| Issue → blocks → Issue | Yes | **38** edges (cross-team). |
| PR → Commit | Yes | `pr_commits` map; commits include `_pr`, `_repo`. |
| PR → Repository | Yes | `base.repo.full_name`, `_repo_full`; edges `pr_repo` (**from** is PR **number** string — weak global ID). |
| Actor → PR | Yes | `user` on PR; commit `author`. |

**Weakest links for a general execution graph:** PR–issue link is **text parsing** (`[NEX-*]`, `Closes` sometimes); **no** guaranteed foreign key from GitHub to Linear.

---

## 9. Signal generation potential

| Signal | Supported? | Example (seed 42) |
|--------|------------|-------------------|
| Review bottleneck | **Yes (single)** | PR **#4** — 30h update lag. |
| Cross-team dependency delay | **Structural only** | `blocks` edges are cross-team; **no** time-series “blocked duration.” |
| Shadow work (PR without ticket) | **Yes** | `nexora/api#1` *chore: cleanup* (no `NEX-*`). |
| Execution hygiene | **Yes** | Wrong link on **NEX-43**; empty/triage titles; typo hygiene in bodies. |
| Duplicate work | **Claimed, not in relations** | **0** duplicate relations — use **similar titles** only if your detector reads text. |
| Planning drift | **Yes (fixture)** | Slack `#eng-random` — work discussed **without** `linear_issue_id` (`discussion_drift`). |

---

## 10. Dataset weaknesses — top 10 generator improvements (prioritized)

1. **Dwell time / state realism** — Tie `state` and `updatedAt` to intended scenarios (Todo 30d, In Review 5d, etc.).  
2. **Align Linear ↔ GitHub timelines** — For chosen golden issues, merge/close/comment ordering across tools.  
3. **Fix duplicate relations** — Same-team duplicate edges never fire today; repair indexing or explicit pairs.  
4. **Project ↔ service coherence** — Optionally map each Linear **project** (blueprint) to a **primary** repo for demos; today only **issue index ↔ repo** is consistent with the default PR link.  
5. **Distribution of review delays** — Not only `p==3`; add percentiles and requested reviewers when you ingest them.  
6. **Issue reopened + epic closure rules** — State transitions or at least historical events.  
7. **Deeper dependency chains** — Optional DAG generator for length >3.  
8. **Comment spacing** — Allow multi-week gaps for “silent ticket” signals.  
9. **Explicit EM / PM roles** — If insights need manager vs IC separation in assignee/creator mix.  
10. **Stable cross-tool IDs** — e.g. metadata or body conventions for golden tests beyond regex on titles.

---

## 11. Final readiness verdict

### Verdict: **READY WITH IMPROVEMENTS**

The Nexora mock is **ready** as the **primary dev environment** for **building** the execution graph (volume, cross-tool text links, comments, relations, mixed hygiene, Slack fixtures).

It is **not yet ready** as a **calibrated benchmark** for **time-based execution and insight detection** (dwell, reopen, duplicate graph, aligned lifecycles, review distributions) without the improvements above.

### Impact-ranked follow-ups

1. **Time + state coupling** (unlocks most aging/stuck insights).  
2. **Golden cross-tool lifecycles** (validates end-to-end graph logic).  
3. **Duplicate relation fix + explicit multi-PR/unticketed scenarios** (matches `pattern_coverage` claims).  
4. **Repo/project coherence** (reduces false “wrong repo” when you want true positives).  
5. **Role expansion (EM)** if persona-specific insights matter.

---

## Appendix: code references

- Fixed clock: `t0 = datetime(2025, 10, 1, …)` in `generate_dataset`.  
- Issue state: `workflow_states[i % len(workflow_states)]`.  
- PR–Linear link: `li = linear_issues[p % len(linear_issues)] if p % 7 != 0 else None`.  
- Relations: API/UI `blocks`, data/core `related`, duplicate loop gated on **consecutive same-team** (never true with rotating teams).
