# OCTS golden vectors (`v1`)

**Canonical root** for all **`G-P05-***` fixtures per `DOCS/cortex/05-traversal/phase-05-ci-enforcement-architecture.md` §7.

| Subdirectory | Purpose |
| ------------ | ------- |
| `canonicalization/` | `OCTS-CANON-1` JCS + NFC vectors |
| `temporal/` | `export_sequence` + anchor monotonicity |
| `walks/` | Full walk request / `walk_result_hash` pairs |

**Immutability:** `v1/` is **append-only** until tag `octs-vectors-v1`; corrections use `v2/`.
