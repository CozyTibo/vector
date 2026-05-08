# Phase 02 Storage and Retention Doctrine

## Append-Only Meaning (Operational)
Append-only means:
- no in-place semantic rewrites of raw evidence rows,
- new observations/revisions append new rows,
- trust/state metadata may evolve, but preserved evidence content for a row is immutable.

## Retention Boundary
Retention must preserve declared replay/reconstruction obligations.
Any retention policy that violates obligations must fail closure gates.

## Required Policy Dimensions
- operational replay horizon,
- long-horizon audit/reconstruction horizon,
- legal/compliance deletion obligations,
- hot vs cold tier retention boundaries.

## Archival Boundary
- cold archival is allowed if evidence remains reconstructable through rehydration + integrity checks,
- archival transitions must preserve lineage queryability.

## Deletion Policy
- tenant/policy deletion must be explicit, auditable, and trust-state-impacting,
- no silent deletion that preserves healthy trust-state labels.

## Compliance Constraint
Allowed metadata retention post-content deletion must remain non-content-bearing and policy-approved.
