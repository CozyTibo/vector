# Phase 03 — Deterministic Canonicalization Doctrine

**Status:** normative.  
**Defines:** what “deterministic” means for Phase 03; what is explicitly forbidden as probabilistic or interpretive.

## Definitions

- **Deterministic:** For a fixed Phase 02 raw substrate snapshot (including configured mapping version identifiers), canonicalization produces a canonical artifact set such that:

  - Every emitted canonical record’s identity keys are stable functions of declared inputs (including declared normalization tables),
  - Ordering precedence follows `phase-03-temporal-timeline-doctrine.md`,
  - No canonical field depends on randomness, wall-clock “now” inside algorithms (timestamps may be recorded as metadata **about processing**, but cannot silently alter canonical identities),
  - Retry/replay does not create duplicate authoritative identities for the same logical tuple per `phase-03-replay-versioning-doctrine.md`.

- **Structural extraction:** Copying, renaming, typing (into allowed enums), partitioning, joining by explicit keys, parsing formats **specified by mapping tables**, and emitting explicit unknown/partial markers.

- **Semantic inference (forbidden in Phase 03):** Any step that assigns managerial meaning, interprets natural language content beyond deterministic parsing rules, or chooses among interpretive hypotheses without preserving alternatives as explicit ambiguity records.

## Allowed deterministic operations (non-exhaustive)

- Normalizing identifiers and URLs per stable rules (case folding only where explicitly allowed; preserve canonical raw pointers).
- Mapping provider resource types to canonical types using **versioned** mapping tables.
- Extracting explicitly keyed references (IDs, URLs, mention handles) where extraction rules are pure functions of input strings and mapping tables.
- Timestamp normalization when rule is explicit (timezone conversion with declared default only if raw lacks zone—must emit ambiguity/confidence markers per ambiguity doctrine).
- Emitting canonical graph edges that mirror explicitly evidenced relationships in raw payloads (e.g., parent/child IDs present in provider JSON).

## Forbidden operations (hard anti-goals)

- Inferring priority/urgency/blockers/ownership semantics not directly evidenced as structured fields.
- LLM classification of text unless explicitly exempted by a future closure gate (default: forbidden).
- Clustering/embedding similarity to merge entities (Phase 04 domain).
- “Best guess” entity linking across providers (Phase 04 domain).
- Hidden thresholds that change mapping outcomes without surfacing as **mapping version** bumps.

## Evidence grades for fields (required posture)

Canonical fields must carry one of:

- **E0 — provider-explicit:** Present as structured provider fields backing the statement.
- **E1 — deterministic-parse:** Derived only by deterministic grammar/regex/table rules from provider text fields; **must** still preserve raw excerpts as evidence references where ambiguity doctrine requires.

Any field not meeting E0/E1 must be absent or represented under ambiguity/contestation records—not as silent fact.

## Versioning rule (determinism anchor)

Any change to extraction logic that can change outputs **must** bump:

- `canonical_mapping_version` (or equivalent bundle identifier), and/or
- Per-connector mapping micro-version,

so replay equivalence tests can attribute divergence correctly.

## References

- Anti-goals: `phase-03-anti-goals-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
