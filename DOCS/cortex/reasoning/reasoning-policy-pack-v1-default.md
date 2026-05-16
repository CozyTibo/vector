# ReasoningPolicyPackV1_Default — canonical constitutional fixture

**Status:** normative **frozen default** — first policy artifact for Phase **06** (TCRE).  
**Role:** Single **constitutional** baseline for reducers, replay harnesses, legality checks, admin readouts, and **`G‑P06‑POL‑01`** / **`G‑P06‑CHRON‑01`** until a tenant‑specific pack is explicitly selected.

**Not in scope:** runtime loaders, env overrides, feature flags, hot reload, or deployment wiring (implementation chooses how to load bytes).

---

## 1. Artifact location and identity

| Item | Value |
|------|-------|
| **Fixture file** | [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json) |
| **`tcre_policy_pack_id`** | `ReasoningPolicyPackV1_Default` |
| **`tcre_policy_pack_version`** | `2` (integer in JSON) |
| **`TCRE_POLICY_PACK_DEFAULT_ID`** | Same string as `tcre_policy_pack_id` (implementation constant name **TBD**). |

---

## 2. Canonical serialization and digest

**Digest law (frozen):**  
Let **`canonical_body`** be the UTF‑8 encoding of **`json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`** where **`obj`** is the parsed JSON object **without** any field named **`tcre_policy_bundle_digest`** (the fixture file omits that field).

**`TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST`** (hex):

```
d48f77eb363cc2828b7af5351365d3e96dc5e1b4464c5fa1b6a5d6c56590f470
```

**Amendment law:** Any change to the fixture **MUST** bump **`tcre_policy_pack_version`**, recompute digest, update this section, append [`PHASE06_CONSTITUTIONAL_CHANGELOG.md`](./PHASE06_CONSTITUTIONAL_CHANGELOG.md), and pass tracker review.

---

## 3. Contents (normative summary)

The fixture implements [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) §1:

| Section | Purpose |
|---------|-----------|
| **`caps`** | `max_causal_hops_default`, `max_causal_hops_degraded`, `max_transitive_closure_hops`, `max_breakpoints_per_chain`, `max_tcre_edges_per_chain` |
| **`transitive_rule_id_default`** | Sentinel when no transitive closure (`tcre_transitive_none_v1`) |
| **`breakpoint_rule_priority`** | Integer priorities (lower fires first per [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md)) |
| **`chronology_skew_projection_v1`** | **24 rows**: all `(replay_safe_ordering ∈ {strict,partial,unresolved}) × (skew_detected, late_arrival, export_sequence_conflict) ∈ {0,1}³` — each row sets **`chronology_legality_class`** so **§3 forbidden tuples** in [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) **never** occur without the row’s documented exception (default uses **no** `(strict, chronology_unresolved)` rows). |
| **`merge_rules_coordination_edges`** | `[]` — one‑to‑one coordination edge injection |
| **`replay_caps`** | Upper bound placeholder for walk hops per reasoning job |
| **`cross_system_causal_min_rank`** | `4` — aligns [`cross-system-causal-continuity.md`](./cross-system-causal-continuity.md) |
| **`silence_causality`** | Minimal thresholds / flags for [`silence-causality-law.md`](./silence-causality-law.md) |
| **`ambiguity_survivability`** | `allow_ambiguity_none_explicit: true` — [`bounded-ambiguity-law.md`](./bounded-ambiguity-law.md) |
| **`degradation_thresholds`** | Boolean gate for **`CD‑CHRON`** emission policy (deterministic flag for reducers) |

---

## 4. Verifier obligations

- **`G‑P06‑POL‑01`:** Parse fixture → canonical re‑serialize → **`sha256` MUST equal** **`TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST`** when pack id is default and version is `2`.  
- **`G‑P06‑CHRON‑01`:** For each legal snapshot key, **`ChronologyLegalityProjectionV1`** lookup **MUST** return the **`chronology_legality_class`** in the matching row (see state machine §2.1).

---

## 5. Runtime / reducer obligations (constitutional only)

- First implementation **SHOULD** pin this pack for CI and golden vectors unless a case explicitly imports an alternate pack **with waiver** per [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) §4.  
- **`tcre_policy_bundle_digest`** on all derived ids **MUST** match the active pack digest.

---

## 6. Related

[`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) · [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) · [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md)
