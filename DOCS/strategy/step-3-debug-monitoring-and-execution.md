# Step 3 — Debugging Tools, Execution Pipeline, and Operational Monitoring

**Status:** Architecture locked (companion to `step-3-canonical-ontology-implementation-spec.md`)  
**Purpose:** Finalize **developer-facing observability** and **runtime execution** for Step 3 before implementation.

This document describes:

1. **Canonical debugging interface** — table explorer + optional graph mode  
2. **Confirmed execution pipeline** — sync → Step 2 → Step 3 + safety net  
3. **Backlog / lag monitoring** — `/debug/canonical/status` and metrics semantics  

Building observability for the **data model itself** (not only service metrics) is intentional: ontology mistakes are expensive to unwind later; the debug explorer should become one of the most-used internal tools.

---

## 1. Execution pipeline (confirmed)

### 1.1 Ordered chain

Step 3 runs **after** connector projections are up to date for the same scope. The canonical chain is:

```
connector sync (Step 1 ingestion for that connection)
        ↓
Step 2 projection drain (materialize / update connector projections)
        ↓
Step 3 canonical drain (mapping, artifacts, relationships from projections in replay order)
```

**Confirmation:** There is **no** path where Step 3 runs “before” Step 2 for the same backlog item. Step 3 consumers **only** read Step 2 outputs (or the same ordered replay stream Step 2 used), per the Step 3 spec (Parts F, G, J).

### 1.2 Primary trigger

- **On success** of Step 2 projection drain for `(tenant_id, connection_id, connector)`, invoke **Step 3 canonical drain** for that same scope (same pattern as “GitHub sync → drain projections” today).

### 1.3 Safety net (scheduled / continuous)

- A **scheduled job** (or low-frequency worker loop) **drains Step 3 backlog** for connections that are **lagging**—e.g. missed hook, partial failure, deploy mid-batch, operator retry.
- This does **not** replace the post–Step 2 trigger; it **complements** it so the system is **self-healing** without manual intervention.

### 1.4 Failure and retries

- If Step 3 drain fails, **cursor does not advance** (or advances only after successful commit—implementation must pick one invariant and document it).
- Next successful run (post–Step 2 or safety net) **retries** from the last committed cursor position.

---

## 2. Step 3 debugging tools

### 2.1 Goals

Allow developers to **visually verify** during implementation and in production debugging:

- Artifacts and actors are created and classified correctly  
- Relationships match intent (including temporal `valid_to`)  
- External references and **mapping events** / **current_mapping** align with projections  
- Containment / association edges (`part_of`, `associated_with`, …) behave as expected  

This is a **developer tool**, not a polished product UI.

### 2.2 API surface (prefix)

- **`/debug/canonical/...`** — session-authenticated, tenant-scoped (same security posture as `/debug/connectors/...`).

### 2.3 Table-based entity explorer (required for v1)

**Lists (paginated):**

| Method | Path | Notes |
|--------|------|--------|
| GET | `/debug/canonical/actors` | Filters as needed |
| GET | `/debug/canonical/artifacts` | Filter by kind slug / `artifact_kind_id` |
| GET | `/debug/canonical/relationships` | Optional filters: subject/object id, `relation_kind`, `current_only` |
| GET | `/debug/canonical/external-references` | |
| GET | `/debug/canonical/mapping-events` | Filter by `external_reference_id`, etc. |

**Detail (navigation-friendly):**

| Method | Path | Notes |
|--------|------|--------|
| GET | `/debug/canonical/actors/{id}` | Actor + identities + **incoming/outgoing relationship** summaries with **resolved counterparty labels** |
| GET | `/debug/canonical/artifacts/{id}` | Spine + extension summary + neighbors + linked external refs / recent mapping events |
| GET | `/debug/canonical/relationships/{id}` | Edge detail + resolved subject/object one-liners |
| GET | `/debug/canonical/external-references/{id}` | Ref + current mapping + mapping history |

**UI:** Routes such as `/debug/canonical` with tabs or query params; clicking a counterparty navigates to the corresponding actor or artifact detail route.

### 2.4 Graph visualization mode (optional for v1 UI, API designed up front)

**Purpose:** When inspecting an artifact (or actor), render a **small graph**: anchor node → relationships → connected actors and artifacts. This catches structural mistakes (wrong edge type, missing link) faster than tables alone.

**Client:** Lightweight rendering with **Cytoscape.js** or **D3** (team choice); start with force-directed or hierarchical layout for small `depth`.

**Subgraph API (required for easy UI integration):**

```http
GET /debug/canonical/subgraph?artifact_id={uuid}&depth=2
```

**Alternative anchor (at least one required):**

```http
GET /debug/canonical/subgraph?actor_id={uuid}&depth=2
```

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `artifact_id` | Anchor artifact UUID (mutually exclusive with `actor_id` as anchor—exactly one anchor type required) |
| `actor_id` | Anchor actor UUID |
| `depth` | Non-negative integer; **BFS hops** from anchor along **relationship** edges (default `2`). Cap **max depth** (e.g. 4) in the API to avoid abuse. |
| `connection_id` | Optional; if multi-connection semantics need scoping |

**Response shape (illustrative):**

```json
{
  "anchor": { "type": "artifact", "id": "uuid" },
  "depth": 2,
  "nodes": [
    {
      "id": "uuid",
      "node_type": "artifact",
      "artifact_kind": "changeset",
      "label": "Add feature X",
      "status": "open",
      "last_observed_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": "uuid",
      "node_type": "actor",
      "actor_kind": "person",
      "label": "alice"
    }
  ],
  "edges": [
    {
      "id": "relationship-row-uuid",
      "source_id": "uuid",
      "target_id": "uuid",
      "relation_kind": "authored_by",
      "directed": true,
      "valid_from": "...",
      "valid_to": null
    }
  ],
  "truncated": false,
  "truncation_reason": null
}
```

**Semantics:**

- Traverse **both directions** from the anchor (incoming and outgoing relationships) unless a future query flag restricts direction.
- Include only relationships **visible to the tenant** and optionally **current-only** default (`valid_to IS NULL`) with a query flag `include_historical=true` if historical edges should appear in the graph.
- Enforce a **max node budget** (e.g. 200–500 nodes) and set `truncated: true` with a short `truncation_reason` when the cap is hit.

This keeps the **same canonical IDs** as the table views so clicking a node in the graph can deep-link to `/debug/canonical/artifacts/{id}` or `/debug/canonical/actors/{id}`.

---

## 3. Operational monitoring — Step 3 backlog and lag

### 3.1 Why

Developers and operators need to answer: **Is Step 3 keeping up with Step 2?** Without this, silent lag looks like “ontology bugs” when the real issue is **pipeline backlog**.

### 3.2 Status endpoint

```http
GET /debug/canonical/status
```

**Scope:** Tenant-scoped; optional `connection_id` and `connector` query params to narrow to one connection.

**Response fields (names are part of the contract):**

| Field | Meaning |
|-------|--------|
| `step3_last_processed_replay_sequence` | Last **replay_sequence** value committed by Step 3 for this scope (aligns with Step 1/2 ordering contract—exact column may live on `step3_projection_cursor` or equivalent). |
| `step3_last_processed_id` | Tie-breaker id in the same ordering as projections (e.g. last raw record id or last projection row id processed)—must match the documented ordering key pair in implementation. |
| `step3_lag_rows` | **Estimated or exact** count of Step 2 rows (or ordered work items) **not yet** processed by Step 3 after the cursor—computed as `watermark_step2 - cursor_step3` in consistent units. |
| `step3_last_processed_timestamp` | Wall-clock time when Step 3 **last committed** a batch for this scope (server time). |

**Optional useful additions (implementation may add without breaking the core four):**

- `step2_watermark_replay_sequence` / `step2_watermark_id` — so lag is explainable in one response  
- `connector`, `connection_id`, `tenant_id` echoes for clarity  
- `status`: `healthy` \| `lagging` \| `stale` if thresholds are defined later  

### 3.3 Implementation note

Persist cursor state in a dedicated table (e.g. `step3_projection_cursor` keyed by `(tenant_id, connection_id, connector)`) so status is **O(1)** to read and consistent with the worker.

### 3.4 Relation to service metrics

If the stack exports **Prometheus** metrics later, these values can be **mirrored** as gauges; the **debug endpoint** remains the **source of truth** for developers during ontology work.

---

## 4. Documentation map

| Document | Role |
|----------|------|
| `step-3-canonical-ontology-implementation-spec.md` | Ontology, schema, determinism, rebuild (Parts A–K), implementation plan (SP*) |
| **This document** | Debugging UI, subgraph API, execution order, `/debug/canonical/status`, operational expectations |

---

## 5. Implementation checklist (for Step 3 + debug track)

- [ ] Cursor table + Step 3 worker integrated **after** Step 2 drain  
- [ ] Scheduled / periodic Step 3 drain (safety net)  
- [ ] `/debug/canonical/*` list + detail routes with neighbor resolution  
- [ ] `GET /debug/canonical/subgraph` with depth cap and node cap  
- [ ] `GET /debug/canonical/status` with the four core fields  
- [ ] Frontend: `/debug/canonical` table explorer; graph panel optional in v1 but **API ready**  

---

## 6. Closing

**Ontology observability** is not optional for a system that claims deterministic, explainable execution intelligence. The combination of **ordered pipeline triggers**, **lag visibility**, and **entity + subgraph debug APIs** makes Step 3 **testable in development** and **operable in production**—reducing time spent chasing phantom “bad edges” when the root cause is backlog or ordering.

**Next step:** Implement schema, workers, and debug routes per the Step 3 specification and this document.
