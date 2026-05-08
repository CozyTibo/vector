# Phase 03 — Ambiguity & Confidence Doctrine

**Status:** normative.

## Principle

**Ambiguity must never disappear silently.** Canonicalization may refuse to assert a fact; it may not substitute an assertion without evidence.

## Ambiguity objects (first-class)

Represent unresolved states as explicit records (conceptual minimum):

- **Unresolved mapping** — no applicable mapping rule for this raw type/field.
- **Unresolved identity** — cannot choose among candidates without Phase 04 semantics.
- **Conflicting evidence** — two raw revisions imply incompatible structured fields; both retained.
- **Competing canonical candidates** — multiple deterministic interpretations allowed by schema (rare; must be narrowed by mapping version bump, not runtime guess).

Each ambiguity record references:

- Supporting `raw_record_id`(s),
- Rule/table identifiers implicated,
- Status lifecycle (`open`, `superseded_by_evidence`, `superseded_by_mapping_version`, `void`).

## Confidence taxonomy (allowed classes)

| Class | Meaning | Allowed in Phase 03? |
| ----- | ------- | ---------------------- |
| **DETERMINISTIC_RULE** | Output follows a named mapping rule exactly | Yes |
| **TABLE_LOOKUP** | Output from versioned lookup table | Yes |
| **PARSE_FORMAT** | Deterministic parse produced the value | Yes, with raw excerpt refs |
| **UNRESOLVED** | Explicitly not resolved | Yes (preferred over guessing) |
| **CONTESTED** | Multiple evidence-backed alternatives kept | Yes |
| **PROBABILISTIC_MODEL** | Model score drives choice | **No** (Phase 03 default) |
| **OPERATOR_POLICY** | Human-declared override | Only via explicit operator actions outside automatic canonicalization (future gate; default off) |

## Operator visibility minimums

Operators must be able to list:

- Count of unresolved ambiguities by connector/type,
- Top conflicting evidence pairs (by rule id),
- Mapping versions that would reduce ambiguity (if any planned).

## Canonical uncertainty propagation

Downstream phases must treat canonical records as carrying optional ambiguity attachments; absence of ambiguity record **does not** imply semantic completeness across providers—only within declared mapping coverage.

---

## Operational / runtime semantics (ambiguity engine)

This section defines **runtime behavior expectations**—distinct from passive schema descriptions.

### Unresolved canonical candidates

When multiple deterministic interpretations remain valid **without** a narrowing rule:

- Emit **`CONTESTED`** or hold **zero authoritative canonical fact rows**—prefer emitting structured candidate stubs tied to ambiguity ids over picking one.

### Competing mappings

If two bundle-compatible rules could apply:

- **Forbidden:** silent precedence based on insert order.
- **Required:** explicit rule priority table per bundle version OR ambiguity emission when priorities tie.

### Confidence propagation (runtime)

- Confidence labels propagate to downstream indexes **only** as structured metadata—never as hidden ranking weights.
- Downstream phases MUST NOT interpret confidence as semantic importance (anti-goals).

### Ambiguity persistence engine behavior

- Writes MUST be append-only with lifecycle supersession (`open` → `superseded_by_mapping_version` / `superseded_by_evidence`).
- Runtime MUST NOT garbage-collect ambiguity rows without archival policy equivalent to raw memory retention doctrine.

### Unknown / unresolved representation

Represent explicit **UNKNOWN** states via:

- Missing canonical field + attached ambiguity record, **or**
- Typed placeholder value `UNKNOWN` only when schema demands presence—paired with ambiguity reference.

Never coerce UNKNOWN into default structural values that resemble real provider data.

### Operator-visible ambiguity (minimum runtime)

- Streaming counters + exemplar drill-down: unresolved by connector, rule id, bundle id.
- Heatmaps for **ambiguity explosion** detection (see readiness audit).

## References

- Anti-goals: `phase-03-anti-goals-doctrine.md`
- Failure semantics when ambiguity handling itself fails: `phase-03-failure-degradation-doctrine.md`
- Mapping system: `phase-03-mapping-system-doctrine.md`
