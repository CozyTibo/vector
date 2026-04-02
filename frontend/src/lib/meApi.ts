import { getApiBase } from "./canonicalApi";

export type MeResponse = {
  user_id: string;
  email: string;
  full_name: string | null;
  tenant_id: string;
  company_name: string;
  tenant_slug: string;
  role: string;
  /** When absent (legacy API), RequireAuth does not gate on onboarding. */
  onboarding_completed?: boolean;
  /** Active connector provider keys for this tenant (e.g. github, linear). */
  connected_connectors?: string[];
  /** True when backend uses local mock GitHub/Linear URLs (development only). */
  use_mock_connectors?: boolean;
};

export async function fetchMe(base: string): Promise<MeResponse | null> {
  const res = await fetch(`${base}/me`, { credentials: "include" });
  if (res.status === 401 || res.status === 403) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<MeResponse>;
}

export function productApiBase(): string {
  return getApiBase();
}
