import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

export type AdminSlackChannelRow = {
  channel_id: string;
  name: string;
  is_private: boolean;
  is_member: boolean;
  selected_for_ingest: boolean;
  can_bot_join: boolean;
};

type ListResponse = {
  connected: boolean;
  team_id: string | null;
  team_name: string | null;
  saved_channel_ids: string[];
  channels: AdminSlackChannelRow[];
};

type ApplyResponse = {
  saved_channels: { channel_id: string; name: string }[];
  join_results: {
    channel_id: string;
    joined: boolean;
    error: string | null;
    already_member?: boolean;
  }[];
  joined_count: number;
  failed_count: number;
  message: string;
};

type Props = {
  tenantId: string;
  open: boolean;
  onClose: () => void;
};

export default function AdminSlackChannelsModal({ tenantId, open, onClose }: Props) {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [applyResult, setApplyResult] = useState<ApplyResponse | null>(null);

  const listQ = useQuery({
    queryKey: ["admin-slack-channels", tenantId],
    queryFn: () =>
      adminJson<ListResponse>(`/admin/tenants/${tenantId}/connections/slack/channels`),
    enabled: open && Boolean(tenantId),
  });

  useEffect(() => {
    if (!listQ.data) {
      return;
    }
    const ids = new Set<string>();
    for (const ch of listQ.data.channels) {
      if (ch.selected_for_ingest) {
        ids.add(ch.channel_id);
      }
    }
    setSelected(ids);
    setApplyResult(null);
  }, [listQ.data]);

  const applyMut = useMutation({
    mutationFn: async (channelIds: string[]) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/connections/slack/channels`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_ids: channelIds }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return (await res.json()) as ApplyResponse;
    },
    onSuccess: (data) => {
      setApplyResult(data);
      void qc.invalidateQueries({ queryKey: ["admin-slack-channels", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-connections", tenantId] });
    },
  });

  const filtered = useMemo(() => {
    const rows = listQ.data?.channels ?? [];
    const q = query.trim().toLowerCase().replace(/^#/, "");
    if (!q) {
      return rows;
    }
    return rows.filter(
      (c) => c.name.toLowerCase().includes(q) || c.channel_id.toLowerCase().includes(q),
    );
  }, [listQ.data?.channels, query]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="slack-channels-modal-title"
    >
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-xl border border-stone-200 bg-white shadow-xl">
        <div className="border-b border-stone-200 px-5 py-4">
          <h2 id="slack-channels-modal-title" className="text-lg font-semibold text-stone-900">
            Slack channels for ingest
          </h2>
          <p className="mt-1 text-sm text-stone-600">
            Select channels Vector should join and read. Public channels are joined automatically on
            save; private channels require inviting the bot in Slack. History is fetched on the next
            ingestion run.
          </p>
          {listQ.data?.team_name ? (
            <p className="mt-1 text-xs text-stone-500">
              Workspace: {listQ.data.team_name}
            </p>
          ) : null}
        </div>

        <div className="flex-1 overflow-hidden px-5 py-3">
          {listQ.isPending ? (
            <p className="text-sm text-stone-600">Loading channels…</p>
          ) : null}
          {listQ.isError ? (
            <p className="text-sm text-red-700">{(listQ.error as Error).message}</p>
          ) : null}
          {applyMut.isError ? (
            <p className="mb-2 text-sm text-red-700">{(applyMut.error as Error).message}</p>
          ) : null}
          {applyResult ? (
            <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
              <p>{applyResult.message}</p>
              <p className="mt-1 text-xs">
                Joined: {applyResult.joined_count} · Issues: {applyResult.failed_count}
              </p>
            </div>
          ) : null}

          {!listQ.isPending && !listQ.isError ? (
            <>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter by name…"
                  className="min-w-[12rem] flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm"
                />
                <button
                  type="button"
                  className="rounded-lg border border-stone-200 px-3 py-2 text-xs font-medium text-stone-800 hover:bg-stone-50"
                  onClick={() => {
                    setSelected(new Set(filtered.map((c) => c.channel_id)));
                  }}
                >
                  Select visible
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-stone-200 px-3 py-2 text-xs font-medium text-stone-800 hover:bg-stone-50"
                  onClick={() => setSelected(new Set())}
                >
                  Clear
                </button>
              </div>
              <div className="max-h-[50vh] overflow-y-auto rounded-lg border border-stone-200">
                <table className="data-table w-full text-sm">
                  <thead className="sticky top-0 bg-stone-50">
                    <tr>
                      <th className="w-10" />
                      <th>Channel</th>
                      <th>Type</th>
                      <th>Bot member</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="text-stone-500">
                          No channels match.
                        </td>
                      </tr>
                    ) : (
                      filtered.map((ch) => (
                        <tr key={ch.channel_id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={selected.has(ch.channel_id)}
                              onChange={(e) => {
                                setSelected((prev) => {
                                  const next = new Set(prev);
                                  if (e.target.checked) {
                                    next.add(ch.channel_id);
                                  } else {
                                    next.delete(ch.channel_id);
                                  }
                                  return next;
                                });
                              }}
                            />
                          </td>
                          <td className="font-medium">#{ch.name}</td>
                          <td>{ch.is_private ? "Private" : "Public"}</td>
                          <td>
                            {ch.is_member ? (
                              <span className="text-emerald-700">Yes</span>
                            ) : (
                              <span className="text-amber-800">No</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-stone-500">
                {selected.size} selected · {filtered.length} shown · {listQ.data?.channels.length ?? 0}{" "}
                total visible
              </p>
            </>
          ) : null}
        </div>

        <div className="flex justify-end gap-2 border-t border-stone-200 px-5 py-4">
          <button
            type="button"
            className="rounded-lg border border-stone-200 px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
            onClick={onClose}
          >
            Close
          </button>
          <button
            type="button"
            disabled={applyMut.isPending || listQ.isPending}
            className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
            onClick={() => applyMut.mutate([...selected])}
          >
            {applyMut.isPending ? "Saving…" : "Save & join channels"}
          </button>
        </div>
      </div>
    </div>
  );
}
