# Phase 04 — Anti-Goals Doctrine (Identity & Linking)

**Status:** normative — **frozen** with **P04-01** (`phase-04-normative-index.md` §Program freeze).  
**Audience:** implementers, verification authors, operator-console authors.  
**Companion:** `phase-04-architecture-identity-linking-doctrine.md` §1.3–1.5, `phase-04-control-plane-doctrine.md` §4.

---

## Purpose

Phase 04 establishes **organizational continuity** as **evidence-bound, replay-safe, operator-auditable** linkage. This document lists what Phase 04 **must never become**, so runtime, admin UI, and fixtures do not drift into later-phase concerns or probabilistic authority.

---

## Non-negotiable anti-goals

### Layer boundaries

1. **Not the graph engine (Phase 05)** — no native graph storage, traversal products, force-directed visualization, or path semantics in Phase 04 runtime or operator console.
2. **Not the causal engine (Phase 06)** — no authoritative “A caused B” org facts.
3. **Not retrieval (Phase 07)** — no ranking, semantic search, or relevance UX in Phase 04 admin.
4. **Not synthesis / intelligence (Phase 08)** — no LLM explanations of identity, NL merge suggestions as authority, or automated org narratives.
5. **Not Phase 09 product UX** — operator console remains **substrate inspection** only (`phase-04-control-plane-doctrine.md`).

### Identity and authority

6. **No probabilistic or embedding-default identity** — ML “same person” is not authoritative; no silent collapse of personas into one handle.
7. **No email-only or display-name-only human merge** as default authority (governance doctrine may define narrow exceptions; they must be explicit).
8. **No hint → merge closure** — hints and “might be related” edges **must not** feed merge equivalence closure (`G-P04-02`).
9. **No topology-as-meaning** — Phase 03 materialization / replay DAG edges **must not** be treated as org meaning links without a separate Phase 04 ledger row and evidence model (`G-P04-08`).

### Data integrity

10. **No retroactive raw or canonical rewrite** — continuity is layered **on top of** append-only substrate.
11. **No delete of merge history** — corrections via **compensating** records only.
12. **No bundle-agnostic mutation of Phase 03 logical keys** — Phase 03 boundary preserved.

### Operator experience

13. **No dashboard theater** — green counts without receipts, drift classes, and drilldown are insufficient for “healthy.”
14. **No graph visualization theater** in admin — see control plane §3 (tables + inspectors + receipts first).

---

## Allowed (not anti-goals)

- Deterministic **candidate** links from versioned rules.
- **Authoritative** links and merges only via ledger + policy.
- **Ambiguity** and **multiplicity** surfaced honestly in queues.
- **OrgGraphProjectionV1** **metadata** preview for Phase 05 handoff (not traversal UI).
- **Hostile mock data** that stresses continuity **without** random noise (`phase-04-mock-data-strategy.md`).

---

## References

- `phase-04-normative-index.md`
- `phase-04-implementation-plan.md` §3.7
- `phase-04-control-plane-doctrine.md` §4
