# Archived unlock scripts (operator recovery only)

These scripts were used during Cortex unlock / war-room recovery. They are **not** part of autonomous runtime continuity or semantic intelligence sign-off.

## When to use

- **Recovery only** after an explicit incident or engineering-directed rollback — not for daily health checks.
- Never during the 48h AA continuity hold (`assert_wedge_script_allowed_v1`).

## Canonical operator entrypoints (Wave S5+)

From repo root with prod DB credentials in `.env`:

```bash
cd backend
python scripts/continuity_audit_snapshot.py --tenant-id <tenant> --json
python scripts/graph_truth_audit_snapshot.py --tenant <tenant> --json
```

## Do not use for routine ops

- `backend/scripts/prod_substrate_proof_queries.py` — deprecated; exits **2** unless `--allow-deprecated`
- `backend/scripts/archive/unlock/*` — this directory only
- `continuity_p0_phase_*_proof.py` — CI gates; see [`DOCS/audits/cortex_continuity_p0_ci_matrix.md`](../../../../DOCS/audits/cortex_continuity_p0_ci_matrix.md)

Moved here as part of runtime continuity stabilization (R6) and semantic cleanup (Wave S5).
