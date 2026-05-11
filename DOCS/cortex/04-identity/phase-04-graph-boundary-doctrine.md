# Phase 04 — Graph boundary (P04-13)

**Status:** normative boundary between **Phase 04 org continuity** exports and **Phase 05 organizational graph**.  
**Role:** forbid sneaking **Phase 03 materialization / topology / canonical transform** artifacts into the **OrgGraphProjectionV1** contract Phase 05 may consume.

---

## 1) Hard separation

| Layer | In OrgGraphProjectionV1? |
| ----- | ------------------------- |
| **`cortex_org_entities`** | **Yes** — org handle nodes (`kind=org_entity`). |
| **`cortex_org_primitive_instances`** | **Yes** — execution primitive nodes (`kind=org_primitive`), structural fields only. |
| **`cortex_org_links`** with **`link_authority='authoritative'`** | **Yes** — meaning edges (`kind=org_meaning_link`). |
| **Hint / non-authoritative links** (`link_authority != 'authoritative'`) | **No** — excluded from export (not merge-closure truth). |
| **Phase 03 canonical transforms, materializations, replay topology** | **No** — never serialized into this export; **G-P04-10** scans canonical JSON for forbidden substrings (defense-in-depth). |

---

## 2) Non-goals (Phase 04)

- No graph **storage**, **index**, or **traversal engine** in Phase 04.
- No admin **graph visualization** or adjacency theater — export is a **frozen JSON contract** + stable hash for handoff.

---

## 3) Normative references

- `phase-04-graph-projection-export-doctrine.md` — JSON shape + hashing.
- `phase-04-implementation-plan.md` — §10 graph implication, §11 graph-ready semantics, §14 Phase boundary audit.
- `vector.domains.cortex.identity.projection_export` — runtime builder + gates **G-P04-10** / **G-P04-EXP-01**.
