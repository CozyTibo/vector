# Phase 03 — Bundle Pinning Doctrine (Deterministic Resolution)

**Status:** normative.  
**Purpose:** eliminate **floating mappings**, **environment-relative resolution**, and **implicit “latest”** behavior. Pins are **law** for determinism proofs.

**Anti-goals:** unchanged — no semantic cognition; pins bind **structural transforms only** (`phase-03-anti-goals-doctrine.md`).

## Definitions

| Term | Definition |
| ---- | ---------- |
| **Tenant-level pin** | Binding `(tenant_id, scope_selector) → mapping_bundle_id` where scope_selector may partition by connector, connection, resource-type slice, or certification lane—**declared in policy**, not inferred. |
| **Replay-job pin** | Binding `(canonical_replay_job_id) → mapping_bundle_id` fixed at job creation; **immutable** for job lifetime. |
| **Rebuild-generation pin** | Binding `(rebuild_job_id, generation_counter) → mapping_bundle_id` capturing which bundle produced which generation of outputs. |
| **Certification pin** | Binding used only for **certification tenants / slices** to freeze bundles for evidence packs; isolated from production defaults. |
| **Object-level lineage** | Every canonical object **SHALL** record **`mapping_bundle_id`** + **manifest hash** (or bundle record hash) sufficient to resolve registry entry (`phase-03-transform-lineage-doctrine.md`). |

---

## Deterministic resolution algorithm (normative outline)

Given a materialization or rebuild job:

1. Collect applicable **tenant pins** matching narrowest scope.
2. If **replay-job pin** present, it **wins** over tenant default for that job.
3. If **rebuild-generation pin** declared on job, it **wins** for that generation.
4. If **certification pin** applies, it wins **only** inside certification scope.
5. If no pin matches: **FAIL CLOSED**—do not fabricate a bundle.

**Forbidden:**

- **Floating mappings:** resolver **must not** pick “whatever bundle is newest” without an explicit **approved** pin policy artifact.
- **Environment-dependent bundle selection** without a **written mapping** (e.g., config table versioned alongside bundles): **forbidden** for authoritative paths.
- **Time-relative bundle resolution** (“use bundle valid at clock T”) for identity/order: **forbidden**—use explicit pins + regeneration jobs.

---

## Pin inheritance

1. **Narrow scope overrides broad** (e.g., per-connector overrides tenant default).
2. **Child tenants / workspaces** inherit parent pin **unless** explicitly detached (policy artifact required).
3. **New resources** created under an existing scope **inherit current pin** at creation—no retroactive drift.

---

## Pin immutability during replay

- **Replay-job pins** are immutable for the job record.
- **Retried workers** **must** resolve the **same** bundle pin; mismatch ⇒ **C4-class** failure (engine/nondeterminism path) until corrected.

---

## Rebuild supersession behavior

When migrating **A → B**:

1. Outputs remain attributed to **A** until regeneration/remap job explicitly produces **B** generations with supersession pointers (`phase-03-replay-versioning-doctrine.md`).
2. Pins **do not auto-update**—operators or automated policy jobs migrate pins **explicitly**.

---

## Historical replay guarantees

Re-running rebuild/regeneration with **same** `(raw snapshot scope, bundle pin, engine build)` **must** reproduce canonical logical keys and ordering within declared divergence classes (**C0–C2** acceptable per gate policy).

---

## Multi-generation coexistence

Multiple generations **may** coexist during migration:

- Each generation **must** carry distinct **`generation_counter`** + **`mapping_bundle_id`** on receipts,
- Queries **must** default to **latest non-tombstoned** generation **only** under explicit API/query contract—not implicit mutation.

---

## Anti-goals: forbidden “latest bundle” behavior

| Pattern | Verdict |
| ------- | ------- |
| Default connector mapping = registry head | **Forbidden** unless replaced by explicit **policy artifact** equivalent to a pin (versioned, auditable) |
| Implicit upgrade on worker restart | **Forbidden** |
| Silent selection based on deploy region | **Forbidden** |

---

## References

- Registry governance: `phase-03-mapping-bundle-registry.md`
- Replay / C-classes: `phase-03-replay-versioning-doctrine.md`
- CI enforcement: `phase-03-ci-deterministic-enforcement-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
