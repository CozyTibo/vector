# Phase Debugging Model

## Debugging Objective
Explain causality of operational behavior from source event to phase output.

## Debug Entry Points
- by phase object id,
- by replay job id,
- by failure incident id,
- by provenance chain id.

## Required Debugging Views
- transformation lineage trace,
- last successful checkpoint/run context,
- failed stage and failure class,
- ambiguity and confidence evidence breakdown,
- replay divergence diff summary.

## Expected Debug Workflow
1. Identify failing/degraded phase object.
2. Trace lineage backward to raw input.
3. Identify first failing transformation step.
4. Inspect confidence/ambiguity and version context.
5. Choose safe operator action with blast radius preview.
