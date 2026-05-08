# Phase 03 — Canonicalization Implementation Plan (Implementation-Grade Sequencing)

**Last updated:** 2026-05-08 (cross-cutting operator track + control-plane co-evolution)  
**Purpose:** **Granular operational sequencing** for a deterministic canonical substrate—**not** doctrine rewrite. Doctrines remain authoritative in `phase-03-*.md` and `phase-03-normative-index.md`.

## Anti-drift principle

Each numbered stage maps to **one primary runtime responsibility**. Stages **may not** be merged during execution without an explicit tracker amendment—prevents “different engineers interpreting the same umbrella step differently.”

## Runtime responsibility matrix (independence)

| Concern | Primary stages | Must remain isolated from |
| ------- | ------------- | --------------------------- |
| Mapping system (registry, bundles, transforms, lineage) | **01–06** | Replay orchestration internals |
| Replay / rebuild / regeneration | **10** | Mapping table authoring |
| Ambiguity / confidence persistence | **07–08** | Verification scoring semantics |
| Provenance graph | **11** | Query ranking / NL search |
| Temporal ordering | **12** | Causal reasoning |
| Canonical query / retrieval | **13** | Semantic/AI retrieval |
| Failure + remediation | **14** | “Fixing data” without raw |
| Verification engine | **15** | Admin layout / UX |
| Control plane / admin | **16** | Core transform engine |
| Stabilization + certification | **17–18** | New feature work |

## Stage list (1–18) — canonical execution program

| Stage | Name | Primary deliverable (runtime/ops) | Doctrine anchors |
| ----- | ---- | --------------------------------- | ---------------- |
| **01** | Canonical ontology foundations | Frozen **structural** ontology slice: allowed types, enums, non-interpretive class graph | `phase-03-canonical-model-doctrine.md`, `phase-03-anti-goals-doctrine.md` |
| **02** | Canonical object taxonomy | Authoritative class list + entity/event/artifact/edge/snapshot boundaries | `phase-03-canonical-model-doctrine.md` |
| **03** | Logical key doctrine + key oracle | Per-class logical key spec + test vectors (pre-code) | `phase-03-logical-key-doctrine.md` |
| **04** | Deterministic mapping contracts | Rule/table shapes, evidence grades, forbidden ops | `phase-03-deterministic-canonicalization-doctrine.md` |
| **05** | Mapping bundle registry + versioning | Live registry process + pins + compatibility + ownership | `phase-03-mapping-bundle-registry.md`, `phase-03-mapping-system-doctrine.md` |
| **06** | Canonical transform runtime | Deterministic engine applying bundles; field lineage emission | `phase-03-transform-lineage-doctrine.md`, `phase-03-mapping-system-doctrine.md` |
| **07** | Ambiguity persistence runtime | Storage + lifecycle for unresolved/contested states | `phase-03-ambiguity-confidence-doctrine.md` |
| **08** | Confidence propagation runtime | Propagation as structured metadata (not ranking) | `phase-03-ambiguity-confidence-doctrine.md` |
| **09** | Canonical identity continuity | Provider-scoped identity stability; Phase 04 handoff hooks | `phase-03-identity-continuity-doctrine.md` |
| **10** | Replay / rebuild / regeneration runtime | Job orchestration, pins, divergence classes C0–C5, receipts | `phase-03-replay-versioning-doctrine.md` |
| **11** | Provenance lineage runtime | Forward/reverse indexes, multi-source merge records | `phase-03-provenance-traceability-doctrine.md` |
| **12** | Temporal continuity + ordering runtime | Deterministic ordering + supersession + rebuild sort keys | `phase-03-temporal-timeline-doctrine.md` |
| **13** | Canonical query + retrieval runtime | Supported query classes, budgets, anti-goal enforcement | `phase-03-canonical-query-doctrine.md` |
| **14** | Failure, degradation, remediation | Classified failures + **policy-gated** recovery flows | `phase-03-failure-degradation-doctrine.md`, `phase-03-remediation-recovery-doctrine.md` |
| **15** | Canonical verification engine | Gate automation, CI vectors, divergence reporting | `phase-03-verification-engine-doctrine.md`, `phase-03-closure-gates-doctrine.md` |
| **16** | Canonical control plane + admin | Operator visibility/actions; mandatory surfaces **A–H** | `phase-03-canonical-control-plane-doctrine.md` |
| **17** | Stabilization + proof pass | Soak, perf/replay economics probes, large-tenant drills | `phase-03-implementation-readiness-audit.md` (operational) |
| **18** | Closure + operational certification | **G-P03-01–G-P03-21** evidence pack + sign-off (includes operator visibility gates) | `phase-03-closure-gates-doctrine.md`, `phase-03-canonical-control-plane-doctrine.md` |

## Dependency graph (simplified)

```
01 → 02 → 03 ─┬→ 04 → 05 → 06 ─┬→ 07 → 08
              │                 ├→ 09
              │                 ├→ 10 → 11 → 12
              │                 └→ 13
14 ↔ 10/11/07 (failure loops)     15 consumes 06–12 outputs
15 → 16 → 17 → 18
```

**Rule:** **06** unlocks **07–13** parallelization where infra allows; **15** must not start until **06 + 07 + 10 + 11 + 12** have minimally viable runtime paths.

---

## Cross-cutting operator / control-plane track (co-evolution, mandatory)

**This is not a “final admin step.”** Operator-visible deterministic proof **co-evolves** with runtime stages. A stage is **operationally incomplete** if operators cannot audit its failure modes using **minimum surfaces** defined in `phase-03-canonical-control-plane-doctrine.md`.

### Principles

1. **Every risky runtime gains a matching audit surface** before the stage can be marked complete (interim paths may be API/CLI/export—never undocumented internals).
2. **Canonical trust must be explainable** without semantics—receipts, ids, matrices, lineage—not dashboards inferring org meaning.
3. **Stages 16–18** aggregate hardening and certification; they **do not substitute** for interim visibility where safety demands it.

### Stage → minimum operator visibility before “stage complete”

| Stage | Runtime concern | Minimum operator surface (see canonical control plane §A–H) |
| ----- | ----------------- | ------------------------------------------------------------- |
| **05–06** | Mapping registry + transforms | **Mapping inspection** skeleton: bundles visible; pins readable; remap risk flagged |
| **07–08** | Ambiguity/confidence | **Ambiguity review** skeleton: unresolved counters + exemplar drilldown path |
| **10** | Replay/rebuild/regeneration | **Replay/Rebuild** observability: jobs + divergence ledger + receipts |
| **11** | Provenance lineage | **Provenance tracing**: forward/reverse drill paths (may be query-backed CLI at first) |
| **12** | Temporal ordering | Object inspector shows ordering metadata + supersession hooks |
| **15** | Verification engine | **Verification** dashboard: gate matrix + staleness/freshness |
| **16** | Consolidated control plane | Full **IA sections** operational per doctrine (Overview … Recovery) |
| **17–18** | Proof + certification | **Certification** pack + archived artifacts satisfying **G-P03-15–G-P03-21** |

**Hard rule:** **Mapping runtime cannot close without mapping inspection.** **Replay runtime cannot close without rebuild observability.** **Ambiguity runtime cannot close without ambiguity review surfaces.** **Provenance runtime cannot close without lineage tracing.** **Verification cannot close without operator-visible gate/cert surfaces.**

## Readiness checklist (pre-Stage-06 coding)

- Registry + bundle pins drafted (**Stage 05**).
- Logical key oracle vectors drafted (**Stage 03**).
- Gate fixtures inventory exists (**Stage 15** prep parallel to **03–05**).

## Exit criteria (phase closure)

- **Stage 18** complete: gates **G-P03-01–G-P03-21** PASS on certified connector slice + archived evidence (**includes operator visibility gates G-P03-15–G-P03-21**).
- Operator-visible deterministic proof pack archived per `phase-03-canonical-control-plane-doctrine.md`.
- Rebuild economics / ambiguity explosion risks **explicitly recorded** (even if mitigations are operational—not silent).

## Explicit blockers & risks

See `phase-03-implementation-readiness-audit.md` §Remaining operational risks.

## References

- Normative index: `phase-03-normative-index.md`
- Tracker alignment: `MASTER_TRACKER.md` Phase 03 Steps **1–18**
