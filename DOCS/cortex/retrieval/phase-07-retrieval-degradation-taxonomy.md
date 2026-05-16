# Phase 07 — Retrieval degradation taxonomy

**Status:** normative.

---

## Substrate health states (retrieval stage)

| State | Predicate |
| ----- | --------- |
| `healthy` | Index coverage ≥ policy threshold; last query replay-safe; no replay conflicts |
| `degraded` | Partial index; degraded upstream; or cap omissions > 0 |
| `critical` | Index missing while TCRE/graph require retrieval; or >50% unverifiable |
| `unresolved` | Addressing failures dominate |
| `replay_conflicted` | Upstream identity/TCRE replay conflict poisons retrieval |

---

## `RD-*` omission/degradation codes (closed registry v1)

| Code | Meaning | Typical upstream trigger |
| ---- | ------- | ------------------------ |
| `RD-CAP-HITS` | Hit cap exceeded | policy |
| `RD-CAP-CHRON` | Chronology row cap | policy |
| `RD-CAP-EDGE` | Edge cap | policy |
| `RD-CAP-LINEAGE` | Lineage depth cap | policy |
| `RD-TCRE-GAP` | TCRE coverage gap | `reconstruction_coverage_gap` |
| `RD-GRAPH-ORPHAN` | Entity without link | `orphan_artifacts` |
| `RD-TRAVERSAL-IDLE` | No walks | `traversal_never_executed` |
| `RD-TRAVERSAL-BLOCKED` | Graph disconnected | graph propagation |
| `RD-LINEAGE-GAP` | Incomplete lineage | lineage builder |
| `RD-REPLAY-UNSAFE` | Upstream replay unsafe | identity/TCRE |
| `RD-INDEX-STALE` | `index_epoch` lag | index job |
| `RD-POLICY-MISMATCH` | Digest pin mismatch | query pins |
| `RD-ADDRESSING-UNRESOLVED` | Bad refs | query |

**RULE RET‑DEG‑01:** New codes require registry amendment + golden vector.

---

## Degradation propagation (substrate pipeline)

| From stage | Trigger class | To retrieval | Consequence code |
| ---------- | ------------- | ------------ | ---------------- |
| canonical | `canonical_backlog_unmaterialized` | retrieval | `RD-TCRE-GAP` (indirect) |
| identity | `replay_conflicted_identity` | retrieval | `RD-REPLAY-UNSAFE` |
| graph | `orphan_artifacts` | retrieval | `RD-GRAPH-ORPHAN` |
| graph | `pending_link_candidates` | retrieval | `RD-TRAVERSAL-BLOCKED` |
| traversal | `traversal_never_executed` | retrieval | `RD-TRAVERSAL-IDLE` |
| tcre | `reconstruction_coverage_gap` | retrieval | `RD-TCRE-GAP` |

Completeness projection MUST emit human-readable propagation chain entries (mirror Phase 06 style).

---

## Lawful missing-data handling

| Case | Behavior |
| ---- | -------- |
| Artifact never existed | Omission `RD-*-GAP` — not fabricated hit |
| Artifact exists but legality forbids | Omission `omitted_legality` |
| Exploration-only artifact in authoritative query | Omission `omitted_exploration_partition` |

---

## Monotonicity

Adding artifacts to upstream (without policy change) MUST NOT **remove** hits from authoritative replay — may only add hits or improve legality class (**RET‑DEG‑02**).
