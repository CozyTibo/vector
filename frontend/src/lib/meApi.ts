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
  /** False = waitlist: no product shell until an operator enables the workspace. */
  workspace_access_enabled?: boolean;
};

/** Where to send a signed-in user (landing after OAuth, login, signup, waitlist unlock). */
export function signedInDestination(me: MeResponse): string {
  if (me.workspace_access_enabled === false) {
    return "/signup/waitlist";
  }
  const mustFinishOnboarding = "onboarding_completed" in me && me.onboarding_completed !== true;
  return mustFinishOnboarding ? "/app/onboarding" : "/app";
}

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
