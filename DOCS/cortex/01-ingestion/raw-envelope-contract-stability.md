# Raw Envelope Contract Stability

## Purpose
Stabilize the Phase 01 raw event envelope so Cortex can start implementation without risking replay corruption, idempotency drift, or provenance discontinuity.

## Contract Classification
- **Frozen Core Contracts:** breaking mutation forbidden.
- **Additive-Only Contracts:** new optional fields allowed, existing semantics fixed.
- **Evolvable Contracts:** changes allowed with explicit versioning + replay compatibility policy.
- **Runtime Metadata:** operational diagnostics only; must not affect replay equivalence.

## Frozen Core Envelope Fields
| Field | Why Frozen | Replay Implication | Idempotency Implication | Provenance Implication | Mutation Policy | Migration Constraint |
| ----- | ---------- | ------------------ | ----------------------- | ---------------------- | --------------- | ------------------- |
| `raw_event_id` | durable raw identity root | replay references remain stable | dedupe/audit linkage anchor | root lineage anchor | immutable | never rewritten |
| `tenant_id` | isolation boundary | replay scope correctness | dedupe scope safety | chain isolation | immutable | no cross-tenant remap |
| `connector_type` | source route semantics | deterministic source path | key-scoped dedupe | source trust context | immutable | remap requires new envelope |
| `connector_instance_id` | instance-level source boundary | replay target resolution | idempotency scoping | source lineage continuity | immutable | remap via new records only |
| `source_event_id` (if present) | provider identity anchor | replay equivalence by source identity | duplicate suppression anchor | source traceability | immutable-if-present | absence/presence cannot be rewritten |
| `source_object_id` + `source_object_type` | object lineage continuity | scoped replay/object reconstruction | object-level dedupe stability | object evidence continuity | immutable | type reinterpretation requires new schema version |
| `source_occurred_at` semantics | chronology anchor | deterministic ordering windows | stable key derivation context | temporal provenance continuity | immutable semantic | cannot redefine meaning |
| `payload_hash` semantics | payload equivalence anchor | replay equivalence checks | dedupe key component | payload integrity continuity | immutable semantic | hash algorithm change requires explicit versioning policy |
| `ingestion_idempotency_key` semantics | dedupe determinism | replay duplicate prevention | primary idempotency contract | lineage uniqueness integrity | immutable semantic | key construction changes require extraction/schema version bump + compatibility plan |
| `replay_job_id` + `replay_version` semantics | replay lineage identity | replay trace isolation | replay-context dedupe guarantees | replay provenance continuity | immutable-if-populated | no semantic repurpose |
| `ingestion_version` tuple semantics (`schema_version`, `extraction_version`, `processor_version`) | deterministic regeneration context | replay comparability | deterministic key derivation context | transformation lineage integrity | additive-only tuple evolution | cannot remove tuple dimensions |
| `provenance.chain_id` + minimum `provenance.source_refs[]` | minimum evidence continuity | replay to evidence trace | dedupe for lineage checks | non-breakable provenance root | immutable minimum requirement | minimum cannot be removed |
| `ordering_metadata` semantics | deterministic ingestion order hints | stable replay traversal | deterministic tie-break behavior | chronology proof support | additive-only fields, fixed semantics | semantic rewrite forbidden |

## Additive-Only Contracts
- `cursor_metadata` keys may be extended, but existing key semantics cannot change.
- optional connector-specific metadata may be added under namespaced extension fields.
- optional observability hints may be added when marked non-authoritative.

## Evolvable Contracts
- connector extension payload adapters,
- non-authoritative diagnostics and enrichment counters,
- optional runtime annotations.

All evolvable changes must preserve:
1. frozen field semantics,
2. replay equivalence for unchanged version context,
3. provenance minimum continuity.

## Runtime Metadata (Replay-Safe Only)
- queue timing diagnostics,
- retry counters,
- processing host/runtime identifiers,
- operator annotations.

Runtime metadata is valid only if excluded from idempotency/replay equivalence logic.

## Implementation-Ready Stability Threshold
Phase 01 contract stability is implementation-ready when:
- frozen core fields are explicit and immutable by doctrine,
- replay-critical semantics are fixed,
- provenance minimums are fixed,
- versioning/evolution rules are explicit.

It does **not** require freezing all future optional metadata.
