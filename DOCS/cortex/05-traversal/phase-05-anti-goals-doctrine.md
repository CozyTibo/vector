# Phase 05 — Anti-goals doctrine (OCTS)

**Normative step:** **3** (tracker). **Freeze bundle:** **FF-1**.  
**Depends on:** `phase-05-normative-index.md`, `phase-05-observed-vs-derived-doctrine.md`.

---

## 1. Constitutional intent

This doctrine exists to **guarantee** that OCTS remains a **substrate**: deterministic bounded walks, structural artifacts, replay, provenance, and operator visibility — **without** becoming a cognition layer. Any feature request that implies judgment, ranking, narrative, or semantic importance **MUST** be rejected from Phase 05 scope.

---

## 2. Explicit anti-goals

Phase 05 **MUST NOT**:

- Perform retrieval, ranking, recommendation, or “most relevant” edge selection beyond **deterministic policy tie-breaks** in `phase-05-walk-policy-doctrine.md`.
- Emit **insights**, **root causes**, **narratives**, **summaries**, or **conclusions**.
- Assign **semantic scores**, **importance**, **confidence narratives**, or **LLM-derived** fields in **walk_result** or **hop_receipt** canonical bodies.
- Infer **causality** or **temporal reasoning** beyond **validity interval arithmetic** and **anchor pinning** (Phase 06 owns causality).
- Collapse **traversal** into **reasoning** outputs (see step 5 doctrine).
- Use **derived** structures as **default authority** (step 2).
- Expose Phase 03 topology / canonical transform payloads as traversable truth (step 4).

---

## 3. Formal terminology

| Term | Meaning |
| ---- | ------- |
| **Substrate output** | JSON-serializable artifact in the **allowed algebra** of step 5. |
| **Cognition leakage** | Any field or behavior that requires interpretation beyond structural validity checks. |
| **Deterministic policy** | Tie-break fully specified by inputs + `policy_hash` — no learned weights. |

---

## 4. Deterministic semantics

**RULE AG-01:** If an implementation choice affects walk outputs and is not pinned by normative text, that choice is **ILLEGAL**. Open gaps **MUST** be listed in `phase-05-spec-gap-matrix.md` until resolved.

**RULE AG-02:** Randomized or ML-driven neighbor ordering is **FORBIDDEN**.

---

## 5. Replay semantics

**REPLAY REQUIREMENT AG-01:** Replay jobs **MUST** reject payloads containing forbidden cognition fields (see §12). **G-P05-ANTI-01** (verification gates doctrine) scans canonical JSON for forbidden key substrings/patterns.

---

## 6. Temporal semantics

Temporal validity operations **MUST** remain **interval algebra** and **anchor pinning** only — no “causal windows,” “likely ordering,” or heuristic time expansion.

---

## 7. Provenance semantics

Provenance fields **MUST** cite **org links / primitives / projection rows** — never “because model said so.” **Evidence refs** are structural pointers only.

---

## 8. Serialization contracts

Anti-goal enforcement is **hash-stable**: forbidden content **MUST NOT** appear in canonical bodies; telemetry may carry **non-canonical** debug strings **only** when **TELEMETRY-EXCLUDED** from all OCTS hashes per normative index.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-AG-01** | `walk_result` contains keys matching forbidden patterns (`insight`, `recommendation`, `root_cause`, `summary`, `narrative`, `relevance_score`, … full list in verification doctrine). |
| **FS-AG-02** | Exploration mode results written to authoritative stores. |
| **FS-AG-03** | Derived index served without `index_epoch` / **stale** banner when contract requires visibility. |

---

## 10. Verification implications

- **G-P05-ANTI-01:** Static scan of walk/receipt schemas for forbidden keys and string patterns.  
- **G-P05-ANTI-02:** Export surface audit — no Phase 03 forbidden tokens in traversal ingress (extends P04-10 class).

---

## 11. Abuse scenarios

| Abuser | Attack | Containment |
| ------ | ------ | ----------- |
| Phase 07 retrieval | Smuggle ranking into “policy” | Policy hash pins explicit tie rules; static gate rejects weighted scores. |
| Phase 08 synthesis | Read walk as “explanation” | Traversal vs reasoning doctrine bans narrative fields. |
| Operator UI | Display walk as insight | Control plane may show **tables of structural diagnostics** only. |

---

## 12. Negative examples

**ILLEGAL** `walk_result` fragment:

```json
{
  "insight": "Team blocked by dependency",
  "recommendations": ["hire more ICs"]
}
```

**LEGAL** diagnostic (in allowed taxonomy):

```json
{ "diagnostics": { "termination_reason": "budget_exhausted", "edges_visited": 42 } }
```

---

## 13. CI oracle expectations

- Schema tests + **forbidden key** regression suite.  
- Golden walk fixtures proving **reject** paths for illegal payloads.  
- Cross-phase import gate ensuring **topology** never enters hashed walk body.

**Reference implementation (P05-03):** `vector.domains.cortex.traversal.anti_goals` — `validate_octs_canonical_json_mapping_no_cognition_leakage`, `list_forbidden_cognition_key_violations`, `verify_gp05_anti01_forbidden_cognition_keys_static`, `verify_gp05_anti02_traversal_ingress_no_phase03_tokens_static` (reuses P04 export token scan for **G-P05-ANTI-02**).
