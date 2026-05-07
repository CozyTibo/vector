# Admin Permissions Model

## RBAC Levels
- `viewer`: read-only phase and health visibility.
- `operator`: can run safe scoped actions (pause/resume, targeted replay preview/run).
- `senior_operator`: can run wider reprocessing/replay scopes.
- `admin`: can approve dangerous actions and policy overrides.
- `platform_admin`: cross-workspace governance and emergency controls.

## Permission Boundaries
- tenant scope enforced for non-platform roles.
- dangerous actions require elevated role + approval chain.
- no role may bypass audit logging.

## Least Privilege Rule
Grant only minimum role needed for action class and scope.
