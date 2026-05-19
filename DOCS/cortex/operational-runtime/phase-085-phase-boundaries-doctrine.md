# Phase 08.5 — Phase boundaries

**Status:** normative.

---

## Acyclic dependency

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 08.5 → 09 → 10
```

**08.5** MAY import and extend runtime in Phases **02–08** packages.  
**08.5** MUST NOT import Phase **09** product code.

---

## Boundary laws

| Law | Rule |
| --- | ---- |
| **CESP-BND-08-01** | CESP MUST NOT alter `SynthesisIntelligenceArtifactV1` schema without Phase 08 amendment |
| **CESP-BND-08-02** | CESP MAY add orchestration tables, reports, maturity enums |
| **CESP-BND-09-01** | Phase 09 MUST NOT ship until **G-P085-CLOSE-01** pass |
| **CESP-BND-10-01** | Cockpit routes register via Phase 10 admin shell |

---

## What 08.5 owns

- Substrate pipeline continuation + recovery
- Density schedulers (graph, traversal, TCRE, retrieval, synthesis activation)
- Operational maturity + health models
- Materialization / activation audit tables
- Admin operational cockpit (spec + routes)

## What 08.5 does not own

- New synthesis workloads (Phase 08 policy pack)
- Retrieval query algebra changes (Phase 07)
- TCRE causal legality rules (Phase 06)
