# Action system — architecture guideline (V0 + LLM-ready)

**Status:** implementation-ready reference.  
**Audience:** backend engineers.  
**Stack:** Python, FastAPI — must fit `vector/api/http/routes`, `vector/contracts`, `vector/domains`, `vector/application/services`, `vector/infrastructure`, Celery.

**V0 companion:** [`v0_action_system.md`](./v0_action_system.md) is normative for the **Slack → `report.user`** slice (e.g. **`window_days` only**, Slack **`response_url`** execution model, parallel-fetch DB rules). If **§9** below uses date-based windows for illustration, **V0 implementations MUST follow the companion** (companion §1.1).

---

## 1. What is an Action

An **Action** is a **named, backend entry point** for doing one unit of imperative work. It:

- Is registered under a **stable** `name` (long-term API).
- Declares **typed** I/O via **Pydantic `input_model` / `output_model`** (see §2).
- Implements a `**handler**` with a **mandatory** signature (see §2.1).
- **Orchestrates** domain `*_commands`, domain services, application services, and (where already permitted) repositories / connectors / ingestion reads.
- Is callable identically from **Slack (V0)** and from an **LLM tool runtime (future)** — only adapters differ.

**Action ≠ domain logic.** Domain modules own invariants, state machines, normalization, and transactional boundaries. The Action validates I/O at the boundary and delegates.

**Action ≠ LLM.** Only `**type == "llm"`** Actions invoke a model to **generate text** from structured input. Other types **must not** call LLM client libraries directly; they **may** call a registered `**llm`** Action via the **executor** (composition).


| Concept                                                | Owns                                                                                                           |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **Domain**                                             | Business rules, persistence orchestration, errors with semantic meaning                                        |
| **Action**                                             | Stable contract, `ActionContext`, permission tags, input/output validation, dispatch, composition via executor |
| **LLM** (only inside registered `type=="llm"` Actions) | Non-deterministic natural-language generation from fixed structured input                                      |


---

## 2. Action specification (strict)

### 2.1 Mandatory handler signature

**Every** Action handler **MUST** use exactly this shape (sync or async body allowed; if async, executor awaits):

```python
def handler(db: Session, ctx: ActionContext, payload: InputModel) -> OutputModel: ...
```


| Parameter | Rule                                                                                                                                                                    |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `db`      | `sqlalchemy.orm.Session` — passed by executor; not part of payload.                                                                                                     |
| `ctx`     | `**ActionContext**` — **required**, **never** `Optional`; same contract weight as `input_model`. Built only by trusted adapters (Slack route, HTTP route, LLM gateway). |
| `payload` | Instance of this Action’s `**input_model`** — business inputs only.                                                                                                     |


**Return:** instance of this Action’s `**output_model`** (executor validates).

Handlers **MUST NOT** use `*args`, `**kwargs`, or alternate parameter layouts for the public Action boundary.

---

### 2.2 Global contract: `ActionContext` (first-class, not optional)

Define **once** in shared contracts (e.g. `vector/contracts/actions/context.py`). **Do not** redefine per feature module.

```python
# vector/contracts/actions/context.py
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ActionContext(BaseModel):
    """Mandatory execution context for every Action. Not part of business payload."""

    tenant_id: UUID
    actor_user_id: UUID
    request_id: str = Field(min_length=8, description="Correlation id for logs and tracing")
    source: Literal["slack", "http", "llm"]
```

**Why locked:** audit trails, permission checks (`actor_user_id`), tenancy isolation (`tenant_id`), LLM safety gates (`source == "llm"` policies), rate limits, and incident replay all key off `**ctx`** without parsing payloads.

Adapters **MUST** populate all fields. No partial contexts.

---

### 2.3 `ActionSpec` fields (complete)

Every Action **MUST** define:


| Field              | Requirement                                                                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`             | `str`, globally unique, namespaced (e.g. `report.user`). Immutable once shipped.                                                                                    |
| `description`      | Short, factual; suitable for tool metadata when `llm_exposed` is true.                                                                                              |
| `type`             | One of: `**data`**, `**aggregation**`, `**llm**` (see §3).                                                                                                          |
| `input_model`      | `**type[BaseModel]**` — Pydantic model class for business payload **only**.                                                                                         |
| `output_model`     | `**type[BaseModel]`** — Pydantic model class for success return value.                                                                                              |
| `handler`          | Callable obeying §2.1.                                                                                                                                              |
| `permissions`      | `**tuple[str, ...]**` — required capability strings (see §2.4). Empty tuple only if explicitly documented as public read within tenant with no extra checks (rare). |
| `idempotent`       | `bool` — whether safe logical repeat is intended / supported.                                                                                                       |
| `idempotency_note` | `str` — one sentence; explains what repeats mean (no separate `idempotency` field name elsewhere).                                                                  |
| `side_effects`     | `tuple[str, ...]` — explicit strings (DB writes, Slack posts, Celery enqueue, external API, **or** `invokes <action.name>`).                                        |
| `errors`           | `tuple[str, ...]` — expected failure identifiers surfaced to callers.                                                                                               |
| `llm_exposed`      | `bool` — if `False`, this Action **must not** appear in LLM tool lists (internal, debug, or human-only). Slack/HTTP may still invoke if policy allows.              |
| `cost_hint`        | Optional: `**Literal["low", "medium", "high"]`** — default `"low"` if omitted in implementation.                                                                    |
| `latency_hint`     | Optional: `**Literal["fast", "slow"]**` — default `"fast"` if omitted. Used for routing, quotas, and preventing runaway tool loops.                                 |


### 2.4 Schema rule: Pydantic models only

**FORBIDDEN:** registering an Action with free-form `dict` JSON Schema blobs, `input_schema={}`, or `TypeAdapter(dict)`.

**REQUIRED:** `input_model` and `output_model` are `**type[BaseModel]`**. Validation, OpenAPI, and LLM tool export **derive** from `model_json_schema()` at runtime — **single source of truth**, no schema drift.

---

### 2.5 Permissions

Each Action **MUST** declare:

```python
permissions: tuple[str, ...]  # e.g. ("read:user_activity",)
```

The **executor** (§5) runs `**enforce_permissions(ctx, spec.permissions)`** before `handler`. Implementation lives in `vector/domains/actions/permissions.py` (or identity domain) and maps `(ctx.actor_user_id, ctx.tenant_id, permission strings)` to allow/deny.

**Any** Action that runs if called without this check is **invalid**.

---

## 3. Action types (very important)

Do **not** mix responsibilities **inside one handler** (no LLM client in `data` handlers). **Composition** uses the executor to chain registered Actions.

### 3.1 `data` — Data Actions (deterministic)

- Read/fetch from Slack, GitHub, Linear, DB, ingestion stores.
- **Deterministic** modulo documented external variance.
- **No LLM client** in handler; no calls to `type=="llm"` unless explicitly justified as delegation (prefer keeping fetches self-contained).

Examples: `data.fetch_slack_activity`, `data.fetch_github_activity`

### 3.2 `aggregation` — Aggregation Actions (deterministic structure)

- Merge / join / filter / reshape structured data.
- **Deterministic** over given inputs.
- **May** call `**execute_action`** on other registered Actions, including `**type=="llm"**` for generation steps (the LLM runs inside the child Action, not ad hoc in the parent).
- **Composed user-facing Actions** (orchestrating multiple steps) **MUST** use `**type="aggregation"`**, even when the pipeline includes an LLM child Action.

Examples: `report.build_user_context`, `**report.user**` (composed)

### 3.3 `llm` — LLM Actions (non-deterministic, generation only)

- Structured input → natural language (or structured + prose) per `output_model`.
- `**idempotent` is typically `False**`; document in `idempotency_note`.
- `**side_effects`:** list inference API usage; **no** business entity writes (those stay in `data` or dedicated mutations).

Example: `report.generate_user_summary`

---

## 4. Action registry

**Central registry:** `name → ActionSpec`.

- **Modules:** `vector/domains/actions/` (recommended) or `vector/application/actions/` — single registrar.
- **Discovery:** explicit imports + `register()` at startup (**no** filesystem globbing in V0).
- **Collision:** `register()` **raises** if `name` exists.

```python
# vector/domains/actions/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Literal, Type, Union

from pydantic import BaseModel
from sqlalchemy.orm import Session

from vector.contracts.actions.context import ActionContext

ActionKind = Literal["data", "aggregation", "llm"]
CostHint = Literal["low", "medium", "high"]
LatencyHint = Literal["fast", "slow"]

Handler = Callable[
    [Session, ActionContext, BaseModel],
    Union[BaseModel, Awaitable[BaseModel]],
]


@dataclass(frozen=True, slots=True)
class ActionSpec:
    name: str
    description: str
    type: ActionKind
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    handler: Handler
    permissions: tuple[str, ...]
    idempotent: bool
    idempotency_note: str
    side_effects: tuple[str, ...]
    errors: tuple[str, ...]
    llm_exposed: bool
    cost_hint: CostHint = "low"
    latency_hint: LatencyHint = "fast"
```

```python
# vector/domains/actions/registry.py
from __future__ import annotations

from vector.domains.actions.types import ActionSpec

_REGISTRY: dict[str, ActionSpec] = {}


def register(spec: ActionSpec) -> None:
    if spec.name in _REGISTRY:
        msg = f"duplicate action name: {spec.name!r}"
        raise ValueError(msg)
    _REGISTRY[spec.name] = spec


def get(name: str) -> ActionSpec:
    if name not in _REGISTRY:
        msg = f"unknown action: {name!r}"
        raise KeyError(msg)
    return _REGISTRY[name]


def all_specs() -> frozenset[ActionSpec]:
    return frozenset(_REGISTRY.values())
```

**Registering a new Action**

1. Add `input_model` / `output_model` under `vector/contracts/actions/`.
2. Implement `handler(db, ctx, payload)` per §2.1.
3. `register(ActionSpec(...))` from module `init()`.
4. Wire module in `bootstrap.register_all_actions()`.

**Naming:** `<domain>.<action>` lowercase ASCII (see §8). `**data.*`** reserved for `type=="data"` (CI or review gate).

---

## 5. Execution flow and executor (core infra)

### 5.1 V0 (Slack)

```
Slack HTTP callback
  → verify signature / auth
  → parse text → { action_name, raw_inputs: dict[str, str] }
  → build ActionContext (all fields mandatory)
  → execute_action(db, ctx, action_name, raw_inputs)
  → format Slack message from OutputModel
```

### 5.2 Future (LLM)

```
Tool call { name, arguments }
  → build ActionContext (source="llm", request_id from runtime)
  → execute_action(db, ctx, name, arguments)
```

Same `**execute_action**` entrypoint.

### 5.3 Executor contract (non-negotiable behavior)

The executor is the **only** supported path from `{name, raw dict}` to handler execution. Handlers that skip it for “internal” calls **violate** the spec unless calling domain directly (not another Action).

**Required steps (in order):**

1. `**spec = get(name)`** — unknown name → consistent error type.
2. **Input validation:** `payload = spec.input_model.model_validate(raw)` — strict; reject unknown keys per Pydantic config.
3. **Permission enforcement:** `enforce_permissions(ctx, spec.permissions)` — deny → consistent error (e.g. `PermissionDenied`).
4. **Logging:** structured log line with `name`, `type`, `ctx.tenant_id`, `ctx.actor_user_id`, `ctx.request_id`, `ctx.source`, redacted `raw`, `cost_hint`, `latency_hint`.
   - **Optional (V0+ops):** also record each nested `execute_action` `name` (e.g. in `extra` or tracing) so runtime behavior can be compared to declared `invokes` strings — see [`v0_action_system.md`](./v0_action_system.md) §6.0 (`side_effects` remain informational in V0).
5. **Execute:** `result = spec.handler(db, ctx, payload)` (await if coroutine).
6. **Output validation:** `return spec.output_model.model_validate(result)` — ensures handler contract; catches accidental wrong shapes.
7. **Errors:** map domain exceptions to stable codes/messages for adapters; never leak raw SQL.

```python
# vector/domains/actions/executor.py (behavioral contract)
from __future__ import annotations

import inspect
import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from vector.contracts.actions.context import ActionContext
from vector.domains.actions.permissions import enforce_permissions
from vector.domains.actions.registry import get

log = logging.getLogger("vector.actions")


def execute_action(db: Session, ctx: ActionContext, name: str, raw: dict[str, Any]) -> BaseModel:
    spec = get(name)
    payload = spec.input_model.model_validate(raw)
    enforce_permissions(ctx, spec.permissions)

    log.info(
        "action_begin",
        extra={
            "action": name,
            "action_type": spec.type,
            "tenant_id": str(ctx.tenant_id),
            "actor_user_id": str(ctx.actor_user_id),
            "request_id": ctx.request_id,
            "source": ctx.source,
            "cost_hint": spec.cost_hint,
            "latency_hint": spec.latency_hint,
        },
    )

    result = spec.handler(db, ctx, payload)
    if inspect.isawaitable(result):
        # in async runtime, await here; sync stack may forbid async handlers
        raise RuntimeError("async handler requires async executor variant")

    out = spec.output_model.model_validate(result)

    log.info(
        "action_end",
        extra={
            "action": name,
            "tenant_id": str(ctx.tenant_id),
            "request_id": ctx.request_id,
        },
    )
    return out
```

### 5.4 Composed Actions

- `**report.user**` (and any multi-step orchestration) **MUST** have `**type="aggregation"`**.
- `**side_effects` MUST** include explicit lines: `invokes <child.action.name>` for **every** delegated Action.
- Implementation **MUST** delegate via `**execute_action`** (same `ctx` unless a child requires a derived context — document if ever needed).

### 5.5 Composability rule

**Any Action MUST be invocable from another Action via `execute_action`.** No Action may assume Slack, HTTP, or LLM as its only entrypoint. Adapters are thin; the registry + executor are canonical.

---

## 6. Integration with existing architecture

**Allowed**

- `vector.domains.<area>.*_commands`, domain services
- `vector.application.services.`*
- Repositories / connectors **only** where domain or application already allows it

**Forbidden**

- Duplicating domain invariants in handlers
- Bypassing `execute_action` when calling another Action by name

**Flow**

```
execute_action → handler → Domain command / service → Repository → DB / external API
```

---

## 7. Action design rules (non-negotiable)

1. **Atomic:** One clear responsibility per `name` (composed Actions orchestrate only their declared pipeline).
2. **Explicit inputs:** `payload` + mandatory `ctx`; nothing hidden on `Session` except DB handle.
3. **Deterministic** except `**type=="llm"`** (and documented external reads).
4. **Separation:** `data` / `aggregation` / `llm` — no ad hoc LLM outside registered `llm` Actions.
5. **Composable:** Any Action may call any other via `**execute_action`** with the same executor rules.
6. **No mega-actions.**
7. **Stable naming.**
8. **Observable:** executor logging (§5.3) + domain logs as needed.
9. **Permissions:** every Action declares `permissions`; executor enforces.

---

## 8. Naming convention

Format: `**<domain>.<action>`** (lowercase, dot-separated, ASCII).

Examples:

- `data.fetch_slack_activity`
- `data.fetch_github_activity`
- `report.build_user_context`
- `report.generate_user_summary`
- `report.user`

**Idempotency field names (consistency):** use `**idempotent: bool`** and `**idempotency_note: str**` only — nowhere else.

---

## 9. Full example: `report.user`

**Illustrative inputs:** this example uses **`window_start` / `window_end`** on `ReportUserInput` to show date handling in composition. The **shipped V0** Slack path uses **`window_days` only** — see [`v0_action_system.md`](./v0_action_system.md) §1.1; adjust models accordingly for V0 contracts.

### Contracts (`vector/contracts/actions/report_user.py`)

```python
from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

# ActionContext: import from vector.contracts.actions.context (global); do not redefine here.


class ReportUserInput(BaseModel):
    user_id: UUID
    window_start: date
    window_end: date


class SlackActivityInput(BaseModel):
    user_id: UUID
    window_start: date
    window_end: date


class GithubActivityInput(BaseModel):
    user_id: UUID
    window_start: date
    window_end: date


class SlackActivitySlice(BaseModel):
    messages_sample: list[str]


class GithubActivitySlice(BaseModel):
    commits_sample: list[str]


class BuildUserContextInput(BaseModel):
    user_id: UUID
    window_start: date
    window_end: date
    slack: SlackActivitySlice
    github: GithubActivitySlice


class UserReportContext(BaseModel):
    user_id: UUID
    window_start: date
    window_end: date
    slack: SlackActivitySlice
    github: GithubActivitySlice


class GenerateUserSummaryInput(BaseModel):
    context: UserReportContext


class UserSummaryText(BaseModel):
    markdown: str = Field(min_length=1)


class ReportUserOutput(BaseModel):
    context: UserReportContext
    summary: UserSummaryText
```

### Handlers (`vector/domains/actions/report_user_handlers.py`)

```python
from __future__ import annotations

from sqlalchemy.orm import Session

from vector.contracts.actions.context import ActionContext
from vector.contracts.actions.report_user import (
    BuildUserContextInput,
    GenerateUserSummaryInput,
    GithubActivityInput,
    GithubActivitySlice,
    ReportUserInput,
    ReportUserOutput,
    SlackActivityInput,
    SlackActivitySlice,
    UserReportContext,
    UserSummaryText,
)
from vector.domains.actions.executor import execute_action


def handle_fetch_slack_activity(
    db: Session,
    ctx: ActionContext,
    payload: SlackActivityInput,
) -> SlackActivitySlice:
    _ = (db, ctx, payload)
    return SlackActivitySlice(messages_sample=[])


def handle_fetch_github_activity(
    db: Session,
    ctx: ActionContext,
    payload: GithubActivityInput,
) -> GithubActivitySlice:
    _ = (db, ctx, payload)
    return GithubActivitySlice(commits_sample=[])


def handle_build_user_context(
    db: Session,
    ctx: ActionContext,
    payload: BuildUserContextInput,
) -> UserReportContext:
    _ = db, ctx
    return UserReportContext(
        user_id=payload.user_id,
        window_start=payload.window_start,
        window_end=payload.window_end,
        slack=payload.slack,
        github=payload.github,
    )


def handle_generate_user_summary(
    db: Session,
    ctx: ActionContext,
    payload: GenerateUserSummaryInput,
) -> UserSummaryText:
    _ = db, ctx
    return UserSummaryText(markdown="# Summary\n…")


def handle_report_user(
    db: Session,
    ctx: ActionContext,
    payload: ReportUserInput,
) -> ReportUserOutput:
    slack_in = SlackActivityInput(
        user_id=payload.user_id,
        window_start=payload.window_start,
        window_end=payload.window_end,
    )
    slack = execute_action(db, ctx, "data.fetch_slack_activity", slack_in.model_dump(mode="json"))
    github = execute_action(
        db,
        ctx,
        "data.fetch_github_activity",
        GithubActivityInput(
            user_id=payload.user_id,
            window_start=payload.window_start,
            window_end=payload.window_end,
        ).model_dump(mode="json"),
    )
    user_report_context = execute_action(
        db,
        ctx,
        "report.build_user_context",
        BuildUserContextInput(
            user_id=payload.user_id,
            window_start=payload.window_start,
            window_end=payload.window_end,
            slack=slack,  # runtime: output_model of data.fetch_slack_activity
            github=github,
        ).model_dump(mode="json"),
    )
    summary = execute_action(
        db,
        ctx,
        "report.generate_user_summary",
        GenerateUserSummaryInput(context=user_report_context).model_dump(mode="json"),
    )
    return ReportUserOutput(context=user_report_context, summary=summary)
```

`execute_action` returns the validated `**output_model**` instance for the resolved `name`; typed narrowing in production may use generics or per-action wrappers.

### Registration (`vector/domains/actions/report_actions.py`)

```python
from __future__ import annotations

from vector.contracts.actions.report_user import (
    BuildUserContextInput,
    GenerateUserSummaryInput,
    GithubActivityInput,
    GithubActivitySlice,
    ReportUserInput,
    ReportUserOutput,
    SlackActivityInput,
    SlackActivitySlice,
    UserReportContext,
    UserSummaryText,
)
from vector.domains.actions.registry import register
from vector.domains.actions.types import ActionSpec
from vector.domains.actions.report_user_handlers import (
    handle_build_user_context,
    handle_fetch_github_activity,
    handle_fetch_slack_activity,
    handle_generate_user_summary,
    handle_report_user,
)


def init() -> None:
    register(
        ActionSpec(
            name="data.fetch_slack_activity",
            description="Fetch Slack message samples for a user and time window.",
            type="data",
            input_model=SlackActivityInput,
            output_model=SlackActivitySlice,
            handler=handle_fetch_slack_activity,
            permissions=("read:slack_activity",),
            idempotent=True,
            idempotency_note="Read-only; repeated calls may observe newer messages if window is relative to clock.",
            side_effects=("calls Slack Web API",),
            errors=("SlackNotConnected", "RateLimited"),
            llm_exposed=True,
            cost_hint="medium",
            latency_hint="slow",
        )
    )
    register(
        ActionSpec(
            name="data.fetch_github_activity",
            description="Fetch GitHub commit samples for a user and time window.",
            type="data",
            input_model=GithubActivityInput,
            output_model=GithubActivitySlice,
            handler=handle_fetch_github_activity,
            permissions=("read:github_activity",),
            idempotent=True,
            idempotency_note="Read-only.",
            side_effects=("calls GitHub API",),
            errors=("GithubNotConnected", "RateLimited"),
            llm_exposed=True,
            cost_hint="medium",
            latency_hint="slow",
        )
    )
    register(
        ActionSpec(
            name="report.build_user_context",
            description="Merge Slack and GitHub slices into one structured user report context.",
            type="aggregation",
            input_model=BuildUserContextInput,
            output_model=UserReportContext,
            handler=handle_build_user_context,
            permissions=("read:slack_activity", "read:github_activity"),
            idempotent=True,
            idempotency_note="Deterministic function of inputs.",
            side_effects=(),
            errors=("InvalidDateRange",),
            llm_exposed=False,
            cost_hint="low",
            latency_hint="fast",
        )
    )
    register(
        ActionSpec(
            name="report.generate_user_summary",
            description="Generate markdown summary from structured user report context.",
            type="llm",
            input_model=GenerateUserSummaryInput,
            output_model=UserSummaryText,
            handler=handle_generate_user_summary,
            permissions=("read:report_context", "invoke:llm_inference"),
            idempotent=False,
            idempotency_note="LLM output is non-deterministic.",
            side_effects=("calls LLM inference API",),
            errors=("LLMTimeout", "LLMRefusal"),
            llm_exposed=True,
            cost_hint="high",
            latency_hint="slow",
        )
    )
    register(
        ActionSpec(
            name="report.user",
            description="End-to-end user report: fetch data, build context, generate summary.",
            type="aggregation",
            input_model=ReportUserInput,
            output_model=ReportUserOutput,
            handler=handle_report_user,
            permissions=(
                "read:slack_activity",
                "read:github_activity",
                "read:report_context",
                "invoke:llm_inference",
            ),
            idempotent=False,
            idempotency_note="Contains LLM child step; non-deterministic summary text.",
            side_effects=(
                "invokes data.fetch_slack_activity",
                "invokes data.fetch_github_activity",
                "invokes report.build_user_context",
                "invokes report.generate_user_summary",
            ),
            errors=("SlackNotConnected", "GithubNotConnected", "LLMTimeout"),
            llm_exposed=True,
            cost_hint="high",
            latency_hint="slow",
        )
    )
```

---

## 10. Slack command layer (V0)

**Format**

```text
/do <action_name> <key>=<value> [<key>=<value> ...]
```

**Example**

```text
/do report.user user_id=550e8400-e29b-41d4-a716-446655440000 window_start=2026-04-01 window_end=2026-04-07
```

`**ActionContext**` fields **not** parsed from user text: route sets `tenant_id`, `actor_user_id`, `request_id` (generate UUID string), `source="slack"`.

**Parsing rules**

- Unknown keys → **error**
- Missing required keys → **error**
- Parse to `dict` → `execute_action` → Pydantic strict validation

**Slack layer:** verify Slack, parse, map identity, build `ctx`, call executor only — **no business logic**.

---

## 11. LLM compatibility


| Mechanism                                                    | Use                                          |
| ------------------------------------------------------------ | -------------------------------------------- |
| `name`                                                       | Tool identifier                              |
| `input_model.model_json_schema()`                            | Tool parameters                              |
| `output_model.model_json_schema()`                           | Tool result                                  |
| Registry `all_specs()` filtered by `**llm_exposed is True`** | Published tool list                          |
| `permissions` + `enforce_permissions`                        | Safety gate for autonomous calls             |
| `cost_hint` / `latency_hint`                                 | Budgeting, routing, loop prevention          |
| `**execute_action**` unchanged                               | Zero backend rewrite when adding LLM adapter |


---

*End of document.*