# Ambiguity registry v1 (`TCRE_AMBIGUITY_REGISTRY_VERSION`)

**Status:** constitutional **freeze** — replaces placeholder ambiguity strings in Phase **06** docs.  
**Owner:** `DOCS/cortex/reasoning/ambiguity-registry-v1.md` — amendments **MUST** bump **`TCRE_AMBIGUITY_REGISTRY_VERSION`** and update [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md).

---

## 1. Closed enum — `ambiguity_class_id`

| Id | Meaning | Default propagation (see [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md) §5) |
|----|---------|----------------------------------------------------------------------------------------------------------------------------------|
| **`AMB‑NONE`** | Explicit no ambiguity. | Local only. |
| **`AMB‑OWN‑parallel`** | Parallel ownership / assignee conflict evidence. | Continuity + may block ownership causal edges. |
| **`AMB‑CHRON‑partial`** | Pairwise order undefined under policy. | Chronology‑blocking for strict assertions. |
| **`AMB‑CHRON‑conflict`** | Competing anchors / export vs observed. | Chronology + replay risk; often **`CD‑CHRON`**. |
| **`AMB‑PART‑storyline`** | Partitioned non‑mergeable storylines. | Causal‑blocking across partitions without supersession. |
| **`AMB‑BRIDGE‑weak`** | Continuity bridge below cross‑system causal floor. | Continuity + causal for cross‑system claims. |
| **`AMB‑ACK‑conflicted`** | Contradicted ack/deny patterns. | Replay legality / conflict receipts. |
| **`AMB‑ANCH‑missing`** | Required temporal anchor absent. | Chronology + often **`replay_unverifiable`**. |

**Forbidden:** Any corpus value, API string, or DB field using **free‑text** ambiguity labels outside this table + §3 aliases.

---

## 2. Versioning and extension

1. **Patch:** clarify prose only — **no** `TCRE_AMBIGUITY_REGISTRY_VERSION` bump if enum ids unchanged.  
2. **Minor:** add new **`AMB‑*`** id — bump version; golden corpus schema **MUST** accept new id.  
3. **Major:** retire or remap an id — requires migration note in [`PHASE06_CONSTITUTIONAL_CHANGELOG.md`](./PHASE06_CONSTITUTIONAL_CHANGELOG.md) + corpus version bump.

---

## 3. Corpus alias table (normative)

Golden thread and legacy fixtures **MAY** use the left column; validators **MUST** normalize to the right **`AMB‑*`** id:

| Legacy / example string | Canonical `ambiguity_class_id` |
|-------------------------|-------------------------------|
| `ownership_parallel_assignees` | `AMB‑OWN‑parallel` |
| `chronology_partial_order` | `AMB‑CHRON‑partial` |
| `parallel_cause` | `AMB‑PART‑storyline` |
| `partitioned_storyline` | `AMB‑PART‑storyline` |
| `weak_cross_system_bridge` | `AMB‑BRIDGE‑weak` |
| `conflicted_ack` | `AMB‑ACK‑conflicted` |
| `missing_anchor` | `AMB‑ANCH‑missing` |
| `unresolved_chronology` | `AMB‑CHRON‑conflict` |

**G‑P06‑AMB‑01:** Corpus loader **MUST** reject unknown strings after alias normalization.

---

## 4. Survivability

**AMB‑S1 (unchanged law):** [`bounded-ambiguity-law.md`](./bounded-ambiguity-law.md) — downstream **MUST NOT** coerce to false certainty.

---

## 5. Ambiguity receipt

`reasoning_ambiguity_receipt` lists **sorted** `ambiguity_class_id` + optional partition ids + blocked derivation rule ids hash — per [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md).

---

## 6. Admin

[`reasoning-admin-control-plane-spec.md`](./reasoning-admin-control-plane-spec.md) **Ambiguity propagation inspector** displays **canonical `AMB‑*`** ids; legacy aliases shown read‑only for audit.
