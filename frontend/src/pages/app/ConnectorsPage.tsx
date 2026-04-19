import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { landingSubtleLineH } from "../../components/landing/landingBrandPalette";
import {
  marketingBody,
  marketingCard,
  marketingKicker,
  marketingMutedLink,
  marketingPageTitle,
} from "../../components/marketing/marketingStyles";
import { ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS } from "../../components/onboarding/onboardingUiConstants";
import { readErrorDetail } from "../../lib/canonicalApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";
import { mergeProductSessionAuth } from "../../lib/sessionToken";

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
    category: "Project management",
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

const connectorTileClass =
  "flex min-h-[11rem] flex-col rounded-2xl border border-zinc-200/90 bg-white/90 p-4 shadow-[0_12px_40px_-28px_rgba(15,23,42,0.14)] ring-1 ring-zinc-950/[0.03] sm:min-h-[12rem] sm:p-5";

const iconLiveClass =
  "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#FDF4F8] text-lg font-semibold text-[#E878BE] ring-1 ring-[#E878BE]/25";

const iconSoonClass =
  "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-zinc-100 text-lg font-semibold text-zinc-400 ring-1 ring-zinc-200/80";

const disconnectBtnClass =
  "mt-auto w-full rounded-full border border-zinc-200/90 bg-white px-4 py-2.5 text-sm font-medium text-[#0F0F12] shadow-sm transition hover:border-zinc-300 hover:bg-zinc-50/90 disabled:cursor-not-allowed disabled:opacity-50";

const connectGradientClass =
  `${ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS} mt-auto flex w-full justify-center py-2.5 text-center sm:py-3`;

const disabledConnectClass =
  "mt-auto w-full cursor-not-allowed rounded-full border border-zinc-200/90 bg-zinc-50 py-2.5 text-sm font-medium text-zinc-400 sm:py-3";

async function fetchConnectors(base: string): Promise<ConnectorsResponse> {
  const res = await fetch(`${base}/connectors`, mergeProductSessionAuth());
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<ConnectorsResponse>;
}

async function disconnectProvider(base: string, provider: string): Promise<void> {
  const res = await fetch(`${base}/connectors/${provider}`, mergeProductSessionAuth({ method: "DELETE" }));
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
  const me = useProductMeQuery(apiBase);
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

  if (q.isPending) {
    return (
      <main className="relative mx-auto flex min-h-0 max-w-3xl flex-1 flex-col items-center justify-center overflow-y-auto px-5 py-16 sm:px-8">
        <div
          className="h-9 w-9 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
        <p className={`${marketingBody} mt-5 text-center`}>Loading connectors…</p>
      </main>
    );
  }

  return (
    <main className="relative mx-auto max-w-3xl min-h-0 flex-1 overflow-y-auto px-5 py-10 sm:px-8 sm:py-14">
      <div className="relative space-y-7 sm:space-y-8">
        <section className={`${marketingCard} overflow-hidden !p-0 sm:!p-0`}>
          <div className={`h-1 w-full ${landingSubtleLineH}`} aria-hidden />
          <div className="px-7 py-8 sm:px-10 sm:py-10">
            <p className={marketingKicker}>Integrations</p>
            <h1 className={`${marketingPageTitle} mt-3`}>Connectors</h1>
            <p className={`${marketingBody} mt-4`}>
              Link the tools your team already uses. Vector syncs activity in the background so your
              workspace stays current.
            </p>
          </div>
        </section>

        {me.data?.use_mock_connectors ? (
          <div className="rounded-2xl border border-rose-200/80 bg-rose-50/90 px-4 py-3 text-sm text-rose-900">
            Development mode: mock connectors are enabled. OAuth flows may still hit real services; data
            can be sample-only.
          </div>
        ) : null}

        {banner ? (
          <div className="rounded-2xl border border-amber-200/90 bg-amber-50/95 px-4 py-3 text-sm text-amber-950">
            {banner}
          </div>
        ) : null}

        {q.isError ? (
          <p className="rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-900">
            {(q.error as Error).message}
          </p>
        ) : null}

        <div className="space-y-10 sm:space-y-12">
          {CATALOG.map((group) => (
            <section key={group.category} className="space-y-4">
              <h2 className={marketingKicker}>{group.category}</h2>
              <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
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
                    <div key={item.id} className={connectorTileClass}>
                      <div className="flex items-start gap-3">
                        <span className={item.live ? iconLiveClass : iconSoonClass} aria-hidden>
                          {item.icon}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-base font-semibold tracking-tight text-[#0F0F12]">{item.name}</p>
                          {connected ? (
                            <p className="mt-1 text-xs font-medium text-emerald-700">Connected</p>
                          ) : item.live ? (
                            <p className="mt-1 text-xs text-[#52525B]">Not connected</p>
                          ) : (
                            <p className="mt-1 text-xs text-zinc-400">Coming soon</p>
                          )}
                        </div>
                      </div>
                      {connected && last !== undefined ? (
                        <p className="mt-3 text-xs leading-relaxed text-[#52525B]">
                          Last sync{" "}
                          <span className="font-medium text-[#0F0F12]">{formatSync(last)}</span>
                        </p>
                      ) : null}
                      {!item.live ? (
                        <button type="button" disabled className={disabledConnectClass}>
                          Connect
                        </button>
                      ) : item.id === "github" ? (
                        connected ? (
                          <button
                            type="button"
                            className={disconnectBtnClass}
                            disabled={ghDisconnect.isPending}
                            onClick={() => ghDisconnect.mutate()}
                          >
                            {ghDisconnect.isPending ? "Disconnecting…" : "Disconnect"}
                          </button>
                        ) : !configured ? (
                          <p className="mt-auto text-xs leading-snug text-amber-900">
                            GitHub is not configured on the API.
                          </p>
                        ) : (
                          <a className={connectGradientClass} href={`${apiBase}/connectors/github/install`}>
                            Connect GitHub
                          </a>
                        )
                      ) : item.id === "linear" ? (
                        connected ? (
                          <button
                            type="button"
                            className={disconnectBtnClass}
                            disabled={linDisconnect.isPending}
                            onClick={() => linDisconnect.mutate()}
                          >
                            {linDisconnect.isPending ? "Disconnecting…" : "Disconnect"}
                          </button>
                        ) : !configured ? (
                          <p className="mt-auto text-xs leading-snug text-amber-900">
                            Linear OAuth is not configured on the API.
                          </p>
                        ) : (
                          <a className={connectGradientClass} href={`${apiBase}/connectors/linear/install`}>
                            Connect Linear
                          </a>
                        )
                      ) : item.id === "slack" ? (
                        connected ? (
                          <button
                            type="button"
                            className={disconnectBtnClass}
                            disabled={slackDisconnect.isPending}
                            onClick={() => slackDisconnect.mutate()}
                          >
                            {slackDisconnect.isPending ? "Disconnecting…" : "Disconnect"}
                          </button>
                        ) : !configured ? (
                          <p className="mt-auto text-xs leading-snug text-amber-900">
                            Slack OAuth is not configured on the API.
                          </p>
                        ) : (
                          <a className={connectGradientClass} href={`${apiBase}/connectors/slack/install`}>
                            Connect Slack
                          </a>
                        )
                      ) : (
                        <button type="button" disabled className={disabledConnectClass}>
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

        <p className="pt-2">
          <Link to="/app" className={`${marketingMutedLink} text-sm underline decoration-zinc-300`}>
            ← Back to workspace
          </Link>
        </p>
      </div>
    </main>
  );
}
