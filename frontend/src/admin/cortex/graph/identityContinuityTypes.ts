import type {
  SemanticIdentityContinuity,
} from "../pipelineTypes";

export type IdentityContinuitySearchMatch = {
  search_key: string;
  value: string;
  entity_id?: string;
  projection_kind?: string;
  found: boolean;
  error?: string;
  anchor_hits?: number;
  entity_ids?: string[];
};

export type IdentityContinuitySearchResult = {
  surface_kind: "identity_continuity_search";
  tenant_id: string;
  matches: IdentityContinuitySearchMatch[];
  entity_ids: string[];
  entities: Array<Record<string, unknown>>;
};

export type IdentityContinuityCandidate = {
  candidate_id: string;
  link_type: string;
  source_entity_id: string;
  target_entity_id: string;
  rule_id: string | null;
  batch_id: string;
  created_at: string | null;
  evidence_raw_record_ids: number[];
  skip_reason_code: string;
  status: "promotable" | "skipped";
};

export type IdentityContinuityEntityInspector = {
  surface_kind: "identity_continuity_entity_inspector";
  inspector_schema_version?: number;
  tenant_id: string;
  entity: Record<string, unknown>;
  continuity_status: Record<string, unknown>;
  resolved_identities: Array<Record<string, unknown>>;
  linked_handles: Array<Record<string, unknown>>;
  authoritative_links: Array<Record<string, unknown>>;
  candidate_explorer_rows?: Array<Record<string, unknown>>;
  candidates: IdentityContinuityCandidate[];
  promotable_candidates: IdentityContinuityCandidate[];
  skipped_candidates: IdentityContinuityCandidate[];
  unresolved_candidates: Array<Record<string, unknown>>;
  promotion_lineage: Array<Record<string, unknown>>;
  candidate_lineage: Record<string, unknown>;
  continuity_evidence?: Record<string, unknown>;
  evidence_receipts: Array<Record<string, unknown>>;
  generation_rejections: Array<Record<string, unknown>>;
  generation_rejection_counts: Record<string, number>;
  open_ambiguities: Array<Record<string, unknown>>;
  conflicting_identities: Array<Record<string, unknown>>;
  duplicate_identities: Array<Record<string, unknown>>;
  evidence_summary: Record<string, unknown>;
};

export type IdentitySearchParams = {
  slack_user_id?: string;
  github_login?: string;
  notion_user_id?: string;
  email?: string;
  entity_id?: string;
  handle_id?: string;
  canonical_entity_id?: string;
};

export type IdentityContinuityInspectorTenant = {
  surface_kind: "identity_continuity_inspector";
  inspector_schema_version?: number;
  identity_continuity?: SemanticIdentityContinuity;
  unpromoted_candidates?: number;
};
