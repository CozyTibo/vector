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
  OperatorPeopleDirectory,
  OperatorPersonProfile,
} from "./operatorTypes";

async function assertOk(res: Response, label: string): Promise<void> {
  if (!res.ok) {
    throw new Error(`${label} ${res.status}`);
  }
}

export async function fetchOperatorOverview(tenantId: string): Promise<OperatorOverview> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/overview`);
  await assertOk(res, "operator overview");
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
  await assertOk(res, "operator runtime");
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
  await assertOk(res, "operator graph snapshot");
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
  await assertOk(res, "operator edge provenance");
  return res.json();
}

export async function fetchOperatorIslandsList(tenantId: string): Promise<OperatorIslandsList> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/inspect/islands`);
  await assertOk(res, "operator islands");
  return res.json();
}

export async function postOperatorGraphSnapshotRefresh(
  tenantId: string,
): Promise<OperatorGraphComponentRefresh> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/snapshots/graph/refresh`, {
    method: "POST",
  });
  await assertOk(res, "operator graph refresh");
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
  await assertOk(res, "operator queues");
  return res.json();
}

export async function fetchOperatorRetrievalEpochs(
  tenantId: string,
  limit = 5,
): Promise<OperatorRetrievalEpochs> {
  const res = await adminFetch(
    `/admin/tenants/${tenantId}/cortex/operator/inspect/retrieval/epochs?limit=${limit}`,
  );
  await assertOk(res, "operator retrieval epochs");
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
  await assertOk(res, "operator retrieval entries");
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
  await assertOk(res, "operator retrieval lineage");
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
  await assertOk(res, "operator synthesis jobs");
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
  await assertOk(res, "operator execution thread");
  return res.json();
}

export async function fetchOperatorPeopleDirectory(
  tenantId: string,
  params: { limit?: number; offset?: number } = {},
): Promise<OperatorPeopleDirectory> {
  const search = new URLSearchParams();
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.offset != null) search.set("offset", String(params.offset));
  const qs = search.toString();
  try {
    return await adminJson<OperatorPeopleDirectory>(
      `/admin/tenants/${tenantId}/cortex/operator/people${qs ? `?${qs}` : ""}`,
      undefined,
      { timeoutMs: 90_000 },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("503") || msg.toLowerCase().includes("unavailable")) {
      throw new Error("People directory API unavailable (503) — backend may still be deploying or the query timed out.");
    }
    throw e;
  }
}

export async function fetchOperatorPersonProfile(
  tenantId: string,
  personId: string,
  params: { activityLimit?: number } = {},
): Promise<OperatorPersonProfile> {
  const search = new URLSearchParams();
  if (params.activityLimit != null) search.set("activity_limit", String(params.activityLimit));
  const qs = search.toString();
  try {
    return await adminJson<OperatorPersonProfile>(
      `/admin/tenants/${tenantId}/cortex/operator/people/${personId}${qs ? `?${qs}` : ""}`,
      undefined,
      { timeoutMs: 90_000 },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("404") || msg.includes("person_not_found")) {
      throw new Error("person_not_found");
    }
    if (msg.includes("503") || msg.toLowerCase().includes("unavailable")) {
      throw new Error("Person profile API unavailable (503) — backend may still be deploying or the query timed out.");
    }
    throw e;
  }
}
