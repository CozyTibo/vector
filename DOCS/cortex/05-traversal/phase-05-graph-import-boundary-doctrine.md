# Phase 05 — Graph import boundary doctrine

**Normative step:** **4**. **Freeze bundle:** **FF-1**.  
**Depends on:** `phase-04-graph-boundary-doctrine.md`, `phase-04-graph-projection-export-doctrine.md`, `phase-05-normative-index.md`, `phase-05-anti-goals-doctrine.md`.

---

## 1. Constitutional intent

Define the **only** ingress surfaces OCTS may traverse: **OrgGraphProjectionV1**-compatible export and org tables explicitly listed in Phase 04. **FORBIDDEN:** any Phase 03 canonical topology, transform graph, or 3.5 semantic payload as traversable edges.

---

## 2. Explicit anti-goals

- **MUST NOT** “enrich” import with LLM entity resolution.  
- **MUST NOT** add edges from **hint** or **non-authoritative** ledger rows.  
- **MUST NOT** import **candidate** links as walkable unless a **future constitutional amendment** adds an explicit **non-default** exploration profile (default remains **forbidden**).

---

## 3. Formal terminology

| Term | Meaning |
| ---- | ------- |
| **Import bundle** | Frozen `OrgGraphProjectionV1` JSON + `projection_content_hash`. |
| **Traversable authority** | `link_authority == authoritative` org links only. |
| **link_row_stable_id** | Stable id used in **edge_fingerprint** — export MUST expose per edge. |

---

## 4. Deterministic semantics

**RULE GIB-01:** Traversal engine **MUST** reject import if `projection_content_hash` does not match recomputed hash from bytes.  
**RULE GIB-02:** Node and edge iteration order for **build** phases is defined in multigraph doctrine — import order **MUST NOT** affect walk order.

---

## 5. Replay semantics

Walk replay **MUST** pin **`projection_content_hash`** inside **`temporal_anchor`**. Replaying with a different hash **MUST** produce a **distinct** `walk_id` lineage or explicit **mismatch** error in strict mode.

---

## 6. Temporal semantics

Org link **valid_from / valid_to** (half-open) from Phase 04 **MUST** be imported without alteration. Walk **`t_as_of`** **MUST** satisfy `valid_from <= t_as_of < valid_to` for hop eligibility (see temporal walk doctrine).

---

## 7. Provenance semantics

Every **observed** hop **MUST** bind to **`org_link_id`** (or documented primitive binding) present in the **same** import bundle used for the walk.

---

## 8. Serialization contracts

Import bundle canonicalization **MUST** follow Phase 04 export rules. OCTS **MUST NOT** redefine projection hashing — **SHALL** reference P04 export doctrine for the hash input buffer.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-GIB-01** | Traversal reads `cortex_canonical_*` tables directly for edges. |
| **FS-GIB-02** | Hint links appear in `traversable_edge_set`. |
| **FS-GIB-03** | `projection_content_hash` missing from anchor while walk executes. |

---

## 10. Verification implications

- **G-P05-IMPORT-01:** DB/export scan — traversable set ⊆ authoritative org links from approved export builder.  
- **G-P05-IMPORT-02:** Forbidden substring / token scan (extends **G-P04-10** class).

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Phase 07 | Join canonical topics onto edges | Import boundary rejects non-export joins at engine API. |
| Fast path dev | Query org DB ad hoc | Runtime model forbids — all edges via import bundle or derived index contract only. |

---

## 12. Negative examples

**ILLEGAL API input:** `edge_source: "canonical_transform_node:uuid"`  
**LEGAL:** `edge_source: "org_meaning_link"` with `org_link_id` in export.

---

## 13. CI oracle expectations

- Fixture projection with known edges; gate proves no extra edges.  
- Regression: attempt to traverse `candidate` authority → **hard fail**.

**Reference implementation (P05-04):** `vector.domains.cortex.traversal.graph_import_boundary` — `list_oct_graph_import_violations`, `validate_oct_traversal_import_projection`, `validate_inner_projection_matches_stable_hash`, `validate_temporal_anchor_has_projection_content_hash`, `verify_gp05_import01_traversable_subset_authoritative_static`, `verify_gp05_import02_forbidden_ingress_tokens_static`. Phase **04** export builder emits **`link_row_stable_id`** on each edge (same stable row identity as `id`).
