# Phase 03 — Provenance & Traceability Doctrine

**Status:** normative.

## Obligation

**Every canonical object must be reversible to supporting raw evidence** via deterministic provenance pointers (multi-parent allowed).

## Lineage model (conceptual)

Each canonical record carries:

- **primary_evidence**: one or more `raw_record_id` references (Phase 02),
- **derivation_step**: `{stage: canonicalize, mapping_version, rule_id}`,
- **parent_canonical_refs**: optional pointers when canonical rows derive from other canonical rows (mapping churn),
- **confidence/ambiguity attachments** per ambiguity doctrine.

## Derivation shapes

| Shape | Meaning | Required representation |
| ----- | ------- | ------------------------ |
| **1:1** | Single raw row yields single canonical row | Single primary evidence pointer |
| **N:1** | Multiple raw rows compose one canonical row | List all raw IDs + composition rule id |
| **1:N** | Single raw row fans out (e.g., multiple mentions) | Fan-out rule id + child ids |
| **Many:many** | Rare; must be explicit | Graph of evidence pointers |

## Conflicting evidence ancestry

When raw revisions disagree:

- Canonical layer must not silently merge conflicts into one authoritative fact unless the dispute is represented as explicit structured contention **or** ambiguity records per ambiguity doctrine.
- Historical canonical projections remain addressable via supersession links.

## Auditability

Operators must be able to walk:

`canonical_record → raw_record(s) → provider envelope metadata (Phase 01/02)`

and reverse:

`raw_record → canonical projections referencing it`.

## Runtime lineage semantics (expanded)

### Reverse traceability (canonical → raw)

- Every canonical projection MUST expose at least one **primary evidence edge** to Phase 02 `raw_record_id`.
- Multi-hop traces MAY traverse canonical→canonical edges **only** when each hop carries transform lineage (`phase-03-transform-lineage-doctrine.md`).

### Forward index (raw → canonical)

- Canonical runtime MUST maintain a reversible index from raw record to dependent canonical logical keys for rebuild invalidation and incident drill-down.

### Canonical → raw reconstruction

“Reconstruction” here means **evidential reconstruction**, not semantic summarization:

- Given canonical row id, operator retrieves linked raw payloads + mapping bundle id + rule ids—enough to replay transforms offline.

### Multi-source merge provenance

When **N:1** canonical rows exist:

- Store **full raw id multiset** + **composition_rule_id** + ordering-neutral hash of inputs (for determinism proofs).
- Never merge conflicting field values without explicit **CONTESTED** representation (`phase-03-ambiguity-confidence-doctrine.md`).

### Conflicting evidence persistence

Conflicting revisions remain simultaneously queryable via:

- Ambiguity/contestation records,
- Supersession chains per temporal doctrine,
- Optional parallel canonical candidates **only** when mapping declares enumerated ambiguity classes—never silent pick.

### Evidence attribution continuity

Attribution MUST survive:

- Bundle bumps (via superseded lineage),
- Rebuild jobs (same receipts reproducible),
- Partial failures (failed slices omit projections — do not fabricate bridging facts).

## References

- Failure when lineage cannot be recorded: `phase-03-failure-degradation-doctrine.md`
- Query surfaces (debug): `phase-03-canonical-query-doctrine.md`
- Mapping lineage: `phase-03-transform-lineage-doctrine.md`
