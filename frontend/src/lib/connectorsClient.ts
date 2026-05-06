import { readErrorDetail } from "./canonicalApi";
import { mergeProductSessionAuth } from "./sessionToken";

export type GithubDetails = {
  connection_id: string | null;
  installation_id: number | null;
  account_login: string | null;
  account_type: string | null;
  last_sync_at?: string | null;
};

export type LinearDetails = {
  connection_id: string | null;
  organization_id: string | null;
  organization_name: string | null;
  last_sync_at?: string | null;
};

export type SlackDetails = {
  connection_id: string | null;
  team_id: string | null;
  team_name: string | null;
  last_sync_at?: string | null;
};

export type ConnectorRow =
  | {
      provider: "github";
      display_name: string;
      connector_configured: boolean;
      connected: boolean;
      details: GithubDetails | null;
    }
  | {
      provider: "linear";
      display_name: string;
      connector_configured: boolean;
      connected: boolean;
      details: LinearDetails | null;
    }
  | {
      provider: "slack";
      display_name: string;
      connector_configured: boolean;
      connected: boolean;
      details: SlackDetails | null;
    };

export type ConnectorsResponse = { items: ConnectorRow[] };

export async function fetchConnectors(base: string): Promise<ConnectorsResponse> {
  const res = await fetch(`${base}/connectors`, mergeProductSessionAuth());
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<ConnectorsResponse>;
}

export async function disconnectConnector(base: string, provider: string): Promise<void> {
  const res = await fetch(`${base}/connectors/${provider}`, mergeProductSessionAuth({ method: "DELETE" }));
  if (!res.ok && res.status !== 204) {
    throw new Error(await readErrorDetail(res));
  }
}

/** Post-OAuth redirect; must satisfy backend `sanitize_*_return_to` (path under `/app/`). */
export const CONNECTOR_OAUTH_RETURN_PATH = "/app/";

export type ConnectorOAuthProvider = "github" | "linear" | "notion" | "slack";

export function connectorInstallUrl(
  base: string,
  provider: ConnectorOAuthProvider,
  returnPath: string = CONNECTOR_OAUTH_RETURN_PATH,
): string {
  const q = new URLSearchParams({ return_to: returnPath });
  return `${base}/connectors/${provider}/install?${q.toString()}`;
}

/**
 * Start connector OAuth from the SPA using the same auth as API ``fetch`` (cookie + optional Bearer
 * from localStorage). Plain ``<a href={api}/install>`` does not send ``Authorization``, so users who
 * only have a bearer token (e.g. Google sign-in / ITP) get 401 on install links.
 */
export async function startConnectorOAuthRedirect(
  base: string,
  provider: ConnectorOAuthProvider,
  returnPath: string = CONNECTOR_OAUTH_RETURN_PATH,
): Promise<void> {
  const url = connectorInstallUrl(base, provider, returnPath);
  const res = await fetch(url, mergeProductSessionAuth({ method: "GET", redirect: "manual" }));
  if (res.status >= 300 && res.status < 400) {
    const loc = res.headers.get("Location");
    if (loc) {
      window.location.assign(new URL(loc, url).href);
      return;
    }
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
}
