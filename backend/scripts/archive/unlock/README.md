# Archived unlock scripts (operator recovery only)

These scripts were used during Cortex unlock / war-room recovery. They are **not** part of autonomous runtime continuity.

- Do not run during 48h AA continuity hold (guarded by `assert_wedge_script_allowed_v1`).
- Canonical ops entrypoint: `backend/scripts/continuity_audit_snapshot.py`.

Moved here as part of runtime continuity stabilization (R6).
