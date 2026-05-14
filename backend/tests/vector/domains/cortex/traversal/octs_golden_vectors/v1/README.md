# OCTS golden vectors (`v1`)

**Canonical root** for all **`G-P05-***` fixtures per `DOCS/cortex/05-traversal/phase-05-ci-enforcement-architecture.md` §7.

| Subdirectory | Purpose |
| ------------ | ------- |
| `canonicalization/` | `OCTS-CANON-1` JCS + NFC vectors |
| `temporal/` | **G-P05-TEMP-01** / **G-P05-TEMP-02** — sequence monotonicity, half-open, supersession, anchor canonical bytes (**P05-07**) |
| `walk_policy/` | **G-P05-POL-01** / **G-P05-POL-02** — policy bundle + golden ``policy_hash`` (**P05-08**) |
| `walks/` | **G-P05-HASH-01** / **G-P05-HASH-02** — canonical `hash_body` + expected `walk_result_hash`; telemetry separation variants (**P05-09**) |
| `exploration/` | **G-P05-EXP-01** / **G-P05-EXP-02** — walk request explicit ``exploration_mode``; exploration ``hash_body`` markers + authoritative table law (**P05-11**) |
| `hop_receipts/` | **G-P05-HR-01** / **G-P05-HR-02** — observed envelope + fingerprint law; dangling org link bundle (**P05-10**) |
| `multigraph/` | **G-P05-MG-01** neighbor-order bytes + parallel-edge inner projection (**P05-06**) |
| `derived_index/` | **G-P05-IDX-01** / **G-P05-IDX-02** — ``index_content_hash`` golden + lineage vectors (**P05-13**) |
| `index_build_job/` | **G-P05-JOB-01** / **G-P05-JOB-02** — FSM audit trails (good committed vs bad skip validating) (**P05-14**) |
| `walk_execution_strategy/` | **G-P05-EQUIV-01** / **G-P05-WES-01** / **G-P05-WES-02** — fast-path equivalence + strategy policy hash (**P05-15**) |
| `runtime_execution/` | **G-P05-RT-01** / **G-P05-RT-02** — reference-walk determinism (100×) + frontier-cap star (**P05-16**) |
| `diagnostics/` | **G-P05-DIAG-02** — cycle multiset fingerprint golden bytes (**P05-12**) |

**Immutability:** `v1/` is **append-only** until tag `octs-vectors-v1`; corrections use `v2/`.
