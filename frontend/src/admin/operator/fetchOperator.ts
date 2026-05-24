import { adminFetch } from "../../lib/adminFetch";

import type { OperatorOverview } from "./operatorTypes";

export async function fetchOperatorOverview(tenantId: string): Promise<OperatorOverview> {
  const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/overview`);
  if (res.status === 404) {
    const body = await res.json().catch(() => ({}));
    if (body.detail === "operator_admin_v2_disabled") {
      throw new Error("operator_admin_v2_disabled");
    }
  }
  if (!res.ok) {
    throw new Error(`operator overview ${res.status}`);
  }
  return res.json();
}
