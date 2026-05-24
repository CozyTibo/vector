import { adminFetch, adminJson } from "../../lib/adminFetch";

import type {
  OperatorActionRequest,
  OperatorActionResponse,
  OperatorEdgeProvenance,
  OperatorGraphComponentRefresh,
  OperatorGraphSnapshot,
  OperatorIslandsList,
  OperatorOverview,
  OperatorQueueTab,
  OperatorQueues,
  OperatorRetrievalEntries,
  OperatorRetrievalEpochs,
  OperatorRetrievalLineage,
  OperatorRuntime,
  OperatorSynthesisJobs,
  OperatorExecutionThread,
} from "./operatorTypes";

async function assertOperatorV2Response(res: Response, label: string): Promise<void> {
  if (res.status === 404) {
    const body = await res.json().catch(() => ({}));
    if (body.detail === "operator_admin_v2_disabled") {
      throw new Error("operator_admin_v2_disabled");
    }
  }
  if (!res.ok) {
    throw new Error(`${label} ${res.status}`);
  }
}

export async function fetchOperatorOverview(tenantId: string): Promise<OperatorOverview> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/overview`);
  await assertOperatorV2Response(res, "operator overview");
  return res.json();
}

export async function fetchOperatorRuntime(
  tenantId: string,
  params: { transitionLimit?: number; transitionOffset?: number } = {},
): Promise<OperatorRuntime> {
  const search = new URLSearchParams();
  if (params.transitionLimit != null) {
    search.set("transition_limit", String(params.transitionLimit));
  }
  if (params.transitionOffset != null) {
    search.set("transition_offset", String(params.transitionOffset));
  }
  const qs = search.toString();
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/runtime${qs ? `?${qs}` : ""}`,
  );
  await assertOperatorV2Response(res, "operator runtime");
  return res.json();
}

export async function postOperatorAction(
  tenantId: string,
  body: OperatorActionRequest,
): Promise<OperatorActionResponse> {
  try {
    return await adminJson<OperatorActionResponse>(`/admin/tenants/${tenantId}/cortex/operator/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("Confirmation phrase does not match")) {
      throw new Error("confirmation_mismatch");
    }
    throw e;
  }
}

export async function fetchOperatorGraphSnapshot(tenantId: string): Promise<OperatorGraphSnapshot> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/snapshots/graph`);
  await assertOperatorV2Response(res, "operator graph snapshot");
  return res.json();
}

export async function fetchOperatorEdgeProvenance(
  tenantId: string,
  query: Record<string, string>,
): Promise<OperatorEdgeProvenance> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value.trim()) search.set(key, value.trim());
  }
  const qs = search.toString();
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/edges${qs ? `?${qs}` : ""}`,
  );
  if (res.status === 400) {
    throw new Error("edge_query_required");
  }
  await assertOperatorV2Response(res, "operator edge provenance");
  return res.json();
}

export async function fetchOperatorIslandsList(tenantId: string): Promise<OperatorIslandsList> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/inspect/islands`);
  await assertOperatorV2Response(res, "operator islands");
  return res.json();
}

export async function postOperatorGraphSnapshotRefresh(
  tenantId: string,
): Promise<OperatorGraphComponentRefresh> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/snapshots/graph/refresh`, {
    method: "POST",
  });
  await assertOperatorV2Response(res, "operator graph refresh");
  return res.json();
}

export async function fetchOperatorQueues(
  tenantId: string,
  params: { tab?: OperatorQueueTab; limit?: number; offset?: number } = {},
): Promise<OperatorQueues> {
  const search = new URLSearchParams();
  if (params.tab) search.set("tab", params.tab);
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.offset != null) search.set("offset", String(params.offset));
  const qs = search.toString();
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/queues${qs ? `?${qs}` : ""}`);
  await assertOperatorV2Response(res, "operator queues");
  return res.json();
}

export async function fetchOperatorRetrievalEpochs(
  tenantId: string,
  limit = 5,
): Promise<OperatorRetrievalEpochs> {
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/retrieval/epochs?limit=${limit}`,
  );
  await assertOperatorV2Response(res, "operator retrieval epochs");
  return res.json();
}

export async function fetchOperatorRetrievalEntries(
  tenantId: string,
  params: {
    entity_id?: string;
    scope_ref?: string;
    index_kind?: string;
    walk_id?: string;
    external_url?: string;
    limit?: number;
    offset?: number;
  },
): Promise<OperatorRetrievalEntries> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && String(value).trim()) search.set(key, String(value).trim());
  }
  const qs = search.toString();
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/retrieval/entries${qs ? `?${qs}` : ""}`,
  );
  if (res.status === 400) {
    throw new Error("search_query_required");
  }
  await assertOperatorV2Response(res, "operator retrieval entries");
  return res.json();
}

export async function fetchOperatorRetrievalLineage(
  tenantId: string,
  artifactKind: string,
  artifactRef: string,
): Promise<OperatorRetrievalLineage> {
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/retrieval/lineage/${encodeURIComponent(artifactKind)}/${encodeURIComponent(artifactRef)}`,
  );
  await assertOperatorV2Response(res, "operator retrieval lineage");
  return res.json();
}

export async function fetchOperatorSynthesisJobs(
  tenantId: string,
  params: { status?: string; q?: string; limit?: number; offset?: number } = {},
): Promise<OperatorSynthesisJobs> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.offset != null) search.set("offset", String(params.offset));
  const qs = search.toString();
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/synthesis/jobs${qs ? `?${qs}` : ""}`,
  );
  await assertOperatorV2Response(res, "operator synthesis jobs");
  return res.json();
}

export async function fetchOperatorExecutionThread(
  tenantId: string,
  params: {
    walk_id?: string;
    tcre_job_id?: string;
    scope_ref?: string;
    replay_identity?: string;
    limit?: number;
  },
): Promise<OperatorExecutionThread> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && String(value).trim()) search.set(key, String(value).trim());
  }
  const qs = search.toString();
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/execution/thread${qs ? `?${qs}` : ""}`,
  );
  if (res.status === 400) {
    throw new Error("search_query_required");
  }
  await assertOperatorV2Response(res, "operator execution thread");
  return res.json();
}
