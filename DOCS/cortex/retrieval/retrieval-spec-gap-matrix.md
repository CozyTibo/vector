# Phase 07 — Spec gap matrix

**Status:** living document (architecture pass **2026-05-16**).

---

## Active P0

| ID | Gap | Owner step | Resolution |
| -- | --- | ---------- | ---------- |
| — | *none* | — | Architecture pass closed initial P0 |

---

## Active P1

| ID | Gap | Owner step | Target |
| -- | --- | ---------- | ------ |
| P1-P07-01 | JSON Schemas not yet generated on disk | 6 | Implementation wave 1 |
| P1-P07-02 | `RetrievalPolicyPackV1_Default.json` fixture | 13 | Copy from doctrine caps |
| P1-P07-03 | Golden vector corpus empty | 28 | Wave 1.3 |
| P1-P07-04 | `cortex_retrieval_query_audit` migration spec only | 22 | Wave 4 |
| P1-P07-05 | Phase 08 ingress contract cross-doc | 3 | Before FF-P07-5 |

---

## Resolved (architecture pass)

| ID | Resolution |
| -- | ---------- |
| P0-P07-ARCH-01 | Phase 07 decomposed to 30 steps in MASTER_TRACKER |
| P0-P07-ARCH-02 | Anti-goals + boundaries explicit vs 06/08/09 |
| P0-P07-ARCH-03 | Retrieval stage completeness + overview integration defined |
| P0-P07-ARCH-04 | Deterministic ranking law (anti-semantic) |
| P0-P07-ARCH-05 | Operator control plane 16 surfaces |

---

## Promotion to Frozen (doctrine)

Steps **1–30** promote to **`Frozen (doctrine)`** when:

1. No Active P0  
2. All doctrine files cross-linked from normative index  
3. Hostile review sign-off on replay + provenance docs  

Target: **FF-P07-5** (Step 30).
