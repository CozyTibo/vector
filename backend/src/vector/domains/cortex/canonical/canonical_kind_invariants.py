"""Authoritative canonical kind invariants (identity/temporal/provenance/structure/ambiguity/anti-goals).

This is governance data for Phase 03 hardening. It is intentionally explicit and non-semantic.
"""

from __future__ import annotations

from typing import Any, Final

CANONICAL_KIND_INVARIANTS_SCHEMA_VERSION: Final[int] = 1

_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind_id": "document",
        "lifecycle_state": "active",
        "identity_invariants": [
            "logical key uses provider-stable document id only; no title/url-based identity.",
            "connector + bundle are mandatory key dimensions.",
            "identity must not change across replay for same raw row revision.",
        ],
        "temporal_invariants": [
            "later revisions supersede by temporal ordering key; no reordering by semantic fields.",
            "late arrivals are accepted but must preserve deterministic ordering key construction.",
        ],
        "provenance_invariants": [
            "minimum: one provenance row per materialization with primary_raw_record_ids.",
            "field lineage required for logical_key and copied raw columns.",
        ],
        "structural_invariants": [
            "parent_ref, when present, must be explicit provider parent evidence.",
            "containment is evidenced; inferred workspace hierarchies are forbidden.",
        ],
        "ambiguity_invariants": [
            "missing stable provider identity must fail deterministically (no guess fallback).",
        ],
        "anti_goals": [
            "not a semantic summary artifact",
            "not cross-provider merged knowledge object",
        ],
    },
    {
        "kind_id": "database_row",
        "lifecycle_state": "active",
        "identity_invariants": [
            "logical key = tenant + bundle + connector + database_provider_id + row_provider_id.",
            "database containment is part of identity; row id alone is insufficient.",
        ],
        "temporal_invariants": [
            "revision continuity follows source_revision_key + replay_sequence ordering key.",
            "late row updates must remain replay-reconstructable under same logical key.",
        ],
        "provenance_invariants": [
            "relation_refs/title/schema-derived attributes must cite source property paths.",
            "raw reference must remain reversible to original row payload.",
        ],
        "structural_invariants": [
            "row must be contained in explicit database_id.",
            "relation refs are structural pointers, not inferred edges.",
        ],
        "ambiguity_invariants": [
            "missing database containment is deterministic error; do not auto-attach to guessed container.",
        ],
        "anti_goals": [
            "not a free-text document",
            "not semantic rollup of relational table meaning",
        ],
    },
    {
        "kind_id": "message",
        "lifecycle_state": "active",
        "identity_invariants": [
            "logical key requires conversation_provider_id + message_provider_id.",
            "message identity must not depend on mutable text content.",
        ],
        "temporal_invariants": [
            "ordering uses occurred_at/replay_sequence/source_revision/raw_record tie-break.",
            "thread/reply ordering is deterministic and replay-stable.",
        ],
        "provenance_invariants": ["author/channel/message-id evidence must remain traceable."],
        "structural_invariants": ["message contained in conversation/thread when evidenced."],
        "ambiguity_invariants": ["missing conversation identity is deterministic failure."],
        "anti_goals": ["not sentiment/topic/importance inference surface"],
    },
    {
        "kind_id": "thread",
        "lifecycle_state": "planned",
        "identity_invariants": ["thread identity must be provider thread key, not reconstructed by text similarity."],
        "temporal_invariants": ["reply sequence ordering must be deterministic and stable."],
        "provenance_invariants": ["thread root linkage must cite raw evidence fields."],
        "structural_invariants": ["thread belongs to exactly one conversation scope."],
        "ambiguity_invariants": ["competing thread roots create explicit ambiguity records."],
        "anti_goals": ["not conversation clustering by semantic content"],
    },
    {
        "kind_id": "comment",
        "lifecycle_state": "planned",
        "identity_invariants": ["comment provider id must be stable and replay-safe."],
        "temporal_invariants": ["comment ordering is provider timestamp/id derived only."],
        "provenance_invariants": ["comment parent linkage required in provenance."],
        "structural_invariants": ["comment references explicit parent artifact id."],
        "ambiguity_invariants": ["unknown parent target triggers ambiguity/open failure."],
        "anti_goals": ["not synthetic discussion summarization"],
    },
    {
        "kind_id": "issue",
        "lifecycle_state": "active",
        "identity_invariants": ["issue_provider_id is required and immutable under replay."],
        "temporal_invariants": ["state revisions rely on deterministic raw revision keys."],
        "provenance_invariants": ["title/status fields must keep rule/source paths."],
        "structural_invariants": ["issue containment in repo/project must be evidenced."],
        "ambiguity_invariants": ["conflicting issue identifiers must not be merged silently."],
        "anti_goals": ["not prioritization/urgency semantics"],
    },
    {
        "kind_id": "pull_request",
        "lifecycle_state": "active",
        "identity_invariants": ["repository_provider_id + pull_request_discriminant identify PR."],
        "temporal_invariants": ["replay must reproduce same key/hash under unchanged payload."],
        "provenance_invariants": ["base.repo + number lineage is mandatory."],
        "structural_invariants": ["PR contained in one repository scope."],
        "ambiguity_invariants": ["missing repository identity is hard error."],
        "anti_goals": ["not reviewer intent interpretation"],
    },
    {"kind_id": "project", "lifecycle_state": "planned", "identity_invariants": ["project_provider_id stable."], "temporal_invariants": ["state transitions deterministic."], "provenance_invariants": ["project fields traced to raw rows."], "structural_invariants": ["project containment explicit."], "ambiguity_invariants": ["competing project ids explicit."], "anti_goals": ["not initiative semantic decomposition"]},
    {"kind_id": "cycle", "lifecycle_state": "planned", "identity_invariants": ["cycle_provider_id stable."], "temporal_invariants": ["window boundaries deterministic."], "provenance_invariants": ["cycle dates traced to raw."], "structural_invariants": ["cycle containment explicit."], "ambiguity_invariants": ["overlapping uncertain cycles explicit."], "anti_goals": ["not predictive schedule modeling"]},
    {"kind_id": "deployment", "lifecycle_state": "planned", "identity_invariants": ["deployment provider id stable."], "temporal_invariants": ["status chronology deterministic."], "provenance_invariants": ["deployment status lineage preserved."], "structural_invariants": ["deployment belongs to repository/environment scope."], "ambiguity_invariants": ["missing scope => explicit failure/ambiguity."], "anti_goals": ["not rollout risk inference"]},
    {"kind_id": "workflow_run", "lifecycle_state": "planned", "identity_invariants": ["workflow run id stable."], "temporal_invariants": ["run state transitions deterministic."], "provenance_invariants": ["run metadata traced to raw endpoints."], "structural_invariants": ["run tied to repository/workflow ids."], "ambiguity_invariants": ["unknown workflow mapping explicit."], "anti_goals": ["not pipeline health scoring"]},
    {
        "kind_id": "execution_check",
        "lifecycle_state": "active",
        "identity_invariants": [
            "logical key = tenant + bundle + connector + repository_provider_id + check_run_provider_id.",
            "identity must remain stable across workflow rename and pagination shifts.",
        ],
        "temporal_invariants": [
            "status lifecycle ordering is deterministic: queued -> in_progress -> completed.",
            "completed_at must be >= started_at when both are present.",
        ],
        "provenance_invariants": [
            "status, conclusion, lifecycle timestamps, commit linkage, and workflow linkage remain source-traceable.",
        ],
        "structural_invariants": [
            "execution check is contained by one repository scope.",
            "commit/workflow references are explicit fields, never inferred.",
        ],
        "ambiguity_invariants": [
            "duplicate active check identities and illegal status transitions are verification failures.",
        ],
        "anti_goals": [
            "not CI reliability scoring",
            "not semantic root-cause inference",
        ],
    },
    {"kind_id": "transcript", "lifecycle_state": "planned", "identity_invariants": ["transcript id stable per meeting/provider."], "temporal_invariants": ["segment ordering deterministic."], "provenance_invariants": ["segment text traces to raw transcript payload."], "structural_invariants": ["transcript contained by meeting."], "ambiguity_invariants": ["missing meeting linkage explicit."], "anti_goals": ["not semantic summary object"]},
    {"kind_id": "transcript_segment", "lifecycle_state": "planned", "identity_invariants": ["meeting_provider_id + segment_ordinal stable."], "temporal_invariants": ["ordinal ordering strict deterministic tie-break."], "provenance_invariants": ["speaker/text offsets traced to raw."], "structural_invariants": ["segment belongs to one transcript/meeting."], "ambiguity_invariants": ["ordinal conflicts create ambiguity/failure records."], "anti_goals": ["not topic extraction artifact"]},
    {
        "kind_id": "person_actor_boundary",
        "lifecycle_state": "active",
        "identity_invariants": ["PERSON keys use provider actor ids only; no cross-provider merge in Phase 03."],
        "temporal_invariants": ["identity anchor continuity must be deterministic."],
        "provenance_invariants": ["actor identity fields must retain direct source paths."],
        "structural_invariants": ["actor relationships only when evidenced by source records."],
        "ambiguity_invariants": ["cross-provider identity collision => explicit ambiguity, no auto-merge."],
        "anti_goals": ["not global human identity resolution"],
    },
    {
        "kind_id": "container_semantics",
        "lifecycle_state": "active",
        "identity_invariants": ["container ids derive from provider container identifiers."],
        "temporal_invariants": ["membership/containment transitions must be replay-reconstructable."],
        "provenance_invariants": ["container linkage must preserve source endpoint evidence."],
        "structural_invariants": ["containment edges are directional and explicit."],
        "ambiguity_invariants": ["multiple competing containers => explicit ambiguity."],
        "anti_goals": ["not inferred hierarchy from language cues"],
    },
    {
        "kind_id": "relation_semantics",
        "lifecycle_state": "active",
        "identity_invariants": ["relation identity keyed by structural edge kind + endpoints."],
        "temporal_invariants": ["relation mutation ordering deterministic; no inferred temporal repair."],
        "provenance_invariants": ["every relation must reference raw evidence paths."],
        "structural_invariants": ["containment relations distinct from references; never conflated."],
        "ambiguity_invariants": ["conflicting endpoint evidence must not collapse silently."],
        "anti_goals": ["not semantic relationship inference from text"],
    },
)


def build_canonical_kind_invariants_document() -> dict[str, Any]:
    return {
        "canonical_kind_invariants_schema_version": CANONICAL_KIND_INVARIANTS_SCHEMA_VERSION,
        "kinds": list(_KINDS),
    }

