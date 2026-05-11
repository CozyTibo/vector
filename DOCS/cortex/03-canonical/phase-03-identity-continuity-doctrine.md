# Phase 03 — Identity & Continuity Doctrine

**Status:** normative for Phase 03; coordinates with Phase 04 without duplicating it.

## Definitions

| Term | Meaning |
| ---- | ------- |
| **Provider identity** | Stable identifier in provider scope (`user`, `team`, `repo`, …) derivable deterministically from raw payload keys. |
| **Canonical identity** | Phase 03 identifier (`canonical_entity_id`, etc.) computed from `(tenant_id, mapping_version_bundle, provider, provider_identity_tuple)` rules—**not** the universal human identity. |
| **Human identity** | Real-world person continuity across providers — **Phase 04 responsibility**. |
| **Organizational identity** | Teams/orgs spanning tools — **Phase 04+**. |
| **Transient alias** | Deterministic alternate external keys referring to same provider object within one provider (email aliases, login handles) only when evidenced and mapped. |

## Phase 03 obligations

- Emit canonical identities that are **stable under replay** for unchanged inputs (see replay doctrine).
- Preserve **provider identity references** on every canonical object as traceable pointers to raw evidence.
- Represent uncertainty about “who this is” beyond provider IDs using ambiguity records—not guessed merges.

## Phase 03 non-responsibilities (explicit)

- Declaring two provider personas belong to the same human.
- Choosing winners among competing organizational naming interpretations.

These produce **candidate linkage hints** only if explicitly modeled as non-authoritative `hint` edges with zero merge force—default posture is **omit hints** until Phase 04 schema exists.

## Lineage, merges, splits, supersession

- **Supersession:** canonical records move forward via versioned supersede pointers; never silent rewrite-in-place.
- **Splits/merges at canonical layer:** generally **not** performed in Phase 03. If provider emits explicit merge events (e.g., issue transferred with explicit IDs), represent as **events + edges**, not reinterpretation.

## Confidence propagation (identity-specific)

- **Deterministic confidence:** mapping confidence fixed by tables (“this mapping applies”).
- **Probabilistic confidence:** forbidden for identity equality in Phase 03.
- **Unresolved identity:** multiple provider personas remain distinct canonical entities with optional ambiguity bundle linking evidence of uncertainty.

## Replay-safe continuity semantics

- Rebuilding canonical store from raw must recreate the same canonical identity set for the same mapping versions (subject to explicit migration transforms recorded as lineage).

## References

- Canonical model classes: `phase-03-canonical-model-doctrine.md`
- Ambiguity: `phase-03-ambiguity-confidence-doctrine.md`
- Replay/versioning: `phase-03-replay-versioning-doctrine.md`
