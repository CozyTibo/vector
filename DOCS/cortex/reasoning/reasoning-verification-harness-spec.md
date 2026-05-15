# Reasoning verification harness spec (Phase 06)

**Status:** normative CI / harness spec (pre‑code).

## Gate catalog (shell)

Target family **`G‑P06‑*`** including at minimum:

| Gate id | Intent |
|---------|--------|
| **G‑P06‑ANTI‑01** | Static ban scan for forbidden imports / strings in reasoning package. |
| **G‑P06‑PROV‑01** | Every emitted artifact schema includes provenance fields. |
| **G‑P06‑CHRON‑01** | Chronology legality class consistent with anchors. |
| **G‑P06‑CAUS‑01** | Causal edge enum closure + acyclicity default. |
| **G‑P06‑REPLAY‑01** | Double‑run equivalence on golden corpus slice. |
| **G‑P06‑AMB‑01** | Ambiguity never silently cleared. |
| **G‑P06‑CLOSE‑01** | Certification pack structural contract (mirror **G‑P05‑CLOSE‑01** shape). |

## Harness artifacts

Golden vectors under future `tests/.../reasoning_golden_vectors/v1/` — paths TBD at implementation; corpus alignment with `golden-thread-replay-corpus-spec.md`.

## Staging

Mirror **STAGE‑A…Z** pattern from Phase **05** CI enforcement architecture — detailed in implementation phase; this doc freezes **intent** and **severity** defaults (`hard_fail` vs `warn_only`).
