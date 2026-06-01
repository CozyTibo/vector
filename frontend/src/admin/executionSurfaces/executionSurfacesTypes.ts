export type SurfaceOmission = {
  code: string;
  message: string;
  remediation: string | null;
};

export type SurfaceSection<T> = {
  count: number;
  items: T[];
  omission: SurfaceOmission | null;
};

export type DomainListItem = {
  id: string;
  display_name: string;
  declared_container_kind: string;
  lifecycle_bucket?: string;
  stats?: Record<string, unknown>;
  observation_stats?: {
    events_7d: number;
    activity_delta_7d: number;
    footnote: string;
  };
  active_membership_count?: number;
};

export type ConnectedWorkChain = {
  hops: Array<{
    entity: {
      entity_id: string;
      entity_type: string;
      display_label: string;
      connector: string;
    };
    relationship?: {
      relationship_kind: string;
      relationship_kind_label: string;
      extractor_rule: string;
      evidence_ref: string;
      confidence: string;
    };
  }>;
  hop_count: number;
};

export type DomainSurfaceDetail = {
  id: string;
  display_name: string;
  lifecycle_bucket: string;
  declared_container_kind: string;
  seed_connector: string;
  why_belong_together: string;
  seed_provider_status: string | null;
  summary: {
    stats: Record<string, unknown>;
    member_count: number;
    substrate: {
      advisories: SurfaceOmission[];
      graph_expansion_incomplete: boolean;
    };
  };
  current_work: {
    work_items: SurfaceSection<Record<string, unknown>>;
    pull_requests: SurfaceSection<Record<string, unknown>>;
    documents: SurfaceSection<Record<string, unknown>>;
    deployments: SurfaceSection<Record<string, unknown>>;
  };
  people: {
    owners: Array<Record<string, unknown>>;
    participants: Array<Record<string, unknown>>;
    omission: SurfaceOmission | null;
  };
  activity: {
    execution_timeline_available: boolean;
    footnote: string;
    observation_signals: Array<Record<string, unknown>>;
    omission: SurfaceOmission | null;
  };
  conversations: {
    slack_and_threads: SurfaceSection<Record<string, unknown>>;
    meetings: SurfaceSection<Record<string, unknown>>;
  };
  connected_work: {
    chains: ConnectedWorkChain[];
    count: number;
    omission: SurfaceOmission | null;
  };
  evidence: {
    membership_rules: Array<Record<string, unknown>>;
    graph_rules: Array<Record<string, unknown>>;
  };
};
