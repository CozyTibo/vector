# Phase 05 — Organizational Continuity Traversal Substrate (OCTS) — Normative index

**Status:** normative specification program — **PHASE05_PROGRAM_FREEZE_VERSION `1`** (see §Program freeze).  
**Role:** single constitutional entry for OCTS; step↔doctrine map; shared vocabulary; canonical serialization and hashing law; freeze-bundle (**FF-0..FF-5**) registry; doctrinal dependency DAG.  
**Non-role:** This index SHALL NOT substitute for step-specific doctrines; each linked file is independently normative for its slice.

**Upstream (hard):** Phase 04 `phase-04-graph-boundary-doctrine.md`, `phase-04-graph-projection-export-doctrine.md`, `phase-04-temporal-validity-and-revocation-doctrine.md`, `phase-04-continuity-replay-doctrine.md`.  
**Downstream:** Phase 06–09 MUST consume OCTS only through contracts in this tree; abuse vectors in `phase-05-corruption-vectors.md`.

---

## Program freeze (P05-01)

| Field | Value |
| ----- | ----- |
| **PHASE05_PROGRAM_FREEZE_VERSION** | `1` — MUST match runtime constant `vector.domains.cortex.traversal.normative.PHASE05_PROGRAM_FREEZE_VERSION` when OCTS package ships. |
| **Scope** | Normative index; vocabulary; document hierarchy; **FF-0..FF-5** freeze bundle definitions; canonical JSON profile; **edge_fingerprint** law; **walk_result_hash** / **policy_hash** boundary rules; step program **1–26**. |
| **Constitutional boundary** | OCTS is **traversal + continuity + replay + provenance substrate** only — see `phase-05-anti-goals-doctrine.md`. |

**REPLAY REQUIREMENT:** Any artifact labeled **authoritative** in OCTS MUST reproduce under pinned inputs per `phase-05-walk-replay-doctrine.md` and `phase-05-index-replay-doctrine.md`.

---

## Freeze bundle registry (FF-0..FF-5)

Bundles are **doctrine freeze checkpoints**; **FF-5** aligns with phase closure (**G-P05-CLOSE-***). Runtime MAY NOT ship traversal persistence until prior bundles for its slice are satisfied (see step table).

| Bundle | After steps (normative) | Frozen artifacts |
| ------ | ----------------------- | ---------------- |
| **FF-0** | **1–2** | Vocabulary; observed vs derived law; program version. |
| **FF-1** | **1–5** | Anti-goals; import boundary extension; traversal vs reasoning output algebra. |
| **FF-2** | **1–8** | Multigraph model; temporal walk law; walk policy algebra. |
| **FF-3** | **1–12** | Walk result contract; hop receipts; exploration isolation; diagnostics taxonomy. |
| **FF-4** | **1–15** | Derived index contract; index build job; walk execution strategy (incl. fast-path equivalence). |
| **FF-5** | **1–26** | Full verification suite design + tenant slice + control plane + economics + closure gates — **constitutional completion**. |

---

## Doctrinal dependency DAG (informative, acyclic)

Edges read **A → B** as “B depends on A”.

```
phase-05-normative-index (this file)
  → phase-05-anti-goals-doctrine
  → phase-05-observed-vs-derived-doctrine
phase-04-graph-boundary-doctrine + phase-04-graph-projection-export-doctrine
  → phase-05-graph-import-boundary-doctrine
phase-05-traversal-vs-reasoning-doctrine
  → phase-05-walk-result-contract
  → phase-05-hop-receipt-doctrine
phase-05-multigraph-model-doctrine
  → phase-05-temporal-walk-doctrine
  → phase-05-walk-policy-doctrine
phase-05-walk-result-contract + hop-receipt + diagnostics + exploration
  → phase-05-runtime-execution-model
  → phase-05-walk-api-contracts
phase-05-derived-index-contract-doctrine
  → phase-05-index-build-job-doctrine
  → phase-05-index-replay-doctrine
phase-05-walk-execution-strategy-doctrine
  → phase-05-walk-replay-doctrine
  → phase-05-traversal-equivalence-doctrine
phase-05-idempotency-and-retry-doctrine
  → phase-05-verification-gates-doctrine
  → phase-05-tenant-verification-integration
  → phase-05-control-plane-doctrine
  → phase-05-readiness-economics-doctrine
  → phase-05-closure-gates-doctrine
```

---

## Step program ↔ primary doctrine (1:1)

| Step | Title | Primary normative file |
| ---- | ----- | ---------------------- |
| 1 | Normative index + program freeze | **This file** |
| 2 | Observed vs derived traversal | `phase-05-observed-vs-derived-doctrine.md` |
| 3 | Anti-goals | `phase-05-anti-goals-doctrine.md` |
| 4 | Graph import boundary | `phase-05-graph-import-boundary-doctrine.md` |
| 5 | Traversal vs reasoning | `phase-05-traversal-vs-reasoning-doctrine.md` |
| 6 | Multigraph model | `phase-05-multigraph-model-doctrine.md` |
| 7 | Temporal walk | `phase-05-temporal-walk-doctrine.md` |
| 8 | Walk policy | `phase-05-walk-policy-doctrine.md` |
| 9 | Walk result contract | `phase-05-walk-result-contract.md` |
| 10 | Hop receipt | `phase-05-hop-receipt-doctrine.md` |
| 11 | Exploration mode | `phase-05-exploration-mode-doctrine.md` |
| 12 | Walk diagnostics | `phase-05-walk-diagnostics-doctrine.md` |
| 13 | Derived index contract | `phase-05-derived-index-contract-doctrine.md` |
| 14 | Index build job | `phase-05-index-build-job-doctrine.md` |
| 15 | Walk execution strategy | `phase-05-walk-execution-strategy-doctrine.md` |
| 16 | Traversal engine runtime | `phase-05-runtime-execution-model.md` |
| 17 | Walk APIs | `phase-05-walk-api-contracts.md` |
| 18 | Sync walk limits | `phase-05-walk-api-contracts.md` §Sync limits |
| 19 | Walk replay | `phase-05-walk-replay-doctrine.md` |
| 20 | Index replay | `phase-05-index-replay-doctrine.md` |
| 21 | Traversal equivalence | `phase-05-traversal-equivalence-doctrine.md` |
| 22 | Verification gates | `phase-05-verification-gates-doctrine.md` |
| 23 | Tenant verification integration | `phase-05-tenant-verification-integration.md` |
| 24 | Control plane | `phase-05-control-plane-doctrine.md` |
| 25 | Readiness + economics | `phase-05-readiness-economics-doctrine.md` |
| 26 | Closure gates | `phase-05-closure-gates-doctrine.md` |

**Shared:** `phase-05-idempotency-and-retry-doctrine.md` applies to steps **14–21** and APIs **17–18**.

---

## Vocabulary (stable — MUST NOT overload)

| Term | Definition |
| ---- | ---------- |
| **Walk** | Bounded deterministic traversal execution over an **authorized edge multiset** at a **temporal anchor**, under a **walk policy**, producing a **walk result** (and **hop receipts**). |
| **Observed hop** | Hop whose **evidence binding** references an **authoritative org link** (or primitive boundary per import doctrine) visible in the import surface at the anchor. |
| **Derived hop** | Any hop produced using **materialized structure**, **cache**, **precomputed adjacency**, or **non-ledger shortcut** — MUST be tagged **derived** in receipts and MUST NOT be promoted to authoritative without violating constitution. |
| **Temporal anchor** | Authoritative object **`{ tenant_id, export_id, export_sequence, projection_content_hash, snapshot_unix_ns, graph_as_of_unix_ns }`** per `phase-05-temporal-walk-doctrine.md` §3.1 (hashed fields use **`unix_ns`** objects per `phase-05-canonicalization-profile.md`). |
| **edge_fingerprint** | **REQUIRED** stable identifier for an traversable edge instance; **LAW:** `edge_fingerprint = H_canonical( sorted_key_parts )` where key parts are exactly `{source_node_id, target_node_id, link_row_stable_id, validity_half_open, link_type_code, bundle_scope_id}` per §Edge fingerprint law. |
| **Path multiset** | Ordered walk with **allow_repeat_vertices** controlled by policy; multiset of **edge_fingerprint** for cycle/truncation diagnostics — canonical serialization MUST sort **diagnostic edge multiset** for hash **only when** policy declares **unordered diagnostic bundle** (default: **ordered path** for `walk_result_hash`). |
| **index_epoch** | Monotonic **uint64** per tenant (or per partition) incremented on **committed** derived-index successful replay completion — see derived index contract. |
| **walk_result_hash** | Hash over **canonical walk result body** per `phase-05-walk-result-contract.md`; **MUST** exclude volatile telemetry fields listed there. |
| **policy_hash** | Hash over **canonical walk policy** object frozen at walk start. |
| **Exploration partition** | Isolated receipt/result namespace when `exploration_mode=true` — MUST NOT write into authoritative artifact stores. |

---

## Edge fingerprint law (normative summary)

**INVARIANT EFP-01:** Every traversable edge instance MUST have exactly one **edge_fingerprint** computable from **import-visible** fields only.  
**INVARIANT EFP-02:** Parallel edges (same endpoints, different org links) MUST yield **different** fingerprints.  
**INVARIANT EFP-03:** Fingerprints MUST be stable across process restarts given identical **OrgGraphProjectionV1** row content for that edge.  
Full derivation and forbidden shortcuts: `phase-05-multigraph-model-doctrine.md`.

---

## Canonical serialization (**OCTS-CANON-1**)

**Authoritative law:** `phase-05-canonicalization-profile.md`.  
This index **does not** duplicate JCS rules, idempotency bytes, or instant encoding — violations are **`FS-CANON-***` class in that file.

**Deterministic verification mode:** `OCTS_VERIFICATION_MODE=strict` **MUST** reject non-conformant bodies at ingress per **`OCTS-CANON-1`**.

---

## Constitutional completion criteria (phase-level)

Phase 05 is **constitutionally complete** (doctrine + enforcement design) when **all** hold:

1. **FF-5** satisfied: every step **1–26** has a **Shipped** normative file and **G-P05-*** gate list is closed for **P05-22**.  
2. **Replay integrity matrix** (`phase-05-replay-integrity-matrix.md`) has **no** open **P0** gaps.  
3. **Corruption vectors** (`phase-05-corruption-vectors.md`) each have **detection + prevention + CI** rows.  
4. **Gap matrix** (`phase-05-spec-gap-matrix.md`) §**Active P0** is **empty** (constitutional doctrine closure); waivers only via `waivers/verification_waivers.yaml`.  
5. **`MASTER_TRACKER.md`** §Phase 05 **Doctrine strength** row reads **Frozen**; **CI execution** and **production runtime** remain honest **Not started** / **Blocked** until code ships — see tracker’s Phase 05 layer table.

**Runtime “Frozen”** additionally requires migrations, worker idempotency keys, and admin routes per steps **16–26** as implemented.

---

## Legacy path prohibition

`DOCS/cortex/05-graph/*` is **SUPERSEDED** and **non-normative** — see banners in those files. **MUST NOT** implement OCTS from `05-graph`.

---

## Document hierarchy (normative tree)

All paths under `DOCS/cortex/05-traversal/`.

| File | Role |
| ---- | ---- |
| This file | Index, vocabulary, laws, FF bundles, DAG, completion criteria |
| `phase-05-observed-vs-derived-doctrine.md` | Provenance classes; authority; regeneration |
| `phase-05-anti-goals-doctrine.md` | Constitutional non-cognition |
| `phase-05-graph-import-boundary-doctrine.md` | Ingress from P04 export; forbidden tokens |
| `phase-05-traversal-vs-reasoning-doctrine.md` | Output algebra |
| `phase-05-multigraph-model-doctrine.md` | Nodes, edges, neighbor ordering |
| `phase-05-temporal-walk-doctrine.md` | Anchors, validity, supersession |
| `phase-05-walk-policy-doctrine.md` | Budgets, filters, tie-breaks |
| `phase-05-walk-result-contract.md` | Canonical walk result + hashes |
| `phase-05-hop-receipt-doctrine.md` | Per-hop evidence envelope |
| `phase-05-exploration-mode-doctrine.md` | Non-authoritative isolation |
| `phase-05-walk-diagnostics-doctrine.md` | skip_reason, truncation, cycles |
| `phase-05-derived-index-contract-doctrine.md` | Materialized structures; epoch |
| `phase-05-index-build-job-doctrine.md` | Async build states |
| `phase-05-walk-execution-strategy-doctrine.md` | Online vs materialized; fast-path |
| `phase-05-runtime-execution-model.md` | Engine semantics |
| `phase-05-walk-api-contracts.md` | HTTP; OpenAPI generated from `schemas/` |
| `phase-05-idempotency-and-retry-doctrine.md` | Jobs + APIs |
| `phase-05-walk-replay-doctrine.md` | Walk regeneration law |
| `phase-05-index-replay-doctrine.md` | Index regeneration law |
| `phase-05-traversal-equivalence-doctrine.md` | Double-run / async permutations |
| `phase-05-verification-gates-doctrine.md` | **G-P05-*** |
| `phase-05-tenant-verification-integration.md` | Tenant aggregate slice |
| `phase-05-control-plane-doctrine.md` | Operator surfaces |
| `phase-05-readiness-economics-doctrine.md` | **G-P05-ECO-*** |
| `phase-05-closure-gates-doctrine.md` | Certification + closure |
| `phase-05-canonicalization-profile.md` | **OCTS-CANON-1** — JSON, NFC, instants, idempotency bytes |
| `phase-05-ci-enforcement-architecture.md` | **G-P05-*** CI topology, stages, waivers |
| `phase-05-runtime-legality-matrix.md` | When runtime is legal; forbidden deployments |
| `phase-05-certification-pack-format.md` | **OCTS-CERT-PACK-1** archive law |
| `schemas/` | JSON Schema — authoritative request/response shapes |
| `waivers/verification_waivers.yaml` | Time-bounded gate waivers |
| `phase-05-spec-gap-matrix.md` | Amendments + residual **P2** only |
| `phase-05-replay-integrity-matrix.md` | Replay laws |
| `phase-05-corruption-vectors.md` | Abuse + detection |

---

## Verification gates pointer

Canonical gate IDs and acceptance criteria: `phase-05-verification-gates-doctrine.md`. This index SHALL NOT duplicate gate text.
