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

export type ConnectorOAuthProvider = "calls" | "github" | "linear" | "notion" | "slack";

export function connectorInstallUrl(
  base: string,
  provider: ConnectorOAuthProvider,
  returnPath: string = CONNECTOR_OAUTH_RETURN_PATH,
  opts?: { installResponseJson?: boolean },
): string {
  const q = new URLSearchParams({ return_to: returnPath });
  if (opts?.installResponseJson) {
    q.set("install_response", "json");
  }
  return `${base}/connectors/${provider}/install?${q.toString()}`;
}

/**
 * Start connector OAuth: POST mints a short-lived ``install_ticket``, then full-page navigation to
 * ``GET /connectors/.../install?install_ticket=…`` so Slack/GitHub OAuth works even when browsers
 * omit ``Authorization`` on navigations (Safari / cross-site cookies). Falls back to legacy GET+json
 * if ``POST /connectors/install/prepare`` is unavailable.
 */
export async function startConnectorOAuthRedirect(
  base: string,
  provider: ConnectorOAuthProvider,
  returnPath: string = CONNECTOR_OAUTH_RETURN_PATH,
): Promise<void> {
  const prepareRes = await fetch(`${base}/connectors/install/prepare`, mergeProductSessionAuth({
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ provider }),
  }));
  if (prepareRes.ok) {
    const prepared = (await prepareRes.json()) as { install_ticket?: unknown; provider?: unknown };
    const ticket = prepared.install_ticket;
    const p = prepared.provider;
    if (typeof ticket === "string" && ticket.trim() && typeof p === "string" && p) {
      const q = new URLSearchParams({ install_ticket: ticket, return_to: returnPath });
      window.location.assign(`${base}/connectors/${p}/install?${q.toString()}`);
      return;
    }
  }

  const url = connectorInstallUrl(base, provider, returnPath, { installResponseJson: true });
  const res = await fetch(url, mergeProductSessionAuth({ method: "GET", redirect: "manual" }));
  const ct = res.headers.get("content-type") ?? "";
  if (res.ok && ct.includes("application/json")) {
    const data = (await res.json()) as { url?: unknown };
    const next = data.url;
    if (typeof next !== "string" || !next.trim()) {
      throw new Error("Could not start connector OAuth (missing redirect URL). Try again.");
    }
    window.location.assign(next);
    return;
  }
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
  throw new Error("Could not start connector OAuth. Try again.");
}
