# Phase 03 — Canonical Model Doctrine (Structural Primitives)

**Status:** normative.  
**Scope:** define canonical **classes**, **separation of concerns**, and what may be transformed vs what must remain raw-only.

## Mission (restated)

Phase 03 is the **deterministic structural projection** from heterogeneous provider-shaped raw memory (Phase 02) into **stable canonical records** with full provenance. It is **not** a reasoning layer.

## Core distinctions (must remain crisp)

| Term | Definition |
| ---- | ---------- |
| **Raw evidence** | Append-only Phase 02 records (`raw_*` lineage), preserving provider payloads and Phase 01 logical identity/revision keys. Immutable truth substrate. |
| **Canonical projection** | Derived representation for traversal/query/replay; always supersedeable by versioning; never deletes raw. |
| **Canonical identity** | Stable identifier for a canonical record **within** Phase 03 naming/version rules; not necessarily human identity. |
| **Canonical continuity** | Temporal/supersession linkage across canonical versions for the same logical stream of evidence. |
| **Canonical lineage** | Directed derivation graph from raw evidence → canonical records → later canonical records (mapping churn). |

## Canonical object classes (initial taxonomy)

Each class has:

- Immutable canonical primary identifier (`canonical_*_id`) rules per replay doctrine,
- Required provenance envelope per provenance doctrine,
- Temporal anchors per timeline doctrine,
- Optional ambiguity attachments per ambiguity doctrine.

### Structural entities (examples)

- **Person** — provider-native actor objects when evidenced (Slack user, GitHub user, Linear user).
- **Account / Installation / Workspace** — tenancy/installation boundaries when evidenced.
- **Team / Channel / Conversation** — collaboration containers.
- **Repository / Project / Initiative / Cycle** — delivery/planning containers when evidenced.

### Structural artifacts

- **Document / Page / Database row** — durable content artifacts with stable provider IDs.
- **Pull request / Issue / Thread / Message** — discrete communication/review units.
- **Meeting / Recording / Transcript segment** — coordination/timeboxed artifacts.

### Events

- **Canonical event** — something that **happened** at a time or was **observed** at a time; must anchor to evidence and timeline doctrine.
- **Timeline mutation** — canonical records representing state transitions **when evidenced** as structured lifecycle fields (open/closed/merged), not inferred narrative.

### Relationships

- **Canonical relationship / edge** — directed or undirected labeled links **when evidenced** (parent/child, blocks, mentions, membership). Phase 03 does not invent edges from text.

### References

- **Canonical reference** — pointer objects capturing `{kind, provider, stable_key, raw_record_ref}` where `stable_key` derivation is deterministic.

### Snapshots (optional class)

- **State snapshot** — materialized non-semantic projection of explicit provider fields at a revision (use sparingly; prefer events + supersession).

## Boundary rules: entity vs event vs artifact vs relationship

- **Entity:** enduring identity bearer (person/team/repo/issue as an object).
- **Event:** occurrence record (message posted, review submitted, commit pushed) with chronology anchors.
- **Artifact:** content-bearing object (file/document/transcript).
- **Relationship:** linkage record between two or more canonical identities.
- **State snapshot:** only for explicit structured state when event modeling is insufficient—must not smuggle interpretation.

## What becomes canonical vs raw-only

**Becomes canonical when:**

- There is a Phase 02 raw record (or deterministic bundle of records) providing stable keys,
- Mapping tables declare a canonical projection,
- Provenance can enumerate supporting raw refs.

**Remains raw-only when:**

- Payload is prohibited by policy from projection,
- Mapping version lacks a rule (must emit unresolved canonicalization state—not silent drop),
- Evidence is connectivity/ping/auxiliary-only per Phase 01 classifications.

## Immutability rules

- Raw evidence is immutable (Phase 02).
- Canonical rows are **append-only logical history** with supersession; physical deletes forbidden except regulated tombstones with replay-safe semantics.

## Cross-phase boundary

- Cross-provider **same human** linking and organizational equivalence decisions live in **Phase 04**. Phase 03 may emit **candidate hooks** (deterministic keys), not resolutions.

## References

- Anti-goals: `phase-03-anti-goals-doctrine.md`
- Identity semantics: `phase-03-identity-continuity-doctrine.md`
- Provenance: `phase-03-provenance-traceability-doctrine.md`
