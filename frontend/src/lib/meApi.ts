import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";

import { getApiBase } from "./canonicalApi";
import {
  getSessionAuthSlot,
  mergeProductSessionAuth,
  setStoredSessionToken,
  subscribeSessionToken,
} from "./sessionToken";

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
  const init = mergeProductSessionAuth();
  const hadBearer = Boolean(
    new Headers(init.headers).get("Authorization")?.toLowerCase().startsWith("bearer "),
  );
  const res = await fetch(`${base}/me`, init);
  if (res.status === 401) {
    if (hadBearer) {
      setStoredSessionToken(null);
    }
    return null;
  }
  if (res.status === 403) {
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

type MeQueryOpts = Omit<UseQueryOptions<MeResponse | null, Error>, "queryKey" | "queryFn">;

/**
 * Session-aware `/me` query: key includes whether a bearer token is stored so React Query refetches
 * immediately after login/register (cookie alone is unreliable cross-site on mobile).
 */
export function useProductMeQuery(apiBase: string, options?: MeQueryOpts) {
  const authSlot = useSyncExternalStore(subscribeSessionToken, getSessionAuthSlot, getSessionAuthSlot);
  return useQuery({
    queryKey: ["me", apiBase, authSlot],
    queryFn: () => fetchMe(apiBase),
    ...options,
  });
}
