# Phase 05 — Corruption vectors (OCTS)

**Status:** normative threat model for **semantic drift**, **authority corruption**, and **replay collapse**.  
**Pairs with:** `phase-05-verification-gates-doctrine.md`.

---

## Column legend

Each row: **Vector** | **Detection** | **Prevention** | **CI gate(s)** (minimum)

---

## CV-01 — Derived → authoritative silent promotion

| | |
| - | - |
| **Vector** | Cached BFS path used for merge/governance “evidence.” |
| **Detection** | Receipt audit finds `provenance_class=derived` in merge artifacts OR absence of `execution_path_contains_derived` where strategy requires. |
| **Prevention** | Read barriers; explicit non_authoritative flags; store partitions. |
| **CI gates** | **G-P05-OVD-01**, **G-P05-OVD-02**, **G-P05-EXP-02** |

---

## CV-02 — Phase 03 topology ingress

| | |
| - | - |
| **Vector** | Canonical transform nodes appear as traversable. |
| **Detection** | **G-P05-IMPORT-02** token scan; export subset checks. |
| **Prevention** | Engine only reads import bundle builder output; deny raw SQL joins. |
| **CI gates** | **G-P05-IMPORT-01**, **G-P05-IMPORT-02** |

---

## CV-03 — Ranking / scoring smuggled as policy

| | |
| - | - |
| **Vector** | Numeric edge map influences expansion order without policy hash update. |
| **Detection** | **G-P05-RANK-01** static scan; schema rejects floats/maps. |
| **Prevention** | Closed policy schema; policy hash pins all tie logic. |
| **CI gates** | **G-P05-POL-01**, **G-P05-RANK-01** |

---

## CV-04 — Hash telemetry contamination

| | |
| - | - |
| **Vector** | Wall clock or host name enters hashed JSON. |
| **Detection** | **G-P05-HASH-02** mutation tests. |
| **Prevention** | Strict hash_body key allowlist in walk result contract. |
| **CI gates** | **G-P05-HASH-01**, **G-P05-HASH-02** |

---

## CV-05 — Stale derived index in observed walk

| | |
| - | - |
| **Vector** | Materialized adjacency older than export used without warning. |
| **Detection** | Epoch compare + API warnings; strict rejects. |
| **Prevention** | Default disallow stale; publish barriers. |
| **CI gates** | **G-P05-IDX-01**, **G-P05-JOB-01** |

---

## CV-06 — Partial index publish

| | |
| - | - |
| **Vector** | Consumers read half-written adjacency. |
| **Detection** | FSM illegal state tests; storage shadow prefix checks. |
| **Prevention** | Shadow → validate → atomic publish. |
| **CI gates** | **G-P05-JOB-01**, **G-P05-JOB-02** |

---

## CV-07 — nondeterministic neighbor expansion

| | |
| - | - |
| **Vector** | DB row order changes walk shape. |
| **Detection** | **G-P05-MG-01** golden expansion bytes. |
| **Prevention** | Fingerprint lexicographic ordering law. |
| **CI gates** | **G-P05-MG-01**, **G-P05-RT-01** |

---

## CV-08 — Idempotency key abuse / cache contamination

| | |
| - | - |
| **Vector** | Same key returns different body; cross-tenant cache bleed. |
| **Detection** | Concurrent tests; tenant-prefixed cache keys audit. |
| **Prevention** | Keyed by `(tenant_id, key_hash, body_hash)`. |
| **CI gates** | **G-P05-IDEM-01** |

---

## CV-09 — Exploration data in certification

| | |
| - | - |
| **Vector** | Operator packs exploration walks as “proof.” |
| **Detection** | **G-P05-CLOSE-01** rejects exploration hashes in authoritative section. |
| **Prevention** | Pack builder filters `execution_partition`. |
| **CI gates** | **G-P05-CLOSE-01**, **G-P05-EXP-01** |

---

## CV-10 — Traversal/reasoning collapse via free text

| | |
| - | - |
| **Vector** | `notes`, `summary`, or LLM output stored in walk JSON. |
| **Detection** | **G-P05-ANTI-01**, schema closed enums. |
| **Prevention** | API validation (**`G-P05-SCHEMA-01`**) **MUST** reject forbidden keys at ingress; DB constraints **SHOULD** mirror schema once tables exist (same invariants, not weaker). |
| **CI gates** | **G-P05-ANTI-01**, **G-P05-SCHEMA-01** |

---

## CV-11 — Temporal validity drift

| | |
| - | - |
| **Vector** | Using server `now()` (or any undeclared wall clock) as **`graph_as_of_unix_ns`** / **`snapshot_unix_ns`** without pinning them in **`temporal_anchor`**. |
| **Detection** | Strict mode rejects missing anchor; audit logs. |
| **Prevention** | Explicit request fields; temporal doctrine. |
| **CI gates** | **G-P05-TEMP-01**, **G-P05-TEMP-02** |

---

## CV-12 — Fast path without equivalence proof

| | |
| - | - |
| **Vector** | Optimized engine diverges from receipts. |
| **Detection** | **G-P05-EQUIV-01** dual-run. |
| **Prevention** | Feature flag `fast_path_allowed` default false until suite passes. |
| **CI gates** | **G-P05-EQUIV-01**, **G-P05-EQUIV-02** (warn/nightly) |

---

## CV-13 — Downstream phase JSON injection

| | |
| - | - |
| **Vector** | Phase 06 writes narrative fields into OCTS tables via shared migration mistake. |
| **Detection** | Schema migration review + **G-P05-ANTI-01** on snapshots. |
| **Prevention** | Separate tables / module ownership; CODEOWNERS. |
| **CI gates** | **G-P05-ANTI-01** |

---

## Maintenance

Add a row for every new corruption class discovered in review; **MUST** map to at least one gate or file a **GAP-P0**.
