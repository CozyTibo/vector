import { adminFetch, adminJson } from "../../lib/adminFetch";

import type {
  OperatorActionRequest,
  OperatorActionResponse,
  OperatorOverview,
  OperatorRuntime,
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
