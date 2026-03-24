---
name: senior-standards
description: Engineering standards distilled from 3,817 code review comments by the senior Payflows engineers. Use before submitting MRs.
---

# Payflows Senior Engineering Standards

Distilled from **3,817 code review comments** across all 15 backend repos.

Run through this checklist before every MR.

---

## 1. Type Safety (Most Frequent Category)

- **No `Any`, no untyped `dict`, no bare `list`.** Find the real type or create a TypedDict/Pydantic model.
- **Replace untyped tuples with dataclasses or type aliases.** `tuple[str, int, float]` → named dataclass.
- **Type all function arguments and return values.** Every function gets `-> ReturnType`.
- **Type loop variables explicitly** when unpacking query results.
- **No `getattr`/`setattr` on known fields** — it erases the type. Access attributes directly.
- **Use modern Python typing**: `list[int]` not `typing.List[int]`, `X | None` not `Optional[X]`, `StrEnum` not `(str, Enum)`, `typing.Self` not `typing_extensions.Self`.
- **No `datetime.utcnow()`** — deprecated. Use `datetime.now(tz=timezone.utc)`.
- **Parameterize all generics**: `list[int]`, `dict[str, Value]`, never bare `list` or `dict`.
- **No `# type: ignore` without explanation.** Fix the root cause instead.

```python
# BAD
def get_rates(rows: list) -> dict:
    for row in rows:
        rate = row[1]

# GOOD
def get_rates(rows: list[tuple[str, Decimal]]) -> dict[str, Decimal]:
    for currency, rate in rows:
        ...
```

---

## 2. Cyclomatic Complexity & File Size

- **Max ~200 lines per file.** Split by logical stage or responsibility.
- **Split functions that branch on type discriminators.** If a function branches on `source_type`, `serie_type`, etc., extract each branch into its own function.
- **Boolean parameters are a code smell.** If a function takes a bool to switch behavior, split it into two functions.
- **Name split files by domain concept**: `schemas.py`, `validation.py`, `parsing.py` — never `common.py`, `utils.py`, `helpers.py`.
- **Don't mix concerns in one stage.** A `parse_stage` should not also build objects.
- **Extract code blocks into named functions.** If you need a comment to explain a block, it should be a function whose name is that comment.

---

## 3. Error Handling & Exceptions

- **Guard clauses at the top of functions.** Validate preconditions before doing any work.
- **Never silently swallow errors.** No empty `except: pass`. No returning `None` for impossible states.
- **Preserve stack traces**: always `raise NewError(...) from e`, never bare `raise NewError(...)` in an except block.
- **Use exception notes** (Python 3.11+): `error.add_note(f'{bank_order_id=}')` for structured context.
- **Don't duplicate error messages** in nested wrappers. Log the technical detail, raise the user-facing message.
- **Never expose technical details to users.** Bucket names, stack traces, internal IDs → `logger.error(...)`. User gets `"Internal Error"`.
- **Raise proper HTTP status codes.** 404 when not found, 422 for validation — don't silently return empty results.
- **Custom exceptions go in `errors.py`**, not inline in service files.
- **Use `match`/`case` for multi-branch logic** and handle every enum variant — raise `NotImplementedError` for unhandled cases.
- **Use `finally` blocks** when cleanup must happen regardless of success/failure.

```python
# BAD
def process(item: Item) -> Result:
    data = fetch(item)
    if item.connection is None:
        return None  # silent failure

# GOOD
def process(item: Item) -> Result:
    if item.connection is None:
        raise ValueError(f"Item {item.id} has CONNECTION type but connection is None")
    data = fetch(item)
    ...
```

---

## 4. Dead Code & Deprecation

- **Remove dead code immediately.** Don't comment it out. Don't leave it "for reference."
- **Never propagate deprecated patterns.** If a model/method is deprecated, don't add new references.
- **Don't extend code that should be removed.** If a method is marked for deletion, don't add logic to it.
- **Mark deprecated code unmistakably.** Raise `NotImplementedError('deprecated')` in constructor if needed.
- **Track cleanup as explicit Shortcut tickets.** Don't leave TODOs without tickets.
- **Question every `# noqa` / suppression comment.** They often outlive their reason.
- **Don't export dead columns.** Verify data exists before exposing fields.

---

## 5. Layer Boundaries & Import Hierarchy

- **Route → Service → Data. Never skip layers.**
- **Import direction**: `models/ → can import → schemas/`. `schemas/ → NEVER imports → models/`. `models/ → NEVER imports → services/`.
- **NEVER use `from_orm` on Pydantic schemas.** Use `to_schema()` on SQLAlchemy models.
- **No business logic in routes.** Routes handle HTTP validation, auth, and delegation to services.
- **No fetches in presentation logic.** Presentation transforms data, never fetches it.
- **No business logic in parsing packages.** Parsing extracts data; business rules live in services.
- **Keep `__init__.py` files clean.** Logic there risks circular dependencies.
- **Enums go in `app/schemas/<domain>/enums.py`**, not `app/enums/`.
- **Register new models in `models/__init__.py`** or SQLAlchemy won't discover them.

---

## 6. Database & Query Patterns

- **Push filtering to SQL, not Python.** If you can add a WHERE clause, don't filter in a loop.
- **Use `postgresql_concurrently=True`** for index creation on large tables.
- **No DB triggers for business logic.** Use event handlers/subscribers instead.
- **`DISTINCT` requires `ORDER BY`.** Without it, results are non-deterministic.
- **`LIMIT` requires `ORDER BY`.** Always.
- **Prefer `INSERT ... ON CONFLICT DO NOTHING`** over manual diff-and-insert in Python.
- **Use `UNION` not `UNION ALL` + `DISTINCT`.** `UNION` already deduplicates.
- **Make `select_from` explicit** in SQLAlchemy queries. No implicit selects.
- **Reason about join cardinality.** Ask: "Can this join produce multiple rows?" before writing it.
- **Prefer simple filters over subqueries** when possible.
- **Push bulk mutations to SQL.** Don't iterate in Python when a single UPDATE with conditions works.
- **Use composite FKs including `tenant_id`** for multi-tenant tables to prevent cross-tenant leaks.
- **Always add indexes** for columns used in WHERE/JOIN clauses.
- **Design unique constraints on business logic**, not surrogate keys.

---

## 7. Migration Safety

- **New non-nullable columns: add nullable first**, populate existing rows, then alter to non-nullable. Always set `server_default`.
- **Account for deployment ↔ script execution gap.** Migrations run at deploy; data scripts run later. Plan for the interim state.
- **Split risky migrations** into separate files to reduce transaction size.
- **Handle existing data** when adding columns. Don't assume the table is empty.
- **Use `alter_enum_add()`** for new enum values, not `alter_column_enum`.
- **Handle downgrades properly.** Drop new enums in downgrade. If downgrade would corrupt data, skip it entirely.
- **Test migration impact** on creates, updates, AND deletes — not just creates.

---

## 8. Testing

- **Mock at the infrastructure boundary** (`AWSS3.load_file`, `boto3` client), not internal functions that may be refactored.
- **Write integration tests through endpoints**, not just unit tests on internal functions.
- **One concern per test.** Don't lump create, update, and delete into one test.
- **Test the full lifecycle**: create, update, AND delete — not just the happy path.
- **Test both success and error scenarios.**
- **Snapshot structured outputs** (JSON, XML, query results, audit trails, S3 uploads) to catch regressions.
- **Hardcode IDs in tests.** No random UUIDs — deterministic tests are debuggable tests.
- **Remove `print()` statements.** Use snapshots or proper assertions.
- **Reuse existing test helpers** before writing custom assertion logic.
- **Test with realistic edge-case data** that exposes join problems (e.g., unused related records).

```python
# BAD
@patch("app.services.fx.upload_to_s3")
def test_export(mock_upload): ...

# GOOD
@patch("app.infra.aws.AWSS3.load_file")
def test_export(mock_s3): ...
```

---

## 9. Naming & Readability

- **Names must be domain-accurate**: `quote_currency` not `currency`, `list_available_forex_strategies` not `list_strategies`.
- **Match variable names to cardinality**: singular for one item, plural for collections.
- **No variable shadowing.** Two variables with the same name in the same scope is a bug source.
- **Avoid double negations**: `all_access` not `ignore_secret`. Negated booleans lead to `not not_disabled` confusion.
- **No AI-generated boilerplate comments.** Only comment where logic is genuinely non-obvious.
- **Use docstrings, not inline comments**, for function descriptions.
- **Use named constants over magic numbers/strings**: `MAX_RETRY_SECONDS = 30.0`, not bare `30.0`.
- **Pass boolean keyword arguments explicitly**: `process(is_sync=False)` not `process(False)`.

---

## 10. Pythonic Patterns

- **List comprehensions over loop-and-append.**
- **`defaultdict(list)` over manual `if key not in dict` patterns.**
- **Dictionary merge**: `{**d1, **d2}` or `d1 | d2`.
- **Named boolean conditions** for complex expressions.
- **Early return/continue** instead of deep nesting.
- **Iterators can only be consumed once.** If you need to iterate twice, `list()` it first. Consuming an iterator twice silently loses data.
- **Compare sets of IDs**, not full dicts. Use set intersection/difference.
- **`4 if last else 4` → just `4`.** Eliminate no-op conditionals.

```python
# BAD
results = []
for item in items:
    results.append(transform(item))

# GOOD
results = [transform(item) for item in items]

# BAD
if plan.target_is_active and not source.is_active and plan.rate_type_changed:
    ...

# GOOD
is_activating = plan.target_is_active and not source.is_active
has_rate_change = plan.target_is_active and plan.rate_type_changed
if is_activating or has_rate_change:
    ...
```

---

## 11. Boolean Comparisons

- **Never `column == True` or `column == False`** on booleans.
- **SQLAlchemy nullable booleans**: use `column.is_(False)`.
- **SQLAlchemy non-nullable**: use `~column` or `column` directly.
- **Python**: `if source.is_active:` not `if source.is_active == True:`.
- **Replace bare `else` with explicit conditions** when switching on known values.
- **Remove `# noqa: E712`** once you switch to `.is_(False)`.

---

## 12. OOP vs Functional

- **No mutable state → use pure functions.** Classes without state add ceremony without value.
- **Use classmethods for factory patterns** when classes are justified.
- **Pass dependencies as function arguments**, not instance/global state.
- **Remove redundant `tenant_id` arguments** when RLS already scopes queries.
- **Don't pass `account_id` as a global API dependency** — pass where needed.

---

## 13. Inter-Service Communication

- **Always pass `backend_authorized=True`** for internal service-to-service calls. This is a hard rule.
- **Always set tenant context** before cross-service calls. Always clean up with `try/finally`.
- **Use typed client packages** (`counterparty_client.retrieve_counterparty_payments_light`) — never raw HTTP or duplicated schemas.
- **Don't create artificial cross-service dependencies.** If service A needs a simple config from service B, consider a local table.
- **Don't pass `tenant_id` in the call** when it's inferred from context.

```python
# BAD
response = requests.get(f"{SERVICE_URL}/api/counterparties")

# GOOD
result = counterparty_client.retrieve_counterparty_payments_light(
    backend_authorized=True
)
```

---

## 14. Concurrency & Session Management

- **Read-check-write must be atomic** with `SELECT FOR UPDATE` to prevent race conditions.
- **Commit per unit of work.** Don't commit after async calls that may not have completed.
- **Use `try/finally` for tenant context cleanup.** Cross-tenant data leakage is a security issue.
- **Use the right session type for the context.** `app_user_session` is tenant-scoped; `webhook_session` is not.
- **Concurrent execution must be intentional.** Verify that parallel processing won't violate ordering guarantees.
- **No recursion in production code** — use iteration instead.

---

## 15. Resilience & Isolation

- **Isolate independent operations in loops.** One failure must not cascade to the next iteration.
- **Commit + emit events per item**, not after the whole batch. If rule 3 of 10 fails, rules 1-2 should still be committed.
- **Identify downstream consequences of error paths.** What side effects are lost if this fails?
- **Validate all items before applying** in bulk operations. Don't apply 3 of 5 then fail on the 4th.

---

## 16. Logging & Observability

- **Logger uses `%`-format**, never f-strings: `logger.info("Payment %s", payment_id)`.
- **`logger.error` for messages, `logger.exception` for exceptions.** Don't mix them.
- **Sentry captures local variables** — don't repeat them in the log message.
- **Structure errors for Sentry grouping.** Log the exception, raise a new error with a clean title.
- **Add logs at key decision points** for operational support and debugging.
- **No `print()` anywhere** — not in production code, not in tests.
- **Every `# type: ignore` needs an explanation** or it gets removed.

---

## 17. API Design

- **GET for retrieval, not POST** — unless request body is large.
- **Paginate list endpoints.** Never return unbounded arrays.
- **Cache GET endpoints** when data doesn't change frequently.
- **Idempotent operations**: same request = same result. `SKIPPED` not `FAILED` for duplicates.
- **Use typed config accessors**: `current_config.TENANT_BUCKET` not `config["TENANT_BUCKET"]`.
- **Handle `None` with `or ""`** when building schemas from nullable DB columns.
- **Support ISO format** for date input fields.

---

## 18. Comparison & Numeric Safety

- **Compare `.value` attributes, not object references.** Copied objects break identity comparison.
- **Use integer cents for money.** `amount_cents = int(round(amount * 100))` — floats accumulate decimal errors.
- **Be precise about comparison operators.** `<=` vs `<` matters — think about boundary cases.
- **Explicit numeric conversions**: `int(round(amount))` not implicit float-to-int.

---

## 19. Circular Dependency Prevention

- **Follow import hierarchy strictly**: schemas → never imports → models/services.
- **Extract shared code to lower-level modules** to break dependency chains.
- **Move enums to `app/schemas/<domain>/enums.py`** — not inside model files.
- **Even within a package**, manage internal dependency direction.

---

## 20. Reusable Logic & Abstraction

- **Duplicated in 3+ places → extract to shared helper or package.**
- **One function for session + context setup.** Don't duplicate transaction context logic.
- **Don't mix abstraction levels.** Keep orchestration separate from data manipulation.
- **Use abstract base classes** when multiple entities share similar patterns (e.g., `check_condition`, `execute`).
- **Put shared cross-service logic in a central service**, not duplicated per service.
- **Define defaults in one place.** Don't scatter the same default value across files.

---

## Quick Checklist

Before submitting any MR, verify:

1. **Types**: No `Any`, no untyped containers, no bare generics, no `# type: ignore` without reason?
2. **Size**: No file > 200 lines, no function with boolean-switching behavior?
3. **Errors**: Guards at top, stack traces preserved with `from e`, no silent failures?
4. **Dead code**: No deprecated patterns propagated, no dead exports?
5. **Layers**: Route → Service → Data respected, `to_schema()` not `from_orm`?
6. **Queries**: Filters in SQL, indexes added, concurrent index creation, no triggers?
7. **Migrations**: Nullable first → populate → non-nullable, downgrades handled?
8. **Tests**: Mocked at infra boundary, lifecycle tested, snapshots for structured output?
9. **Names**: Domain-accurate, no shadowing, no AI comments, no magic numbers?
10. **Patterns**: Comprehensions, `defaultdict`, early returns, iterators materialized?
11. **Booleans**: No `== True`/`== False`, explicit conditions?
12. **Functions > Classes** when stateless?
13. **Inter-service**: `backend_authorized=True`, typed client packages, tenant context cleaned?
14. **Concurrency**: `SELECT FOR UPDATE` for atomic reads, commit timing correct?
15. **Resilience**: Loop iterations isolated, events emitted per item?
16. **Logging**: `%`-format, `error` vs `exception` correct, no `print()`?
17. **API**: GET for reads, pagination, idempotent, ISO dates?
18. **Numbers**: Integer cents for money, explicit conversions, precise comparisons?
19. **Imports**: No circular deps, enums in schemas, shared code in lower modules?
20. **DRY**: Nothing duplicated 3+ times without extraction?