# Mock data seed — full audit

**Purpose:** Single reference for what the Nexora mock dataset contains, how it flows through the stack today, and how to improve it for execution / insight testing.

**Scope:** Local development only (`VECTOR_USE_MOCK_CONNECTORS=true`, `ENV=development`). Production, CI, and AWS use real vendor APIs.

**Related docs:** [`local-mock-connectors-and-fixtures.md`](./local-mock-connectors-and-fixtures.md) (strategy), [`backend/mock_connectors/README.md`](../../backend/mock_connectors/README.md) (runbook), [`nexora-mock-execution-readiness-audit.md`](./nexora-mock-execution-readiness-audit.md) (execution realism & signal coverage, read-only analysis).

---

## 1. Executive summary

| Area | Status |
|------|--------|
| **Scale & determinism** | Strong: integer `VECTOR_MOCK_SEED`, fixed targets in `seed_config.py`. |
| **Narrative (company, tickets, comments)** | Strong: `nexora_content.py` + `company_generator.py` — realistic B2B product copy, PM/eng split, messy hygiene. |
| **Cross-tool structure** | Good: Linear↔GitHub title links, relations (blocks/duplicate/related), Slack fixture events. |
| **Named “scenario” tags** | Partial: `pattern_coverage` lists intent; not all strategy §11 rows are **time-accurate** in the JSON. |
| **Temporal / dwell-time signals** | **Improved:** `execution_stories.py` drives **per-issue timelines** (multi-day gaps, review delays, shadow work, misaligned merge/close). Still not full vendor state history. |
| **Step 1 dedupe (resync)** | Partial: `linear.issue` + `linear.comment` use watermarks; other Linear types still append every sync. |

**Bottom line:** The seed is **strong for volume, copy, graph shape, and deterministic execution scenarios** (normal delivery, review bottleneck, cross-team block, shadow work, duplicates, misaligned completion, abandoned PR, epic drift, SOC2 / mobile initiatives, 5-level `blocks` chain). Remaining gaps: no **historical** Linear/GitHub state transitions in payloads, Step 1 watermark coverage unchanged.

---

## 2. File map (source of truth)

| Path | Role |
|------|------|
| [`backend/mock_connectors/fixtures/seed_config.py`](../../backend/mock_connectors/fixtures/seed_config.py) | Scale targets (`TARGET_*`), org/repo/team names, simulation window (`SIMULATION_DAYS`). |
| [`backend/mock_connectors/fixtures/nexora_content.py`](../../backend/mock_connectors/fixtures/nexora_content.py) | Product blurb, customers, 12 project blueprints, per-team issue scenarios, epic verbs/outcomes, comment **arcs** (multi-turn threads). |
| [`backend/mock_connectors/fixtures/company_generator.py`](../../backend/mock_connectors/fixtures/company_generator.py) | Orchestrates `generate_dataset(seed)` → execution bundle → Linear + GitHub + Slack + `edges` + `pattern_coverage`. |
| [`backend/mock_connectors/fixtures/execution_stories.py`](../../backend/mock_connectors/fixtures/execution_stories.py) | **Execution story layer:** per-issue plans (timestamps, state, PR shape, relations, comment spacing), orphan PRs (shadow work), PR budget trim, golden slots (indices 0–10, 160–164, 200–227). |
| [`backend/mock_connectors/fixtures/generated/dataset.json`](../../backend/mock_connectors/fixtures/generated/dataset.json) | Optional checked-in or generated snapshot (often gitignored); same shape as in-memory data. |
| [`backend/mock_connectors/runtime_state.py`](../../backend/mock_connectors/runtime_state.py) | Process memory: `generate_dataset(VECTOR_MOCK_SEED)` at startup. |
| [`backend/mock_connectors/unified.py`](../../backend/mock_connectors/unified.py) | FastAPI app: GitHub REST + `/linear/*` + mock `/admin/*`. |
| [`backend/mock_connectors/github_mock/`](../../backend/mock_connectors/github_mock/) | REST list endpoints + pagination (`Link` headers). |
| [`backend/mock_connectors/linear_mock/dataset_generator.py`](../../backend/mock_connectors/linear_mock/dataset_generator.py) | GraphQL dispatch by `operationName`; issues/comments sorted `updatedAt` desc for watermark tests. |
| [`backend/mock_connectors/scripts/generate_dataset.py`](../../backend/mock_connectors/scripts/generate_dataset.py) | Writes `dataset.json`. |
| [`backend/mock_connectors/scripts/validate_mock_dataset.py`](../../backend/mock_connectors/scripts/validate_mock_dataset.py) | Validates **live generator output** (default): scenarios, link styles, `blocks` depth ≥5, duplicates, EM comments, PR open/closed mix. Set `MOCK_VALIDATE_USE_JSON=1` to validate checked-in `dataset.json` instead. |

---

## 3. Quantities (default seed `42`)

Defined in `seed_config.py` (truncated by `TARGET_*` when smaller lists are used):

| Entity | Target | Notes |
|--------|--------|--------|
| Simulation window | **120 days** | `SIMULATION_DAYS` in `seed_config.py` (anchor `t0` + spread). |
| Repositories | 8 | `REPO_NAMES`; one may be `archived`. |
| Users | 16 | Adds **engineering manager** (`scollins`); roles: eng / EM / product / design / support / bot / contractor / intern / slack-only; **some Linear-only (no GitHub activity)**. |
| Teams | 6 | `TEAM_NAMES` → Linear teams + workflow states each. |
| Projects | 12 | From `nexora_content.PROJECT_BLUEPRINTS`. |
| Epics | 45 | Titles from epic verb/outcome × project/team context. |
| Issues | 280 | Scenarios from `ISSUE_SCENARIOS` per team key. |
| PRs | 120 | Linked to Linear issues sometimes; drafts/outliers on specific indices. |
| Commits | 800 | PR-attached + orphan branch commits. |
| Comments | 720 | **Threads** per issue (distribution + arcs from `nexora_content`). |
| Issue relations | ~58+ | Keyword-based blocks (API→UI), related (DATA↔CORE), duplicates, chains — not fixed to `TARGET_*`. |
| Graph edges (dataset) | Padded toward **2000** | Mix of Linear relations, comments, PR→repo, issue→project. |
| Slack events | 3+ | Base 2 + **shadow-work** story line (`execution_stories`); still not Slack API. |
| GitHub issues (non-PR) | 35 | Simple discussion stubs. |

**Mock HTTP admin:** `GET http://<mock>:9183/admin/dataset` returns live counts after reseed.

---

## 4. How the dataset is produced

1. **`generate_dataset(seed)`** (`company_generator.py`)  
   - `random.Random(seed)` for remaining stochastic fields (priority, labels, hygiene).  
   - **`execution_stories.build_execution_bundle`** builds one **`IssueExecutionPlan` per issue** (and **orphan PRs** for shadow work), then **trims** issue-linked PRs to fit `TARGET_PRS` while preserving golden indices.  
   - **Users** → **repos** → **Linear** (`_build_linear`): teams, states, projects, epics; issues use **team-scoped workflow states**, plan timestamps, `metadata.scenario`, optional **`github_pr_number`**, story-driven **relations** (duplicate, blocks, cross-team block), **SOC2 / mobile / epic-drift** parentage bands, comment times from **plan offsets** (with EM-authored slots).  
   - **GitHub** (`_build_github`): collects **orphan + issue PRs**, sorts by `created_at`, assigns PR numbers; **link styles** `title_ref` / `body_closes` / `issue_field_only` / `none`; optional **`_mock_pr_reviews`** (EM); filler PRs to `TARGET_PRS` − 2, then **multi-repo** extras.  
   - **`_execution_bundle`** is attached during build and **stripped** in `dataset_to_json_dict` / `runtime_state` so JSON/API payloads stay clean.  
   - **Slack** (`_build_slack`): base fixtures + story extras.  
   - **edges**, **`pattern_coverage`** (metadata + legacy slugs).

2. **Narrative injection**  
   - Same as before: **`nexora_content`** titles/bodies/epic/comment arcs; hygiene noise preserved.

3. **Runtime**  
   - Unchanged: in-memory data via `dataset_to_json_dict(generate_dataset(seed))`.

4. **Optional JSON**  
   - `scripts/generate_dataset.py` writes `dataset.json` **without** `_execution_bundle`.

---

## 5. How Vector uses the seed today

### 5.1 Configuration (`settings.py`)

| Traffic | Mock mode | Real API |
|---------|-----------|----------|
| GitHub REST (poll sync, install token POST) | `VECTOR_MOCK_CONNECTOR_BASE_URL` | `https://api.github.com` |
| GitHub App JWT **GET** `/app/installations/{id}` | **Always** `https://api.github.com` | Same |
| Linear GraphQL (Step 1 ingestion) | `{base}/linear/graphql` | `https://api.linear.app/graphql` |
| Linear OAuth token + post-auth viewer/org | Always real Linear hosts | — |

So: **connect** hits real GitHub/Linear where required; **bulk Step 1** can hit the mock.

### 5.2 Step 1 ingestion

- **GitHub:** `github_poll_sync` — per-repo watermarks (`connector_sync_state`) for pulls/issues/commits where implemented.  
- **Linear:** `linear_graphql_sync` — **watermarked incremental** for `linear.issue` and `linear.comment` only (`orderBy: updatedAt` + skip ≤ watermark). Other resource types **full pagination each run** → **row growth on every resync** for those types.  
- **Raw storage:** `raw_ingestion_records` + `ingestion_runs`; idempotency is **per run**, so new runs always *attempt* new inserts unless skipped upstream.

### 5.3 Admin / dev UX

- **Vector Admin → Step1 Raw:** lists raw rows; **Reset Step 1 raw** (typed phrase) wipes `ingestion_runs`, cascaded raw rows, and `connector_sync_state` for the tenant — **no connector pull**.  
- **Mock server:** `/admin/reseed`, `/admin/dataset`, `/admin/scenarios`.

### 5.4 Downstream (Step 2 / 3)

- Ingestion still sees **snapshots** (current issue state, PR `merged_at`, etc.). The generator now **aligns many golden stories** in the fixture JSON itself; there is still no **event log** of intermediate transitions unless you add it later.

---

## 6. Scenario / pattern coverage (`pattern_coverage`)

`_verify_patterns` unions **legacy §11 slugs** with **`metadata.scenario`** on issues/PRs/Slack entries.

| Slug / scenario | Implemented (high level) | Fidelity notes |
|-----------------|--------------------------|----------------|
| `normal_delivery`, `review_bottleneck`, `misaligned_completion`, `abandoned_pr`, … | Golden indices + bulk rotation via **`execution_stories`** | Deterministic offsets (hours–days); not a statistical distribution. |
| `shadow_work` | Orphan PR → Slack → Linear **NEX-5** + `github_pr_number` | End-to-end fixture path. |
| `duplicate_work_a` / `b` | **`duplicate`** relation + metadata | Plus same-team stagger duplicates for volume. |
| Cross-team delay | **NEX-4** blocks **NEX-3** (`blocks` edge); CORE blocks WEB | A (WEB, NEX-3) waits on B (CORE, NEX-4): **blocker blocks blockee**. |
| `initiative_soc2` / `mobile_offline` | Issues **200–209** / **210–217**, linked projects | Large clusters. |
| `epic_drift_child` | Issues **218–227** under epic **NEX-212**, epic left **In Progress** | All children **Done** in snapshot. |
| `untracked_pr` / `filler_untracked` | PR `link_style: none` | Explicit in metadata. |
| `multi_repo_change` | Extra PRs for `linear_issues[50]` | Unchanged tail of `_build_github`. |
| `discussion_drift` / `cross_tool_ping` | Slack fixtures | Still not Slack API. |

---

## 7. Timeline & execution realism (updated)

### 7.1 Linear issues

- **State:** **Team-scoped** workflow state chosen from the execution **plan** (`Done`, `In Review` for abandoned paths, etc.), not a global index cycle.  
- **Timestamps:** `createdAt` / `updatedAt` come from **story simulation** over **`SIMULATION_DAYS` (120)**; multi-week separation is possible on golden rows.

### 7.2 GitHub PRs

- PR **`created_at` / `updated_at` / `merged_at`** derived from issue anchors + plan offsets; **abandoned** PRs stay open with last commit time.  
- **`_mock_pr_reviews`**: optional EM review notes (ignored by stock GitHub REST clients; safe for forward-compatible tooling).

### 7.3 Comments

- Times follow **plan `comment_offsets_h`** (hours → multi-day gaps), clamped not to exceed issue `updatedAt`. **EM** replaces selected thread lines with ETA / people-management copy.

### 7.4 Strategy doc §12

- Golden **shadow** and **cross-team** rows approximate §12-style sequencing; bulk rows follow templates, not a single scripted day-by-day narrative for every entity.

---

## 8. Identity & org realism

- **Linear-only users** (PM/design/support): appear in Linear, **absent** from GitHub PR/commit authorship (asserted in generator).  
- **Messy identity:** duplicate `displayName`, bad emails, optional empty GitHub profile name.  
- **Customers:** Named accounts in issue text for CSM / QBR scenarios.

---

## 9. Validation & tests

- **`validate_mock_dataset.py`:** Repo/PR integrity, commit `_repo`, chronological `createdAt`/`updatedAt` on issues, soft scale checks.  
- **Settings:** `test_mock_connectors_env.py` — mock only in development; URL split assertions.  
- **No** automated test that every §11 pattern is **detectable** by a specific metric (opportunity).

---

## 10. Gaps and improvement backlog (prioritized)

### P0 — Execution insight calibration

1. **Time-in-state cohorts:** For a configurable fraction of issues, set `(state, createdAt, updatedAt)` so that e.g. “Todo + `updatedAt` 45d ago” vs “Todo + `updatedAt` 1d ago” is **guaranteed**.  
2. **PR lifecycle bands:** Open PRs with (a) no activity 14d+, (b) active last 24h, (c) approved-but-not-merged (when API fields exist), (d) draft forever.  
3. **Cross-tool alignment:** Pick **golden paths** (issue id X): scripted timestamps so PR merge / issue close / comment sequence matches a §12 row.

### P1 — Step 1 hygiene for local iteration

4. **Extend Linear watermarks** to `issueRelations`, `projects`, `labels`, … (or document “expected growth”).  
5. **Tag mock rows** with `_scenario` or stable `external_id` prefixes for golden tests (strip before “production parity” if needed).

### P2 — Richer vendor shapes

6. **GitHub:** requested reviewers, review submissions, check runs (subset).  
7. **Linear:** history / state transition timeline if consumed later.

### P3 — Documentation & tooling

8. **Scenario manifest:** Machine-readable YAML listing pattern → example `external_id`s / queries.  
9. **Replay pack:** Export one tenant’s Step1 raw JSON as **fixture** for projection unit tests.

---

## 11. Quick reference commands

```bash
# Regenerate JSON snapshot (optional)
cd backend && uv run python mock_connectors/scripts/generate_dataset.py

# Validate
uv run python mock_connectors/scripts/validate_mock_dataset.py

# Mock server summary (server running)
curl -s http://127.0.0.1:9183/admin/dataset | jq
curl -s http://127.0.0.1:9183/admin/scenarios
```

---

## 12. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-04-01 | — | Initial audit document. |
| 2026-04-01 | — | Execution story layer (`execution_stories.py`), EM user, deeper `blocks` chain, validation defaults to live generator, `SIMULATION_DAYS=120`, `TARGET_USERS=16`. |
