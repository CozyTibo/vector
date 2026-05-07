# Cortex Control Plane Overview

## Purpose
Cortex Control Plane is the operational interface for running, inspecting, validating, and governing cognition infrastructure phases. It is not a generic admin dashboard.

## Control Plane Capabilities
- phase-state visibility,
- replay/reprocessing orchestration,
- provenance and lineage inspection,
- ambiguity and confidence inspection,
- failure explanation and recovery guidance,
- auditability and dangerous action governance,
- global ingestion scheduling control,
- workspace-scoped connector ingestion trigger actions.

## Ingestion Control Surface (Admin UX)
- Root-level control:
  - `Scheduled Polling: ON/OFF` CTA controls scheduler dispatch globally.
  - `OFF` pauses scheduled polling job creation without deleting connector state or checkpoints.
  - `ON` resumes scheduled polling from existing cursor/checkpoint state.
- Workspace-level control:
  - `Trigger Connector Ingestion` action allows manual run per selected connector.
  - Action is scoped to workspace + connector + sync mode.
  - Action must show blast radius, expected queue lane, and safe rollback guidance before execution.

## Non-Goals
- no executive business analytics,
- no opaque AI-only operation,
- no uncontrolled direct data mutation.

## Operator Outcomes
Operators can answer:
- what each phase is doing now,
- why a phase failed or degraded,
- what action is safe to take next,
- what blast radius an action has,
- whether cognition outputs remain trustworthy.
