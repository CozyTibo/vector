# Phase 03 — Canonical Control Plane Doctrine (Operator / Admin Authority)

**Status:** normative — **authoritative** for Phase 03 operational surfaces, operator obligations, and admin information architecture (logical IA only; not UI implementation).  
**Supersedes:** operational depth previously summarized in `phase-03-operator-control-plane-doctrine.md` (retained as redirect stub).

## Purpose

Canonicalization is **operationally dangerous**: silent drift, invisible ambiguity accumulation, or opaque transforms destroy trust faster than missing features. This doctrine treats **operator/control-plane evolution as a first-class operational track** that **co-evolves** with runtime stages (`implementation-plan.md` §Cross-cutting operator track).

Canonical admin exposes **deterministic operational truth** and **proof artifacts** — **not** semantic analytics.

## Operator philosophy

1. **Explainability over narration** — every canonical projection must be answerable as: *why*, *from which raw*, *via which rules*, *under which bundle*, *with which ambiguity state*.
2. **Proof over vibes** — trust is backed by receipts: verification reports, divergence classes, lineage edges, bundle pins, generation counters—never summaries of “health.”
3. **Structural visibility only** — surfaces display evidenced fields, deterministic classifications, and explicit unknowns—never managerial interpretation.
4. **Co-evolution** — a runtime stage is **not operationally complete** until its **minimum operator surfaces** exist (see `implementation-plan.md`).

## Anti-goals (control-plane specific)

Canonical admin and operators MUST NOT treat Phase 03 UI as:

- A **semantic dashboard** (themes, “insights,” NL explanations of organizational behavior).
- A venue for **AI-generated canonical explanations** or LLM summaries of why records exist.
- **Managerial interpretation** (priority, urgency, ownership semantics beyond evidenced structure).
- **Execution insights** or delivery narratives.
- **Graph cognition** or traversal intelligence products (Phase 05+ domain).
- **Non-deterministic trust scoring** or opaque composite “confidence indexes.”

Allowed displays are **substrate metrics**: counts, rates, divergence codes, bundle IDs, hashes, stale/fresh labels tied to verification timestamps, explicit ambiguity objects—not interpreted meaning.

Full runtime anti-goals remain in `phase-03-anti-goals-doctrine.md`.

## Canonical trust visibility requirements

Operators must be able to establish **operational trust** in canonical outputs:

| Requirement | Minimum operational proof |
| ----------- | ------------------------- |
| **Generation legitimacy** | For any canonical object: bundle id + engine/build id + logical key + mapping rule ids |
| **Evidence grounding** | Raw evidence refs + field lineage refs (`phase-03-transform-lineage-doctrine.md`) |
| **Ambiguity honesty** | Visible ambiguity/contestation records or explicit NONE with coverage scope |
| **Rebuild integrity** | Latest rebuild/regeneration job id, divergence class summary (C0–C5), pin used |
| **Verification freshness** | Last gate sweep timestamp + PASS/FAIL matrix + stale warnings |

Trust must remain **explainable without semantics**—structured receipts only.

## Runtime proof expectations

Operators should receive **deterministic proof artifacts** (conceptual; storage format TBD at implementation):

- **Rebuild receipt:** `{job_id, scope, bundle_pin, engine_build_id, divergence_summary, timestamp}`
- **Lineage receipt:** edges connecting canonical row ↔ raw ids ↔ rule ids
- **Verification bundle:** gate ids → PASS/FAIL + exemplar references for failures
- **Ambiguity snapshot:** counts + exemplar ids by connector/rule/bundle

These artifacts are the **currency** of Phase 03 operational truth—not charts inferring org performance.

---

## Mandatory operator/admin surfaces (normative)

Surfaces **A–H** are **required doctrine**, not optional polish. Implementation may batch UI delivery only if **every surface has an interim operator-accessible path** (CLI/API/export acceptable where UI lags—still deterministic proof, not NL).

### A) Canonical overview

**Operational questions answered**

- Is canonicalization healthy for this tenant/scope?
- What mapping bundle is **effective** (pin resolution)?
- What rebuild/regeneration activity is in flight or recently completed?
- What is **ambiguity pressure** (rates, backlog growth)?
- What is **drift pressure** (divergence codes trending)?
- How many **unresolved mappings** / contested states?
- What is **verification state** (gate matrix, freshness)?
- Is **certification readiness** satisfied for closure?

**Must expose (minimum)**

- Canonical pipeline health (queue lag, failure class counts—not semantic KPIs),
- Active/pinned bundles per connector scope,
- Rebuild job queue snapshot + last completed job receipts,
- Ambiguity counters + explosion warnings (threshold-based),
- Drift/divergence counters by class,
- Verification gate dashboard + freshness/staleness labels,
- Certification checklist completeness for Step 18.

### B) Canonical object inspection

For a selected canonical object, operators MUST see:

| Element | Purpose |
| ------- | ------- |
| Canonical identity | Surrogate id + **logical key** tuple |
| Class / type | Structural ontology label |
| **Logical key** | Full derivation inputs summary (non-secret) |
| Provenance chain | Raw evidence refs + transform steps |
| Raw evidence refs | Phase 02 pointers + envelope peek metadata |
| Transform lineage | Rule/table ids per field (`phase-03-transform-lineage-doctrine.md`) |
| Mapping bundle/version | Exact bundle id + compatibility context |
| Ambiguity/confidence | Attached ambiguity ids + confidence class per doctrine |
| Replay/rebuild generation | Regeneration generation counter / supersession epoch |
| Supersession chain | Predecessor canonical ids + causing raw revision ids |
| Temporal ordering metadata | Ordering keys used per timeline doctrine |
| Reconstruction integrity | Link to verification artifact / divergence status for this row |

### C) Mapping inspection

Operators MUST inspect mapping governance:

- **Active bundles** list + status (`draft`/`active`/etc.),
- **Pins** per tenant/connector scope + effective bundle resolution chain,
- **Compatibility lines** + declared breaking bumps,
- **Remap risk** labels (breaking bump pending; C5 exposure),
- **Invalidation scope** — which canonical scopes marked stale after bump/trust event,
- **Drift classes** observed historically per bundle migration,
- **Ownership** + escalation contacts,
- **Rebuild impact estimation** — counts/slices estimated affected (deterministic estimator; may be bounded).

### D) Replay / rebuild observability

Operators MUST see:

- **Rebuild jobs** — id, scope, pin, status, duration, outcome divergence summary,
- **Regeneration generations** — supersession epochs per logical stream when applicable,
- **Replay divergence classes** — C0–C5 tallies + exemplars,
- **Determinism state** — last determinism gate result tied to engine build,
- **Replay-safe certification** — whether scope meets deterministic rebuild criteria,
- **Drift warnings** — explicit banners when verification stale or divergence unresolved.

### E) Ambiguity review

Operators MUST see:

- Unresolved ambiguity objects with filters (connector, rule, bundle),
- Competing candidates **as structured records** (not ranked “best guess”),
- Confidence classes **as labels**, not weighted dashboards,
- Unresolved rates + rolling windows,
- Escalation thresholds (explicit numeric policy—not semantic),
- **Ambiguity explosion warnings** when growth exceeds thresholds.

### F) Provenance tracing

Operators MUST be able to perform:

- **Forward lineage** — raw → canonical projections list,
- **Reverse lineage** — canonical → raw evidence set,
- **Raw→canonical reconstruction** — enough pointers + bundle + rules to replay transform offline,
- **Canonical→raw reconstruction** — symmetric explanation package,
- **Transform-chain inspection** — ordered rule applications as deterministic chain,
- **Merge/split visibility** — N:1 / 1:N shapes surfaced with composition rule ids.

### G) Verification / certification

Operators MUST see:

- Canonical closure gates **G-P03-01–G-P03-21** matrix with PASS/FAIL,
- **Verification freshness** — last successful sweep timestamp per scope,
- **Proof quality** — exemplar coverage statement (deterministic), not subjective quality scores,
- **Stale verification warnings** — when clock/time budgets exceeded,
- **Unverifiable states** — explicit BLOCKED/WARN semantics when substrate incomplete,
- **Certification readiness** — checklist for Step 18 archival pack,
- **Drift-risk labels** — structural flags tied to C-classes / stale gates—not semantic risk ratings.

### H) Recovery / remediation

Expose **policy-gated** controls with deterministic scope (`phase-03-remediation-recovery-doctrine.md`):

| Control area | Operator visibility |
| ------------ | ------------------- |
| Rebuild triggers | Scoped rebuild + dry-run output |
| Mapping rollback safety | Pin rollback **preview** + compatibility receipts |
| Remap preview | Expected C-class distribution + affected counts (estimate) |
| Impact estimation | Upper/lower bounds deterministic explanation |
| Divergence recovery | Links to failing exemplars + gate ids |
| Ambiguity suppression policies | **Explicit**: suppression is policy-bound audit logs—not deletion |
| Remediation constraints | Always show **cannot fabricate facts** boundaries |

---

## Admin information architecture (logical sections)

Logical sections (non-prescriptive UI tech; prescriptive **operator responsibilities**):

| Section | Operational responsibility |
| ------- | -------------------------- |
| **Overview** | Health + pins + rebuild activity + ambiguity/drift pressure + verification/cert readiness |
| **Canonical Objects** | Search/browse canonical rows + object inspector (§B) |
| **Mapping** | Registry, pins, compatibility, invalidation scope, remap risk (§C) |
| **Replay / Rebuild** | Jobs, generations, divergence classes, determinism/cert flags (§D) |
| **Ambiguity** | Ambiguity explorer + thresholds + explosion warnings (§E) |
| **Provenance** | Tracing tools forward/back + merge/split visibility (§F) |
| **Verification** | Gate matrix + freshness/stale/unverifiable + proof artifacts (§G) |
| **Certification** | Step 18 pack progress + archival completeness |
| **Recovery** | Remediation controls + previews + constraints (§H) |

Phase 10 unified admin may nest these under **Admin → Tenant → Cortex → Canonical*** — naming is product-level; **operator obligations here are normative**.

---

## Certification requirements (operator-facing)

Phase 03 closure (Step **18**) requires **operator-visible** certification pack:

- Archived verification matrix (all gates including operator visibility gates),
- Representative rebuild receipts + divergence ledger for certified slice,
- Ambiguity snapshot + acknowledgment of unresolved backlog scope,
- Mapping pin state + registry compatibility attestations,
- Signed statement of **known operational risks** remaining (economic/scale—not silent).

## Operator-safe remediation boundaries (recap)

Remediation never:

- Invents canonical facts without raw evidence,
- Deletes ambiguity history silently,
- Uses ML to “resolve” ambiguity,
- Hides rebuild drift or mapping invalidation scope.

---

## References

- Anti-goals: `phase-03-anti-goals-doctrine.md`
- Remediation: `phase-03-remediation-recovery-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
- Co-evolution track: `implementation-plan.md` §Cross-cutting operator track
- Replay/rebuild: `phase-03-replay-versioning-doctrine.md`
