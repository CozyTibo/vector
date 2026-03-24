# Engineering Guidelines — Execution Intelligence Platform

This document is the **baseline contract** for how we structure code, tests, data, and shared behavior. It complements [`technical-vision-execution-intelligence-platform.md`](technical-vision-execution-intelligence-platform.md) (what we build) and **must be read together with** [`senior-standards.md`](senior-standards.md) (Python quality bar distilled from production code review).

**Normative hierarchy**

1. **This file** — project architecture, domains, testing policy, shared services, folder layout.
2. **`senior-standards.md`** — typing, complexity, SQL, migrations, logging, API details, and the **pre-MR checklist**. If anything here conflicts, **this file wins for structure and testing**; **senior-standards wins for Python idioms** unless we explicitly carve out an exception below.

---

## 1. What we optimize for

- **Clear modules (bounded contexts)** with **one obvious place** for each kind of logic.
- **Thin edges** (HTTP, CLI, workers): parse input, authenticate, call a **service**, map errors to responses.
- **Testability**: business rules live in functions/classes that accept explicit dependencies; **no hidden globals** for DB or config in domain code.
- **No drift**: ORM models, migrations, and runtime usage stay aligned; **dead tables, columns, and code are removed** in the same change that replaces them (or in a ticket-bound follow-up with a hard deadline).
- **One implementation** per cross-cutting capability (email, push, in-app notifications, webhooks to external systems): **normalize behavior** behind a small set of well-defined APIs.
- **Sustainable growth**: new features **extend** the model (new module or new slice inside a module) instead of **overlapping** existing responsibilities.
- **Small surfaces per file and per function**: avoid monolithic modules and “do everything” routines — split by **what the code does** (see §3.5).

---

## 2. Modular monolith: domains and isolation

We ship as a **single application** (initially) with **strict internal boundaries**. Each **domain** owns its vocabulary, services, and persistence **facade**; other domains interact only through **public interfaces** (see §4).

### 2.1 Current pipeline domains (v1)

These map directly to the product spec:

| Domain | Responsibility | Must not |
|--------|----------------|----------|
| **`connectors`** | Vendor HTTP/webhooks, rate limits, backfill orchestration; emit **raw ingestion commands/events** | Know canonical user/task shapes or graph schema |
| **`ingestion`** | Append-only raw storage; idempotency; payload retention; outbox for downstream | Normalize business meaning |
| **`normalization`** | Canonical entities, mapping rules, entity resolution inputs/outputs | Direct HTTP to GitHub/Jira (use connectors) |
| **`graph`** | Project canonical facts to nodes/edges; traversal indexes; rebuild/replay support | Fetch from external tools |

### 2.2 Platform / supporting domains (cross-cutting)

Shared infrastructure **is still a domain** — not a junk drawer:

| Domain | Examples |
|--------|----------|
| **`identity_access`** | Authn/z, tenant context, API keys, RBAC checks |
| **`messaging`** | Single **notification dispatcher**: email, Slack, in-app, future channels — **one entry point** (`NotificationService` / `OutboundMessagePort`) |
| **`integrations`** | Generic “call external system with retries” only if not connector-specific; prefer connectors owning vendor shape |
| **`observability`** | Structured logging helpers, tracing spans, metrics names — thin wrappers only |
| **`workflows`** (optional) | Long-running jobs, sagas, durable timers (e.g. Temporal) if we outgrow simple queues |

### 2.3 Future domains (explicit placeholders)

When we add **AI agents**, **tool execution**, or **write-back actions** to external systems:

- **`copilot` / `agents`** (name TBD): LLM orchestration, prompts, planning — consumes **read APIs** from `graph` / `normalization`, does **not** own raw truth.
- **`actions`**: Approved mutations to external systems (create ticket, comment, merge) with policy, audit, and idempotency — calls **`connectors`**, not raw HTTP scattered in agents.
- **`tools`** (if exposed as a registry): Metadata for agent-capable tools (name, JSON schema, handler id) — **handlers** live next to the domain that can satisfy them (`actions`, `connectors`).

**Rule:** If two modules both “kind of” send email or both “kind of” update Jira, **stop** — merge behind the platform service or the connector boundary.

### 2.4 Dependency direction (import rules)

Enforce **one-way dependencies**:

```text
api/ (routes, workers entrypoints)
  → application services (per domain)
    → domain logic + ports (interfaces)
      → infrastructure (DB repos, HTTP clients, queue adapters)
```

- **Domains may not import sibling domains’ internals.** Only **`contracts`** (DTOs, protocols) or **application facades** (see §4).
- **Inner layers never depend on FastAPI**, Starlette request objects, or CLI parsers.
- **Models vs schemas:** follow `senior-standards.md`: schemas do not import ORM models; expose **`to_schema()`** (or explicit mappers) from the persistence layer or DTO builders.

We recommend **import-linter** (or Ruff ecosystem rules) in CI to **fail builds** on forbidden imports between packages.

---

## 3. Layering: what belongs where

### 3.1 HTTP / async workers / CLI

**Allowed:** parse and validate input (Pydantic), resolve auth/tenant, call **one** application service method, return response or schedule job.

**Forbidden:** ORM queries, loops over business rules, direct third-party API calls (except through a **connector client** injected for the rare case), building complex graphs in the handler.

### 3.2 Application services (use cases)

**Allowed:** orchestrate steps for **one use case** (e.g. “IngestGitHubWebhook”, “RecomputeGraphProjection”), transaction boundaries, publish domain events, call repositories and external **ports**.

**Forbidden:** SQL fragments scattered as strings; knowledge of HTTP status codes (map at the edge) except when wrapping a well-typed result type.

### 3.3 Domain core

Pure or mostly-pure **rules**: normalization of a raw row given versioned rules; graph edge derivations; validation of invariants.

Prefer **explicit inputs/outputs** (dataclasses/Pydantic models), not ORM entities, inside the hardest logic — map ORM **at the repository boundary**.

### 3.4 Infrastructure

DB sessions, Alembic migrations, Redis, S3, email/SMS providers, vendor SDKs. **Implements ports** defined by application/domain layers.

### 3.5 File size, function size, and splitting by responsibility

This **reiterates and binds** the project to `senior-standards.md` §2 (cyclomatic complexity and file size). **Do not treat ~200 lines as a suggestion to break only at 201** — if a file mixes concerns or hides multiple steps, **split earlier**.

**Files**

- **Target: stay under ~200 lines per file.** If a file grows past that, **split** into additional modules whose **names describe behavior** (e.g. `map_github_user.py`, `validate_webhook_signature.py`, `graph_edge_derivation.py`), not grab-bags like `utils.py`, `helpers.py`, or `common.py`.
- **One main concern per file.** A `parse_pr_payload` module should not also **persist** rows or **publish** events — those belong in orchestration (`service.py`) calling smaller units.
- **Large domains** use **packages** (subfolders) with clear entrypoints: `normalization/github/user_mapping.py`, `normalization/jira/issue_mapping.py`, etc.

**Functions and methods**

- **No “endless” orchestration functions** that chain dozens of unrelated steps. Each step should be a **named** function or method; the use-case method **reads like a short table of contents** (validate → load → apply → persist).
- **Branching on type discriminants** (`if source == "github": ... elif source == "jira": ...`) → **extract** one function or module **per branch** (or use `match`/`case` delegating to small handlers — `senior-standards.md` §3).
- **Boolean parameters that switch behavior** are a smell — prefer **two named functions** or an explicit strategy parameter (enum / protocol), not `process(..., is_dry_run=False)` doubling all paths unless truly trivial.
- If a block **needs a long comment** to explain what it does, **make that comment the name of a function** and call it instead (`senior-standards.md` §2).

**Reviews**

- PRs that **only append** to an already large file should be challenged: **extract** in the same MR or in a follow-up with a **ticket** and deadline.

---

## 4. Public interfaces between domains (“almost like an API”)

Each domain exposes a **small surface**:

- **Service functions or classes** with verbs that match use cases: `ingestion.record_github_pr_payload(...)`, `normalization.link_jira_user_to_canonical(...)`.
- **Typed contracts only**: Pydantic models, `typing.Protocol` / ABC for ports, **no ORM leakage** across boundaries.
- **Events** (optional but recommended): `NormalizationCompleted`, `GraphEdgeAdded` — other domains subscribe through an **in-process event bus** or **outbox + worker** without importing internals.

**Anti-pattern:** domain A imports `app.domains.graph.internal.repo.GraphEdgeRepository`.

**Preferred:** domain A calls `app.domains.graph.api.GraphFacade.add_edge(command: AddEdgeCommand) -> AddEdgeResult` or posts `GraphEdgeRequested` consumed within `graph`.

---

## 5. Shared behavior: one implementation

### 5.1 Notifications, email, and outbound comms

- **Single `messaging` domain** owns:
  - Channel selection (email vs Slack vs in-app).
  - Template IDs / rendering hooks.
  - Retry and provider configuration.
- Call sites **inject** `MessagingPort` or call **`NotificationService.send(event: NotificationRequest)`** — never instantiate provider SDKs ad hoc.
- **Do not** create `mailer.py` per feature folder; **do not** duplicate “send invite” logic in three services.

### 5.2 Other “singleton” behaviors

Apply the same pattern to:

- File storage uploads
- Feature flags
- Clock/time (inject `ClockPort` in tests)
- Idempotency key store
- Distributed locks (if used)

If the same integration appears **three times**, extract (per `senior-standards.md` §20).

---

## 6. Database discipline: models, migrations, dead code

### 6.1 Single source of truth

- **Alembic migrations** and **SQLAlchemy models** must reflect each other **on every MR** that touches persistence.
- **No “shadow” columns** used only by abandoned code paths.

### 6.2 Removing fields and tables

When deprecating:

1. Stop **all** writes from application code.
2. Backfill or migrate data if needed.
3. **Remove** the column/table in a migration **together with** model + code removal in the **same release train** when safe; if multi-phase, track with a **dated removal ticket** and feature flag.

**Forbidden:** leaving commented-out columns, `TODO: remove`, or unused models “for reference.”

### 6.3 Migration safety

Follow **`senior-standards.md` §7** (nullable first, populate, then lock down; split risky migrations; realistic downgrades or intentional abstention).

### 6.4 Multi-tenant hygiene

Follow **`senior-standards.md` §6**: composite uniqueness with `tenant_id`, indexes on real query paths, filters in SQL.

---

## 7. Testing strategy

### 7.1 Levels

| Level | Scope | Speed | Database |
|-------|--------|------|----------|
| **Unit** | Pure functions, domain rules, mappers | Fast | None or in-memory fakes |
| **Integration** | Repositories vs real Postgres schema; connector adapters vs recorded HTTP | Medium | **Dedicated test DB** (see §7.3) |
| **Acceptance / E2E** | Full HTTP or worker-driven flows BLACK BOX from outside | **Slower** | **Dedicated test DB**; optional Testcontainers |

### 7.2 Test layout mirrors production layout

**Rule:** `tests/` tree mirrors `src/` (or `app/`) tree so every module has an obvious test home.

Example:

```text
src/vector/domains/ingestion/service.py
tests/vector/domains/ingestion/test_service.py

src/vector/domains/graph/projection.py
tests/vector/domains/graph/test_projection.py
```

Acceptance tests may live under `tests/acceptance/api/...` or `tests/e2e/...` but should **name the feature** and **entrypoint** clearly.

### 7.3 **Never run tests against dev/local “real” DB**

- **pytest** (or equivalent) uses a **separate database URL** e.g. `postgresql+psycopg://...@localhost:5432/vector_test`.
- **CI** creates ephemeral DB or uses isolated schema; migrations applied **before** test run.
- **Fixtures** wrap each test (or session) in transactions **or** truncate between cases — pick one strategy and document it.
- **Developers** who run integration tests locally must **not** point `DATABASE_URL` at shared dev data.

Document the exact env vars in the **repo README** (when added) or `DOCS/local-development.md` later.

### 7.4 Mocking rules

Per **`senior-standards.md` §8**: mock at **infrastructure boundaries** (HTTP, S3, SMTP), not at every private function. Prefer **fakes** for ports (e.g. `FakeMessagingPort`) over deep mocks.

### 7.5 Quality bar for tests

- **One behavioral concern per test.**
- **Lifecycle:** create → update → delete** where applicable.
- **Deterministic IDs** and **snapshot** structured outputs when they catch regressions well.
- **No `print()`**; use assertions or approved snapshot tooling.

---

## 8. Recommended repository layout (initial)

Adjust names to taste, **keep the separation**:

```text
vector/
  src/
    vector/
      domains/
        connectors/
          github/
          jira/
          ...
        ingestion/
        normalization/
        graph/
        messaging/          # single outbound comms facade
        identity_access/
      api/
        http/               # routers only
        workers/            # queue/webhook processors — thin
      contracts/            # cross-domain DTOs if needed at edges
      infrastructure/
        db/
          models/
          repositories/
        queue/
        external/
      settings.py
  tests/
    vector/
      domains/
        ...
      acceptance/
        api/
  alembic/
  DOCS/
```

**`domains/<name>/`** should typically contain: `service.py`, `ports.py`, `errors.py`, optional `events.py` — not a single 2k-line file.

---

## 9. Errors, API responses, and logging

This section **standardizes** how we **raise**, **log**, and **expose** failures. It **extends** `senior-standards.md` §3 (errors), §16 (logging), and §17 (API): follow those for Python specifics; follow **this section** for **cross-layer contracts** and **HTTP JSON shape**.

### 9.1 Principles

- **Domains stay HTTP-agnostic.** They raise **domain exceptions** (or return typed `Result` / `Either` if we adopt that pattern consistently) with **stable machine codes** — not status codes or user-facing copy meant for browsers.
- **One mapping layer** at the edge (HTTP middleware or exception handlers; worker error handler) turns exceptions into **responses** / **nacks** / **DLQ** decisions.
- **Never leak internals** to API clients: bucket names, SQL, stack traces, raw vendor payloads, secret IDs → **logs and observability only** (`senior-standards.md` §3).
- **Preserve chain**: `raise AppError(...) from e` when wrapping (`senior-standards.md` §3).
- **Guard clauses** at the top of functions; **no silent `None`** for impossible states.

### 9.2 Exception taxonomy (project convention)

Keep **custom exceptions in each domain’s `errors.py`** (or a small shared `vector/platform/errors.py` for truly generic cases). Typical categories:

| Kind | Role | Example | HTTP (public API) |
|------|------|---------|-------------------|
| **Validation** | Bad input shape/value | `ValidationError`, malformed webhook signature | **400** or **422** (prefer **422** for body/field validation with details) |
| **Authn** | Missing/invalid credentials | `UnauthenticatedError` | **401** |
| **Authz / tenancy** | Valid actor, forbidden resource | `ForbiddenError`, cross-tenant access | **403** |
| **Not found** | Entity missing | `NotFoundError` | **404** |
| **Conflict** | Idempotency or state clash | `ConflictError`, duplicate unique key | **409** |
| **Unprocessable / rule** | Business rule blocked | `InvariantViolation`, “graph rebuild already running” | **422** or **409** (pick per rule; document) |
| **Upstream / dependency** | Vendor or infra failure | `UpstreamError`, timeout talking to GitHub | **502** / **503** / **504** as appropriate |
| **Internal** | Bug or unexpected | anything uncaught | **500** with generic body |

**Workers and webhooks:** not every failure should be **5xx**. Signature failures, bad payload → **400** + log; vendor outage → **retry** with backoff; poison message → **DLQ** after N attempts **with structured log + correlation id**.

### 9.3 Standard API error body (JSON)

Public HTTP APIs should return a **consistent envelope** so clients, SDKs, and future AI tools can rely on it.

**Recommended shape** (fields optional when not applicable):

```json
{
  "error": {
    "code": "GRAPH_REBUILD_IN_PROGRESS",
    "message": "A graph rebuild is already running for this tenant.",
    "request_id": "01JQZ...",
    "details": null
  }
}
```

- **`code`**: Stable **snake_case or SCREAMING_SNAKE** machine identifier — **never change semantics** without a version bump or migration plan. Add new codes instead of overloading.
- **`message`**: Safe, **human-readable** summary for UI or logs at the client — **no secrets**, no stack traces.
- **`request_id`**: Correlation id (matches `X-Request-Id` / trace id) for support.
- **`details`**: Optional structured payload, e.g. validation: `{"fields": {"email": ["Invalid format"]}}`.

For **401/403**, keep the same envelope where possible; OAuth-style APIs sometimes use `WWW-Authenticate` headers — if we adopt that, **document** the exception.

**Success responses** stay domain-specific; only **errors** follow this envelope.

### 9.4 Validation errors (422)

- Use **field-level** detail in `details.fields` (or equivalent) aligned with OpenAPI if we publish a spec.
- **One pattern** for Pydantic validation: centralize FastAPI `RequestValidationError` handler to the same envelope (`code: "VALIDATION_ERROR"` or similar).

### 9.5 Where to raise and where to map

| Layer | Raises | Does not |
|-------|--------|----------|
| **Domain core** | Domain errors when invariants fail | Log with `logger.exception` for expected cases |
| **Application service** | May translate infra failures into `UpstreamError` / `InternalError` with `from e` | Return `None` to mean “error” |
| **Infrastructure** | Low-level exceptions (DB, HTTP) | Map to HTTP |
| **HTTP router** | Nothing (catch only if converting to streaming responses) | Implement business rules |
| **Central exception handler** | N/A | Maps exception types → status + `error` JSON |

### 9.6 Logging: what to log where

Align with **`senior-standards.md` §16**:

- Use **`logger.error("... %s", key, ...)`** with **%-formatting**, not f-strings, for compatibility with log aggregation and lazy evaluation.
- In **`except` blocks** where you need the traceback: **`logger.exception("context %s", id)`** once; avoid duplicating the same trace as both `error` and `exception`.
- **Structured context**: Prefer passing correlation id / `tenant_id` in **logging contextvars** or **extra=** (if our formatter supports it) so Sentry/CloudWatch stay queryable.
- **Expected domain failures** (e.g. “not found”): typically **INFO** or **WARNING**, not **ERROR**, unless it signals abuse or data corruption.
- **Unexpected failures**: **ERROR** + Sentry (or equivalent); include the **exception** for grouping, not a dump of every local variable in the message (Sentry already captures locals when configured).

**Rule of thumb:** **Log technical truth for operators**; **return sanitized `message` + stable `code`** to API consumers.

### 9.7 Workers, queues, and webhooks

- **Retry only** on **transient** errors (network blip, 429 with retry-after, DB deadlock). Make **idempotency** mandatory where duplicates are harmful.
- **Non-retryable** domain errors: **ack** the message and **record** failure (dead letter table or DLQ) with **error code** — do **not** spin forever.
- **Webhook signature / payload validation failure**: respond **400**, log **warning** with **request_id**, **never** enqueue poisonous work.

### 9.8 OpenAPI and clients

When we publish OpenAPI, **document** error responses per route or via shared `ErrorResponse` schema referencing the envelope above. Client SDKs and acceptance tests should assert **`error.code`**, not only status codes.

### 9.9 Tracing

- Attach **request_id** at the edge; pass through **connectors** as idempotency / vendor tracing header where supported.
- Span names should reflect **use case** (“ingestion.record_github_pr”), not only function names.

---

## 10. API and async boundaries

- **Pagination** on list endpoints; **idempotent** mutating operations where the domain allows.
- **GET for reads** unless large body forces POST (`senior-standards.md` §17).
- Workers and schedulers follow the **same service layer** as HTTP — **no duplicated business logic** “because cron.”

---

## 11. AI and automation (future-proofing)

- **Agents** receive **structured context** via graph/normalization **read APIs**, not raw SQL from prompt glue code.
- **Tool execution** that changes the world goes through **`actions` + connectors`** with audit and idempotency — **never** parallel undocumented HTTP from LLM tool stubs.
- **Prompts and models** live in `agents/` (or similar), **versioned** like normalization rules where behavior must be reproducible.

---

## 12. Pre-merge checklist (project + senior)

Before opening a PR:

1. **Domains:** Does new logic belong to **one** domain? If touching two, did you use a **facade/event** instead of reaching into internals?
2. **Edges thin?** Routes/workers free of business branches and SQL?
3. **Shared behavior:** No new duplicate mailer/notification path?
4. **DB:** Migration + model updated; dead fields removed; indexes for new queries?
5. **Tests:** Unit for rules; integration for DB; acceptance for user-visible flow; **test DB only**?
6. **Imports:** No cycles; schemas don’t import models?
7. **Errors:** New domain failures use **`errors.py`** + stable **`code`**; HTTP mapping lives in **exception handlers**, not scattered in routes; API uses the **standard error envelope**; no internal leakage in `message`.
8. **Logging:** %-formatting; **`exception`** where traceback needed; expected domain cases not logged as **ERROR** without reason.
9. **Size:** No file should sit **> ~200 lines** without a strong reason; long functions **split** into named steps; no new `utils.py` / `helpers.py` dumps — use **domain-accurate** module names (§3.5).
10. Run through **`senior-standards.md` Quick Checklist** (typing, file size, SQL, logging, booleans, etc.).

---

## 13. Exceptions and evolution

- Any **intentional** deviation from this doc or `senior-standards.md` must be **documented in the PR description** with rationale and expiry (e.g. temporary spike behind flag).
- If we split into multiple deployables later, **domain folders become packages** with explicit RPC/events — the boundaries above should survive mostly unchanged.

---

## Document history

| Date | Change |
|------|--------|
| 2026-03-24 | Initial engineering guidelines merging project intent with `senior-standards.md` |
| 2026-03-24 | Expanded §9: error taxonomy, standard API error JSON, validation envelope, logging rules, workers/webhooks |
| 2026-03-24 | Added §3.5 file/function size, splitting by responsibility; §1 and checklist updates |
