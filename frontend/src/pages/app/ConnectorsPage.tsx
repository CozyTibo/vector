import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { readErrorDetail } from "../../lib/canonicalApi";
import { productApiBase } from "../../lib/meApi";

type GithubDetails = {
  connection_id: string | null;
  installation_id: number | null;
  account_login: string | null;
  account_type: string | null;
  last_sync_at?: string | null;
};

type LinearDetails = {
  connection_id: string | null;
  organization_id: string | null;
  organization_name: string | null;
  last_sync_at?: string | null;
};

type SlackDetails = {
  connection_id: string | null;
  team_id: string | null;
  team_name: string | null;
  last_sync_at?: string | null;
};

type ConnectorRow =
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

type ConnectorsResponse = { items: ConnectorRow[] };

type CatalogItem = {
  id: string;
  name: string;
  icon: string;
  live: boolean;
};

const CATALOG: { category: string; items: CatalogItem[] }[] = [
  {
    category: "Engineering",
    items: [
      { id: "github", name: "GitHub", icon: "↗", live: true },
      { id: "gitlab", name: "GitLab", icon: "◈", live: false },
    ],
  },
  {
    category: "Project Management",
    items: [
      { id: "linear", name: "Linear", icon: "◎", live: true },
      { id: "jira", name: "Jira", icon: "▤", live: false },
    ],
  },
  {
    category: "Communication",
    items: [{ id: "slack", name: "Slack", icon: "#", live: true }],
  },
  {
    category: "Documentation",
    items: [{ id: "notion", name: "Notion", icon: "N", live: false }],
  },
];

async function fetchConnectors(base: string): Promise<ConnectorsResponse> {
  const res = await fetch(`${base}/connectors`, { credentials: "include" });
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<ConnectorsResponse>;
}

async function disconnectProvider(base: string, provider: string): Promise<void> {
  const res = await fetch(`${base}/connectors/${provider}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(await readErrorDetail(res));
  }
}

function formatSync(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function ConnectorsPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const [banner, setBanner] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthErr = params.get("oauth_error");
    if (oauthErr === "state") {
      setBanner("Sign-in failed (invalid or expired state). Try again.");
    } else if (oauthErr === "token") {
      setBanner("Sign-in failed (could not validate account with Google).");
    }
    const gh = params.get("github_connected");
    const ghErr = params.get("github_error");
    const lin = params.get("linear_connected");
    const linErr = params.get("linear_error");
    const sl = params.get("slack_connected");
    const slErr = params.get("slack_error");
    if (gh === "1" || lin === "1" || sl === "1") {
      setBanner(null);
      void qc.invalidateQueries({ queryKey: ["connectors", apiBase] });
    }
    if (ghErr === "state") {
      setBanner("GitHub connect failed (invalid or expired state).");
    } else if (ghErr === "oauth") {
      setBanner("GitHub OAuth failed. Check app credentials.");
    } else if (ghErr === "conflict") {
      setBanner("This GitHub installation is already linked to another workspace.");
    } else if (linErr === "state") {
      setBanner("Linear connect failed (invalid or expired state).");
    } else if (linErr === "oauth") {
      setBanner("Linear OAuth failed. Check LINEAR_CLIENT_* and redirect URI.");
    } else if (slErr === "state") {
      setBanner("Slack connect failed (invalid or expired state).");
    } else if (slErr === "oauth") {
      setBanner("Slack OAuth failed. Check SLACK_* and redirect URI.");
    } else if (slErr === "denied") {
      setBanner("Slack connection was cancelled or denied.");
    } else if (slErr === "workspace_taken") {
      setBanner("This Slack workspace is already linked to another Vector workspace.");
    }
    if (
      oauthErr ||
      gh ||
      ghErr ||
      lin ||
      linErr ||
      params.get("oauth_ok") ||
      params.get("github_connected") ||
      params.get("linear_connected") ||
      params.get("slack_connected") ||
      params.get("slack_error")
    ) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [apiBase, qc]);

  const q = useQuery({
    queryKey: ["connectors", apiBase],
    queryFn: () => fetchConnectors(apiBase),
  });

  const statusById = useMemo(() => {
    const m = new Map<string, ConnectorRow>();
    for (const row of q.data?.items ?? []) {
      m.set(row.provider, row);
    }
    return m;
  }, [q.data?.items]);

  const ghDisconnect = useMutation({
    mutationFn: () => disconnectProvider(apiBase, "github"),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["connectors", apiBase] }),
    onError: (e: Error) => setBanner(e.message),
  });
  const linDisconnect = useMutation({
    mutationFn: () => disconnectProvider(apiBase, "linear"),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["connectors", apiBase] }),
    onError: (e: Error) => setBanner(e.message),
  });
  const slackDisconnect = useMutation({
    mutationFn: () => disconnectProvider(apiBase, "slack"),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["connectors", apiBase] }),
    onError: (e: Error) => setBanner(e.message),
  });

  return (
    <main className="mx-auto max-w-4xl min-h-0 flex-1 overflow-y-auto px-4 py-10">
      <h1 className="mb-2 text-2xl font-semibold text-stone-900">Connectors</h1>
      <p className="mb-6 text-sm text-stone-600">Link tools to your workspace.</p>
      {banner ? (
        <p className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {banner}
        </p>
      ) : null}
      {q.isError ? (
        <p className="text-sm text-red-700">{(q.error as Error).message}</p>
      ) : null}

      <div className="space-y-10">
        {CATALOG.map((group) => (
          <section key={group.category}>
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-stone-500">
              {group.category}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {group.items.map((item) => {
                const row = statusById.get(item.id);
                const connected = row?.connected === true;
                const configured = row?.connector_configured !== false;
                const last =
                  row?.provider === "github"
                    ? row.details?.last_sync_at
                    : row?.provider === "linear"
                      ? row.details?.last_sync_at
                      : row?.provider === "slack"
                        ? row.details?.last_sync_at
                        : undefined;

                return (
                  <div
                    key={item.id}
                    className="flex flex-col rounded-xl border border-stone-200 bg-white p-4 shadow-sm"
                  >
                    <div className="mb-3 flex items-start gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100 text-lg text-stone-600">
                        {item.icon}
                      </span>
                      <div>
                        <div className="font-medium text-stone-900">{item.name}</div>
                        {connected ? (
                          <div className="mt-1 text-xs text-green-700">Connected</div>
                        ) : item.live ? (
                          <div className="mt-1 text-xs text-stone-500">Not connected</div>
                        ) : (
                          <div className="mt-1 text-xs text-stone-400">Coming soon</div>
                        )}
                      </div>
                    </div>
                    {connected && last !== undefined ? (
                      <p className="mb-3 text-xs text-stone-500">
                        Last sync:{" "}
                        <span className="font-medium text-stone-700">{formatSync(last)}</span>
                      </p>
                    ) : null}
                    {!item.live ? (
                      <button
                        type="button"
                        disabled
                        className="mt-auto w-full rounded-lg border border-stone-200 bg-stone-50 py-2 text-sm text-stone-400"
                      >
                        Connect
                      </button>
                    ) : item.id === "github" ? (
                      connected ? (
                        <div className="mt-auto flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                            disabled={ghDisconnect.isPending}
                            onClick={() => ghDisconnect.mutate()}
                          >
                            Disconnect
                          </button>
                        </div>
                      ) : !configured ? (
                        <p className="mt-auto text-xs text-amber-800">GitHub is not configured on the API.</p>
                      ) : (
                        <a
                          className="mt-auto block w-full rounded-lg bg-stone-900 py-2 text-center text-sm font-medium text-white no-underline hover:bg-stone-800"
                          href={`${apiBase}/connectors/github/install`}
                        >
                          Connect
                        </a>
                      )
                    ) : item.id === "linear" ? (
                      connected ? (
                        <button
                          type="button"
                          className="mt-auto rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                          disabled={linDisconnect.isPending}
                          onClick={() => linDisconnect.mutate()}
                        >
                          Disconnect
                        </button>
                      ) : !configured ? (
                        <p className="mt-auto text-xs text-amber-800">Linear OAuth is not configured on the API.</p>
                      ) : (
                        <a
                          className="mt-auto block w-full rounded-lg bg-stone-900 py-2 text-center text-sm font-medium text-white no-underline hover:bg-stone-800"
                          href={`${apiBase}/connectors/linear/install`}
                        >
                          Connect
                        </a>
                      )
                    ) : item.id === "slack" ? (
                      connected ? (
                        <button
                          type="button"
                          className="mt-auto rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                          disabled={slackDisconnect.isPending}
                          onClick={() => slackDisconnect.mutate()}
                        >
                          Disconnect
                        </button>
                      ) : !configured ? (
                        <p className="mt-auto text-xs text-amber-800">Slack OAuth is not configured on the API.</p>
                      ) : (
                        <a
                          className="mt-auto block w-full rounded-lg bg-stone-900 py-2 text-center text-sm font-medium text-white no-underline hover:bg-stone-800"
                          href={`${apiBase}/connectors/slack/install`}
                        >
                          Connect
                        </a>
                      )
                    ) : (
                      <button
                        type="button"
                        disabled
                        className="mt-auto w-full rounded-lg border border-stone-200 bg-stone-50 py-2 text-sm text-stone-400"
                      >
                        Connect
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
      <p className="mt-10 text-sm text-stone-500">
        <Link to="/app" className="text-blue-600 underline">
          ← App home
        </Link>
      </p>
    </main>
  );
}
