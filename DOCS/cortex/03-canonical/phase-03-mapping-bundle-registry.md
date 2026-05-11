# Phase 03 — Mapping Bundle Registry (Normative Operational Contract)

**Status:** normative operational contract for the **mapping system**. Treat this document like **production migration governance**: undeclared edits are defects; promotions are gated processes; hashes are law.  
**Anti-goal:** no semantic truth claims—only versioned structural transforms (`phase-03-anti-goals-doctrine.md`).

## Purpose

The registry is the **single authoritative inventory** of what “mapping version” means at runtime: bundle identity, artifact hashes, lifecycle, compatibility edges, ownership, promotion authorization, invalidation scope, and tenant pin policy.

Complements: `phase-03-bundle-pinning-doctrine.md`, `phase-03-oracle-vectors-doctrine.md`, `phase-03-ci-deterministic-enforcement-doctrine.md`.

---

## Core definitions

| Term | Definition |
| ---- | ---------- |
| **Mapping bundle** | Named, versioned set of **immutable artifacts**: ontology slice, rule tables, parse grammars, field maps, per-connector micro-versions, logical-key derivation profile, oracle vector manifests. |
| **Bundle ID** | Immutable identifier for an **exact artifact hash set** (e.g., `mb-2026.05.08.3`). Never reused after retirement. |
| **Artifact hash set** | Deterministic content-addressed digest per artifact file/table **before** bundle promotion; recorded on the bundle record. |
| **Compatibility line** | Directed acyclic graph (declared as ordered sequences per migration path) of bundle IDs stating **which bumps are replay-safe remaps** vs **breaking** (`phase-03-replay-versioning-doctrine.md`). |
| **Breaking mapping change** | Any artifact delta that can change **logical keys**, **canonical ordering**, **evidence-grade classification**, **ambiguity emission**, or **field lineage topology** for the same raw snapshot—unless explicitly classified as **non-breaking** under a documented compatibility rule **and** validated by oracle + CI (`phase-03-deterministic-canonicalization-doctrine.md`). |
| **Pin** | Explicit binding of scope → bundle ID (`phase-03-bundle-pinning-doctrine.md`). |

---

## Lifecycle states (normative)

States are **mutually exclusive**. Transitions are **append-only events** with actor + timestamp + rationale (structural—not prose interpretation).

| State | Meaning |
| ----- | ------- |
| **draft** | Mutable **only inside isolated authoring workspace**; **must not** be referenced by tenant pins, replay jobs, CI promotion, or certification. |
| **candidate** | **Immutable artifact snapshot** locked (hashes fixed); eligible for promotion review + oracle/CI; **must not** receive materialization pins except **explicit certification/test tenants** whitelisted in CI. |
| **approved** | Formerly “active”: **only state** from which **new production pins** may be created by policy (subject to rollout controls). Artifacts **immutable**. |
| **deprecated** | **No new default pins**; existing pins **remain honored** until migrated; rebuild/remap guidance mandatory; still rebuild-addressable. |
| **retired** | **No new pins**; historical attribution only; identifiers **never deleted**; supersession targets documented. |

**Forbidden:** returning `retired` → `approved` without issuing a **new bundle ID** (new lineage).

---

## Roles & authorization (who may promote)

| Role | Authority |
| ---- | --------- |
| **Bundle owner** (named team + on-call) | Authors candidate bundles; accountable for determinism checklist + registry hygiene. |
| **Technical approver(s)** | Required **dual control** for `candidate → approved`: independent review of hashes, compatibility lines, oracle outcomes, CI gates (`phase-03-ci-deterministic-enforcement-doctrine.md`). Approvers **must not** be sole committers of the same bundle artifacts. |
| **Registry administrator** | Executes lifecycle transitions on **records** only when gates pass—does not “edit mappings.” |
| **Emergency freeze authority** | Declares **freeze** on new approvals/pins for a connector slice or globally (see below); cannot waive hash integrity. |

**Promotion rule:** `draft → candidate` requires **immutable hash lock** + manifest completeness.  
**Promotion rule:** `candidate → approved` requires **mandatory oracle PASS** + **CI promotion suite PASS** + anti-goal scan artifact (`phase-03-oracle-vectors-doctrine.md`).  
**Promotion rule:** `approved → deprecated` requires **successor bundle ID** + **compatibility line update** + consumer notification policy.  
**Promotion rule:** `deprecated → retired` only after **declared sunset** + **no remaining approved pins** per policy (or explicit waiver with recorded risk).

---

## Compatibility-line declaration rules

1. Every **approved** bundle **SHALL** declare **supersedes** / **replaces** edges and whether each edge is **breaking** or **non-breaking**.
2. **Non-breaking** edges **MUST** have CI evidence (oracle subset) proving **C2-or-better** remap receipts under declared migration (`phase-03-replay-versioning-doctrine.md`).
3. **Breaking** edges **MUST NOT** be traversable without explicit **pin migration** or **regeneration job**—no implicit upgrade.
4. **Silent compatibility expansion** is **forbidden**: adding a new “compatible” predecessor/successor without updating the bundle record + changelog + CI matrix is a **governance violation** (maps to **C5**).

---

## Changelog semantics (mandatory)

Each bundle carries a **CHANGELOG** sequence (ordered entries). Each entry **SHALL** include:

- **bundle artifact delta summary** (which tables/rules changed),
- **breaking / non-breaking** classification,
- **oracle vectors touched** (manifest IDs),
- **compatibility edges added/changed**,
- **rebuild invalidation scope** (connectors/resource types),
- **references** to signed CI/oracle reports.

**Forbidden:** narrative-only changelog entries that leave structural drift undocumented.

---

## Hash / signature expectations

1. Every artifact file referenced by a bundle **SHALL** have a **cryptographic content hash** recorded at candidate lock.
2. Bundle record **SHALL** store an aggregate **manifest hash** over ordered artifact hashes.
3. **Promotion** requires verifying manifest hash against stored value (**deterministic reproducibility** of artifact assembly).
4. Optional **release signatures** (cryptographic) **MAY** wrap manifest hash; if used, CI **MUST** verify signatures before approval.

---

## Forbidden behaviors (hard)

| Forbidden | Consequence |
| --------- | ----------- |
| **Mutable “hot edits”** to approved/deprecated artifact bodies | **Violation** — issue new bundle ID |
| **Runtime auto-learning** mappings | **Forbidden** (`phase-03-anti-goals-doctrine.md`) |
| **Silent compatibility expansion** | **C5** until remediated |
| **Implicit fallback bundle** (“try latest if pin missing”) in production paths | **Forbidden** — pin resolution must **fail closed** or follow explicit emergency policy (`phase-03-bundle-pinning-doctrine.md`) |
| **Environment-dependent bundle selection** without recorded policy | **Forbidden** |
| **Undeclared edits** outside draft workspace | **Violation** |

---

## Rollback semantics

- **Rollback** never mutates an approved bundle in place.
- **Rollback** means **pin rollback** to a prior **approved** bundle ID **or** issuing a **new** corrective bundle that restores prior behavior under compatibility proof.
- Rollback **SHALL** emit **remediation receipts** and **may** trigger rebuild invalidation scopes.

---

## Emergency freeze semantics

**Freeze** halts:

- new **approvals** (`candidate → approved`),
- new **production pins** (policy-defined),

without altering hashes of existing bundles. Freeze **does not** waive oracle integrity for bundles already **candidate**.

Unfreeze requires **explicit authority** + recorded rationale.

---

## Invalidation propagation rules

When bundle **B** supersedes **A**:

1. Canonical rows carrying **`mapping_bundle_id=A`** are marked **superseded-by-bundle=B** per replay doctrine—**never silent rewrite**.
2. **Invalidation scope** **SHALL** list affected connectors, resource types, and **minimum regeneration/rebuild job class**.
3. **Tenant pin inheritance**: pins pointing at **A** **do not** auto-float to **B**—operators migrate pins or run regeneration jobs (`phase-03-bundle-pinning-doctrine.md`).

---

## Bundle supersession policy

- **Supersession** is **explicit** and **versioned**—each successor bundle ID is unique.
- Multiple successors **forbid** unless **non-overlapping scopes** are documented (split bundles).

---

## Tenant pin inheritance rules

Default policy (override only by written tenant policy artifact):

1. **Child scopes inherit** parent tenant pin **unless** explicitly overridden (narrower scope wins).
2. **New scopes** created after a pin change **inherit current pin** at creation time—no retroactive drift.
3. **Certification pins** may lock bundles for certification tenants independently—must not contaminate production defaults.

Details: `phase-03-bundle-pinning-doctrine.md`.

---

## Rebuild dependency graph expectations

The registry **SHALL** support extracting a **directed graph**:

- nodes = bundle IDs,
- edges = compatibility / supersession,

such that rebuild planners can compute **closure of bundles** needed for a rebuild job and detect **undeclared gaps** (**C5**).

---

## Oracle & rebuild triggers (registry-side obligations)

| Event | Oracle re-run required | Rebuild invalidation forced |
| ----- | ---------------------- | ---------------------------- |
| Logical-key derivation profile change | **Yes** | **Yes** for affected scopes |
| Rule table change affecting output identity/order | **Yes** | **Yes** unless non-breaking proven |
| Grammar/regex table change for E1 fields | **Yes** | Per compatibility classification |
| Changelog-only typo fix **with no artifact change** | **No** (hash unchanged) | **No** |

---

## Certification gate blocks

The following **block** `candidate → approved` and **block Phase 03 closure** until cleared:

- Missing or failing **oracle manifest** for declared connector slice.
- Missing **CI promotion suite** PASS artifact.
- Missing **compatibility line** for declared predecessor when superseding.
- **G-P03-09 / G-P03-10 / G-P03-11** failures (`phase-03-closure-gates-doctrine.md`).

---

## References

- Pinning: `phase-03-bundle-pinning-doctrine.md`
- Replay divergence: `phase-03-replay-versioning-doctrine.md`
- Oracle vectors: `phase-03-oracle-vectors-doctrine.md`
- CI enforcement: `phase-03-ci-deterministic-enforcement-doctrine.md`
- Logical keys: `phase-03-logical-key-doctrine.md`
- Transform lineage: `phase-03-transform-lineage-doctrine.md`
- Mapping system umbrella: `phase-03-mapping-system-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
