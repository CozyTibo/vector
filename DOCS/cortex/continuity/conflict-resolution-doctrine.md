# Conflict-resolution doctrine (deterministic constitutional law)

**Status:** normative doctrine — **no new phases**; strengthens **constitutional correctness** across existing **Phases 01–05** execution reconstruction and continuity substrates.  
**Scope:** deterministic law for **contradictory operational execution evidence** — not negotiation, not ML arbitration, not semantic “tie-break.”  
**Code anchors:** `execution_reconstruction_contracts.py` (`EvidenceLineageHop`, `CommitmentLifecycle`, `NegativeExecutionSignal`, `TemporalAnchorChain`, `IdentityLinkDerivation`); Phase 03 canonical / Phase 05 replay legality docs where conflicts surface in traversal or verification.

**Explicit non-goals:** embeddings, LLM reasoning, probabilistic matching, agents, semantic ownership inference, ingestion redesign, DB redesign, UI redesign, graph exploration features.

---

## 1. Conflict philosophy

**Observable operational truth** takes precedence over **inferred semantic certainty**.

When two evidence items appear to tell different stories:

1. **Both remain inspectable** in the substrate (no hidden winner).  
2. Resolution proceeds by **declared precedence doctrine** (§3) and **conflict outcomes** (§4).  
3. Any residual uncertainty is **bounded ambiguity** with receipts — never silent collapse to a single “truth.”

Conflicts are **coordination facts** about the evidence set, not character judgments.

---

## 2. Conflict classes (normative vocabulary)

These classes label **conflict objects** for receipts, audits, and corpus expectations. They are **not** new coordination kinds on messages; they classify **substrate conflict records**.

| Class | Governs |
|-------|---------|
| `ownership_conflict` | Parallel assignees, contradictory claims, handoff vs deny. |
| `chronology_conflict` | Inconsistent total order, skew vs export sequence, anchor mismatch. |
| `continuity_conflict` | Bridges that cannot be merged without violating linkage law. |
| `commitment_conflict` | Lifecycle contradiction (e.g. completed vs active evidence without supersession). |
| `replay_conflict` | Replay artifact mismatch vs prior receipted hash / walk equivalence violation. |
| `provenance_conflict` | Missing or cyclic `EvidenceLineageHop`, empty `source_raw_record_ids` where forbidden. |
| `escalation_conflict` | Escalation targets vs responses that contradict routing evidence. |
| `resolution_conflict` | Competing `CommitmentResolutionState` evidence without supersession chain. |
| `export_sequence_conflict` | Monotonic export / cursor ordering disagrees with source-native timestamps. |

New classes require **contract or corpus schema version** bump and explicit forbiddance review.

---

## 3. Evidence precedence doctrine (deterministic, ordered)

When rules compete, apply **first match wins** in this **fixed** order (document version id: `precedence_v1`):

1. **Direct system evidence** — connector-native immutable ids, immutable message ts, signed export sequence when available.  
2. **Replay receipts** — prior replay legality receipt hashes stored as authoritative substrate facts for **same** evidence bundle version.  
3. **Authoritative exports** — tenant-scoped canonical exports / org link replay job outputs marked authoritative in registry policy.  
4. **Canonical references** — `NormalizedReference` equality on stable keys (issue id, PR url, deployment id).  
5. **Temporal anchors** — `TemporalAnchor` monotonic cursor breaks ties on equal wall timestamps per temporal reconstruction spec.  
6. **Continuity lineage** — `IdentityLinkDerivation` allowed kinds only (`explicit_linkage`, `temporal_overlap`, `shared_execution_reference`, `stable_organizational_anchor`) — **never** similarity.  
7. **Bounded ambiguity rules** — explicit “hold both” or `partitioned` outcomes before any merge.

**Forbidden:** “most recent message wins” without a rule id; “majority of participants”; model confidence.

---

## 4. Conflict outcomes

Allowed **terminal conflict disposition** labels:

| Outcome | Meaning |
|---------|---------|
| `resolved` | Single outcome selected with **full** lineage to precedence steps 1–6. |
| `degraded` | Partial resolution; some artifacts downgraded; receipts list surviving contradictions as subsumed or isolated. |
| `replay_risky` | Replay equivalence cannot be asserted — async or partial-hash policies per Phase 05 matrix. |
| `unverifiable` | Missing mandatory evidence; no guess. |
| `partitioned` | Two or more **non-mergeable** partitions of entities/walks both retained with partition ids. |
| `quarantined` | Evidence bundle segment excluded from automatic downstream merge until operator explicit action (receipted, not silent drop). |

---

## 5. Ambiguity propagation

Rules for when ambiguity **stays local** vs **propagates**:

| Condition | Propagation |
|-----------|-------------|
| Message-level `uncertainty` only | **Local** — does not relax thread chronology. |
| Unresolved ownership with open ask | **Continuity** — `ownership_continuity_ok` false; may emit `ownership_vacuum`. |
| `TemporalAnchorChain.replay_safe_ordering == unresolved` | **Chronology** + **downstream traversal legality** — walks restricted per Phase 05 policy tables. |
| Contradicted ack/deny on same subject | **Replay legality** → `replay_conflicted` until supersession or scope partition. |
| Quarantined raw slice | **All dependent derivatives** marked `replay_unverifiable` or `partitioned` per policy. |

Propagation is **always receipted** — no silent single-field flip.

---

## 6. Contradiction handling

| Concept | Law |
|---------|-----|
| **Contradiction lineage** | Every contradiction record carries ordered `EvidenceLineageHop` to **both** sides. |
| **Contradiction provenance** | Minimum raw ids from each side; connector origins explicit. |
| **Contradiction receipts** | Hashable summary `{ conflict_class, left_event_ids, right_event_ids, precedence_rule_id, outcome }`. |
| **Contradiction survivability** | Contradictions **persist** in audit substrate until `resolved` or `partitioned` with supersession evidence — not garbage-collected by “cleanup.” |
| **Contradiction expiry** | Only when **new authoritative evidence** closes the branch per §3; expiry is itself receipted with `at_iso` and rule id. |

---

## 7. Temporal conflict law

| Situation | Law |
|-----------|-----|
| **Late arrival** | Append-only substrate; may emit `CrossSourceTemporalReference.late_arrival`; may not rewrite prior reducer outputs in-place without versioned migration. |
| **Chronology skew** | `skew_detected` per contract; degradation receipt required. |
| **Export ordering mismatch** | `export_sequence_conflict`; traversal uses **declared** partial order only. |
| **Anchor conflict** | Competing anchors → `chronology_conflict` + `replay_safe_ordering` downgrade. |
| **Continuity gap** | `continuity_gap` refs recorded; bridges **not** invented to fill gaps. |

---

## 8. Ownership conflict law

| Pattern | Law |
|---------|-----|
| **Parallel assignees** | `ownership_conflict` + `partitioned` or explicit **single** winner only if precedence rule id selects deterministic winner (e.g. earliest explicit claim with non-null subject ref). |
| **Reassignment drift** | `CommitmentDriftSignal` `owner` + handoff edge lineage. |
| **Stale ownership** | Negative signals (`ownership_vacuum`, `dependency_without_owner`) — not HR labels. |
| **Implicit vs explicit ownership** | Implicit ownership **never** overrides explicit claim with better lineage; implicit may only produce `uncertainty` / `coordination_gap`. |
| **Thread ownership discontinuity** | Continuity conflict if bridge law violated; else `continuity` degradation only. |

---

## 9. Forbidden behavior

- **Semantic guessing** — resolving “who really owned it” without evidence.  
- **Hidden conflict resolution** — any merge without receipt.  
- **Silent continuity collapse** — removing a bridge because it is inconvenient.  
- **Probabilistic ownership arbitration** — no scores, no learned weights.  
- **Chronology rewriting without degradation propagation** — if order changes, receipts and legality classes **must** update.

---

## 10. Constitutional invariants

**C1:** Conflicting evidence **must** remain inspectable (audit views, corpus diffs).

**C2:** Conflict resolution **must** preserve provenance lineage — no orphan artifacts.

**C3:** Ambiguity **must not** disappear without authoritative evidence or explicit `partitioned` / `quarantined` outcome.

**C4:** Traversal legality **must** degrade under unresolved chronology conflict — no “best-effort walk” through illegal order.

**C5:** Replay equivalence claims **must** be withdrawn when `replay_conflict` is active for the same bundle version.

**C6:** Negative signals **must not** be used as people-punishment; they remain operational coordination facts.

---

## 11. Related doctrine

| Document | Role |
|----------|------|
| [`golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md) | Fixtures proving conflict outcomes. |
| [`cross-system-continuity-law.md`](./cross-system-continuity-law.md) | What may create cross-system evidence in the first place. |
| `DOCS/cortex/ingestion/execution-temporal-reconstruction-spec.md` | Ordering and silence law. |
