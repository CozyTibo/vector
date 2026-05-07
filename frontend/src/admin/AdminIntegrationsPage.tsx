import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { OperatorIntro, OperatorSection } from "./ui/OperatorSections";
import { StatusBadge } from "./ui/StatusBadge";

type StatusTone = "ok" | "warn" | "neutral" | "bad";
type Conn = { id: string; provider: string; status: string; created_at: string };
type AdminConnectorConnectLinkResponse = {
  provider: "slack" | "github" | "linear" | "notion" | "calls";
  connect_url: string;
  tenant_id: string;
  user_id: string;
};

const CARD_ORDER = ["slack", "github", "linear", "notion", "calls"] as const;

type OAuthProvider = "slack" | "github" | "linear" | "notion" | "calls";
const OAUTH_PROVIDERS: readonly OAuthProvider[] = ["slack", "github", "linear", "notion", "calls"];

function titleCaseProvider(p: string) {
  if (p === "github") return "GitHub";
  if (p === "notion") return "Notion";
  if (p === "calls") return "Gemini";
  if (p === "linear") return "Linear";
  return p.charAt(0).toUpperCase() + p.slice(1);
}

export default function AdminIntegrationsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  const disconnectMut = useMutation({
    mutationFn: async (provider: string) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/connections/${encodeURIComponent(provider)}`, {
        method: "DELETE",
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-connections", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
    },
  });
  const connectLinkMut = useMutation({
    mutationFn: async (provider: OAuthProvider) =>
      adminJson<AdminConnectorConnectLinkResponse>(
        `/admin/tenants/${tenantId}/connections/${provider}/connect-link`,
      ),
  });

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading integrations…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const byProvider = new Map(q.data.items.map((c) => [c.provider, c]));

  return (
    <div className="space-y-8">
      <OperatorIntro title="Integrations">
        OAuth links let Vector read Slack, GitHub, Linear, Notion, or Calls on behalf of this workspace.
      </OperatorIntro>

      <OperatorSection
        title="Connection status"
        description="Each card is one integration channel. Disconnect removes tokens only; historical rows stay until you reset the pipeline."
      >
        {disconnectMut.isError ? (
          <p className="mb-4 text-sm text-red-700">{(disconnectMut.error as Error).message}</p>
        ) : null}
        {connectLinkMut.isError ? (
          <p className="mb-4 text-sm text-red-700">{(connectLinkMut.error as Error).message}</p>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CARD_ORDER.map((provider) => {
            const c = byProvider.get(provider);
            const badge: { tone: StatusTone; label: string } = (() => {
              if (c) return { tone: c.status === "active" ? "ok" : "warn", label: c.status };
              return { tone: "neutral", label: "Not connected" };
            })();
            return (
              <div
                key={provider}
                className="flex flex-col rounded-xl border border-stone-200 bg-stone-50/50 p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-lg font-semibold text-stone-900">{titleCaseProvider(provider)}</h3>
                  <StatusBadge tone={badge.tone}>{badge.label}</StatusBadge>
                </div>
                <dl className="mt-4 space-y-2 text-sm">
                  <div>
                    <dt className="text-stone-500">Connected account</dt>
                    <dd className="text-stone-800">
                      OAuth (workspace-scoped)
                    </dd>
                  </div>
                  <div>
                    <dt className="text-stone-500">Connected since</dt>
                    <dd className="text-stone-800">
                      {c ? new Date(c.created_at).toLocaleString() : "—"}
                    </dd>
                  </div>
                </dl>
                <div className="mt-4 space-y-2 border-t border-stone-200 pt-4">
                  {c ? (
                    <>
                      {OAUTH_PROVIDERS.includes(provider as OAuthProvider) && (
                        <>
                          <button
                            type="button"
                            className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                            disabled={connectLinkMut.isPending}
                            onClick={async () => {
                              const out = await connectLinkMut.mutateAsync(provider);
                              await navigator.clipboard.writeText(out.connect_url);
                            }}
                          >
                            {connectLinkMut.isPending && connectLinkMut.variables === provider
                              ? "Generating…"
                              : "Copy connect link"}
                          </button>
                          <button
                            type="button"
                            className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                            disabled={connectLinkMut.isPending}
                            onClick={async () => {
                              const out = await connectLinkMut.mutateAsync(provider);
                              window.open(out.connect_url, "_blank", "noopener,noreferrer");
                            }}
                          >
                            Open connect flow
                          </button>
                        </>
                      )}
                      <button
                        type="button"
                        className="w-full rounded-lg border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-50 disabled:opacity-50"
                        disabled={disconnectMut.isPending}
                        onClick={() => {
                          if (
                            !window.confirm(
                              `Disconnect ${titleCaseProvider(provider)}? OAuth tokens are removed.`,
                            )
                          ) {
                            return;
                          }
                          disconnectMut.mutate(provider);
                        }}
                      >
                        Disconnect
                      </button>
                      {connectLinkMut.isSuccess && connectLinkMut.data.provider === provider ? (
                        <p className="text-xs text-stone-600">
                          Connect link generated for user{" "}
                          <span className="font-mono">{connectLinkMut.data.user_id}</span>.
                        </p>
                      ) : null}
                    </>
                  ) : OAUTH_PROVIDERS.includes(provider as OAuthProvider) ? (
                    <>
                      <button
                        type="button"
                        className="w-full rounded-lg border border-blue-200 bg-blue-50/80 px-3 py-2 text-sm font-medium text-blue-900 hover:bg-blue-100 disabled:opacity-50"
                        disabled={connectLinkMut.isPending}
                        onClick={async () => {
                          const out = await connectLinkMut.mutateAsync(provider);
                          await navigator.clipboard.writeText(out.connect_url);
                        }}
                      >
                        {connectLinkMut.isPending && connectLinkMut.variables === provider
                          ? "Generating…"
                          : "Copy connect link"}
                      </button>
                      <button
                        type="button"
                        className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                        disabled={connectLinkMut.isPending}
                        onClick={async () => {
                          const out = await connectLinkMut.mutateAsync(provider);
                          window.open(out.connect_url, "_blank", "noopener,noreferrer");
                        }}
                      >
                        Open connect flow
                      </button>
                      {connectLinkMut.isSuccess && connectLinkMut.data.provider === provider ? (
                        <p className="text-xs text-stone-600">
                          Link generated for tenant user{" "}
                          <span className="font-mono">{connectLinkMut.data.user_id}</span>.
                        </p>
                      ) : (
                        <p className="text-xs text-stone-500">
                          Generate a tenant-scoped OAuth link and share it with the customer.
                        </p>
                      )}
                    </>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </OperatorSection>

      <details className="rounded-lg border border-stone-200 bg-white">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-stone-600">
          Debug: connection records (table view)
        </summary>
        <div className="border-t border-stone-100 p-4">
          <div className="overflow-x-auto">
            <table className="data-table text-sm">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Connection id</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-stone-500">
                      No connections
                    </td>
                  </tr>
                ) : (
                  q.data.items.map((c) => (
                    <tr key={c.id}>
                      <td>{c.provider}</td>
                      <td>{c.status}</td>
                      <td className="font-mono text-xs">{c.id}</td>
                      <td>{new Date(c.created_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </details>
    </div>
  );
}
