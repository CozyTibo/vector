# Phased Roadmap

## Phase 1: Connectors + Ingestion
Define adapter contracts, backfill/incremental strategy, idempotent ingestion envelopes.

## Phase 2: Raw Event Store
Implement immutable raw events, replay checkpoints, retention policy interfaces.
Phase 02 sequencing now includes:
- Steps 1-10 runtime substrate + baseline closure gate,
- Steps 11-16 stabilization pass (progressive trust enforcement readiness, unified verification semantics, replay proof hardening, trust-signal hardening, critical integrity hardening, operational trust proof pass).
Phase 02 closure remains binary-gated on replay/provenance/reconstruction/corruption/admin trust checks, but enforcement posture is calibrated (catastrophic-only hard block initially).
Phase 02 doctrine authority is centralized in `02-raw-store/normative-index.md`.
Phase 02 implementation sequencing is explicitly expanded to Steps 1-16 in `02-raw-store/implementation-plan.md` and `MASTER_TRACKER.md`.

## Phase 3: Canonicalization (implementation-grade program)

Phase 03 is executed as **18 explicit stages** (see `DOCS/cortex/03-canonical/implementation-plan.md` + `MASTER_TRACKER.md`) covering:

- structural ontology + object taxonomy,
- logical keys + deterministic mapping contracts,
- **mapping bundle registry** + transform runtime + transform lineage,
- ambiguity/confidence **runtimes** (persistence + propagation),
- identity continuity (provider-scoped; Phase 04 for cross-tool joins),
- replay/**rebuild**/regeneration semantics with pinned bundles + divergence classes,
- provenance lineage runtime (forward/reverse indexes, multi-source merges),
- temporal ordering + supersession runtime,
- canonical query/retrieval (bounded, anti-goal guarded),
- failure/degradation + **remediation/recovery**,
- **canonical verification engine** (invariants, CI vectors),
- **canonical control plane/admin**,
- stabilization/proof pass,
- **closure + operational certification** (binary gates **G-P03-01–G-P03-21**, including operator visibility gates **G-P03-15–G-P03-21**).

**Normative map:** `03-canonical/phase-03-normative-index.md`. **Canonical control plane:** operator-visible deterministic proof surfaces co-evolve with stages (`phase-03-canonical-control-plane-doctrine.md`, `implementation-plan.md` cross-cutting track). **Anti-goals remain absolute:** structural, deterministic, provenance-safe, replay-safe—no semantic reasoning layer here.

## Phase 4: Entity Resolution
Implement identity linking, confidence scoring, merge/split audit.

## Phase 5: Graph
Build temporal graph edges for decisions, actions, artifacts, and ownership.

## Phase 6: Memory
Create compressed and derived memory layers with quality scoring.

## Phase 7: Reasoning
Introduce causal and timeline inference with deterministic + AI hybrid policy.

## Phase 8: Retrieval
Build query planner and evidence-grounded context pack assembly.

## Phase 9: Synthesis
Expose explainable synthesis outputs with provenance and confidence metadata.

## Phase 10: Admin/Governance
Operational controls for replay, monitoring, policy, and lifecycle management.

## Cross-cutting: admin closure every phase
Default historical rule: Phases **03–09** referenced **Step 6 = runtime + admin closure**.  
**Phase 03 exception (normative):** Phase 03 uses **Steps 1–18**; operator-grade control plane + verification cluster lands in **Steps 16–18** (control plane, stabilization, operational certification). See `MASTER_TRACKER.md` + `03-canonical/implementation-plan.md`.  
**Phase 02 exception:** Step **9** is dedicated Runtime Memory Control Plane; Step **10** establishes baseline closure gate runtime; Steps **11–16** are mandatory stabilization before final closure confidence.  
Phase **10** integrates those slices into the unified governance UX; it does not replace the requirement that earlier phases already shipped their own closure when they completed.
