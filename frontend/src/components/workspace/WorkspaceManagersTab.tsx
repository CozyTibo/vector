import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { marketingBody, marketingField, workspaceFlatPanel } from "../marketing/marketingStyles";
import {
  fetchOnboarding,
  fetchSlackWorkspaceMembers,
  patchOnboarding,
  type SlackCollaboratorMember,
  type SlackWorkspaceMember,
} from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

export type ManagerTeam = {
  id: string;
  name: string;
  members: SlackCollaboratorMember[];
};

function defaultTeamsFromOnboarding(answers: Record<string, unknown>): ManagerTeam[] {
  const existing = answers.workspace_manager_teams as { teams?: ManagerTeam[] } | undefined;
  if (existing?.teams && Array.isArray(existing.teams) && existing.teams.length > 0) {
    return existing.teams.map((t) => ({
      id: String(t.id),
      name: String(t.name || "Team"),
      members: Array.isArray(t.members) ? (t.members as SlackCollaboratorMember[]) : [],
    }));
  }

  const members: SlackCollaboratorMember[] = [];
  const seen = new Set<string>();

  const ss = answers.slack_stakeholders as
    | { slack_user_ids?: string[]; mention_labels?: string[] }
    | undefined;
  const ids = ss?.slack_user_ids;
  const labels = ss?.mention_labels;
  if (Array.isArray(ids)) {
    ids.forEach((uid, i) => {
      if (typeof uid !== "string" || !uid.trim() || seen.has(uid)) {
        return;
      }
      seen.add(uid);
      const lab = Array.isArray(labels) && typeof labels[i] === "string" ? labels[i]!.trim() : uid;
      const handle = lab.replace(/^@/, "").split(/\s+/)[0] ?? uid;
      members.push({
        slack_user_id: uid,
        username: handle,
        label: lab,
      });
    });
  }

  const collab = answers.slack_collaborators as { members?: SlackCollaboratorMember[] } | undefined;
  if (collab?.members && Array.isArray(collab.members)) {
    for (const m of collab.members) {
      if (!m?.slack_user_id || seen.has(m.slack_user_id)) {
        continue;
      }
      seen.add(m.slack_user_id);
      members.push({
        slack_user_id: m.slack_user_id,
        username: (m.username || m.slack_user_id).replace(/^@/, ""),
        label: m.label || m.username || m.slack_user_id,
      });
    }
  }

  if (members.length === 0) {
    return [];
  }
  return [
    {
      id: crypto.randomUUID(),
      name: "Managers",
      members,
    },
  ];
}

export default function WorkspaceManagersTab() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const me = useProductMeQuery(apiBase);
  const tenantId = me.data?.tenant_id;

  const ob = useQuery({
    queryKey: ["onboarding", apiBase, tenantId ?? ""],
    queryFn: () => fetchOnboarding(apiBase),
    enabled: Boolean(tenantId),
  });

  const slackMembers = useQuery({
    queryKey: ["slack-workspace-members-workspace-page", apiBase, tenantId ?? ""],
    queryFn: () => fetchSlackWorkspaceMembers(apiBase),
    enabled: Boolean(tenantId) && Boolean(ob.data?.slack_connected),
    retry: false,
  });
  const slackRoster = slackMembers.data ?? [];

  const [teams, setTeams] = useState<ManagerTeam[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!ob.data?.answers) {
      return;
    }
    setTeams(defaultTeamsFromOnboarding(ob.data.answers));
    setDirty(false);
  }, [ob.data?.id, ob.data?.version, ob.data?.answers]);

  const saveMut = useMutation({
    mutationFn: async () => {
      await patchOnboarding(apiBase, {
        answers: { workspace_manager_teams: { teams } },
      });
    },
    onSuccess: async () => {
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: ["onboarding", apiBase, tenantId] });
      }
      setDirty(false);
    },
  });

  const addTeam = useCallback(() => {
    setTeams((prev) => [...prev, { id: crypto.randomUUID(), name: "New team", members: [] }]);
    setDirty(true);
  }, []);

  const removeTeam = useCallback((id: string) => {
    setTeams((prev) => prev.filter((t) => t.id !== id));
    setDirty(true);
  }, []);

  const updateTeamName = useCallback((id: string, name: string) => {
    setTeams((prev) => prev.map((t) => (t.id === id ? { ...t, name } : t)));
    setDirty(true);
  }, []);

  const addMemberFromRoster = useCallback((teamId: string, member: SlackWorkspaceMember) => {
    setTeams((prev) =>
      prev.map((t) => {
        if (t.id !== teamId) {
          return t;
        }
        if (t.members.some((m) => m.slack_user_id === member.id)) {
          return t;
        }
        return {
          ...t,
          members: [
            ...t.members,
            {
              slack_user_id: member.id,
              username: member.username,
              label: member.label,
            },
          ],
        };
      }),
    );
    setDirty(true);
  }, []);

  const removeMember = useCallback((teamId: string, slackUserId: string) => {
    setTeams((prev) =>
      prev.map((t) =>
        t.id === teamId
          ? { ...t, members: t.members.filter((m) => m.slack_user_id !== slackUserId) }
          : t,
      ),
    );
    setDirty(true);
  }, []);

  if (ob.isPending || !ob.data) {
    return (
      <div className="flex min-h-[200px] items-center justify-center">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
      </div>
    );
  }

  if (!ob.data.slack_connected) {
    return (
      <div className={`${workspaceFlatPanel} p-6 sm:p-8`}>
        <p className={`${marketingBody} text-zinc-600`}>
          Connect Slack from your workspace Signals page (integrations below) so we can match people by workspace
          handle and display name. Manager teams are stored per workspace and sync with Slack roster
          picks.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-10 lg:space-y-12">
      <p className={`${marketingBody} max-w-3xl text-zinc-600`}>
        Organize managers into teams (for example by org or product area). People are identified from
        your Slack workspace. Changes here are saved for everyone in this workspace.
      </p>

      {slackMembers.isError ? (
        <p className="rounded-lg border-l-4 border-amber-400 bg-amber-50 py-3 pl-4 pr-4 text-sm text-amber-950">
          Could not load Slack members. Check the Slack connection and try again.
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={addTeam}
          className="rounded-lg bg-[#E878BE] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#df6aad] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#E878BE]"
        >
          Add team
        </button>
        <button
          type="button"
          disabled={!dirty || saveMut.isPending}
          onClick={() => saveMut.mutate()}
          className="rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-900 enabled:hover:bg-zinc-50 disabled:opacity-40"
        >
          {saveMut.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>

      {teams.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 px-6 py-12 text-center text-sm text-zinc-600">
          No managers yet. Add a team, then pick people from your Slack directory. If you completed
          onboarding with manager picks, save once to import them here.
        </p>
      ) : (
        <ul className="space-y-6">
          {teams.map((team) => (
            <li key={team.id} className={`${workspaceFlatPanel} p-6 sm:p-7`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <label className="block min-w-[200px] flex-1">
                  <span className="text-xs font-medium text-zinc-500">Team name</span>
                  <input
                    type="text"
                    value={team.name}
                    onChange={(e) => updateTeamName(team.id, e.target.value)}
                    className={`${marketingField} mt-1.5 py-3 text-sm font-medium`}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => removeTeam(team.id)}
                  className="text-sm font-medium text-zinc-500 underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800"
                >
                  Remove team
                </button>
              </div>

              <div className="mt-5">
                <p className="text-xs font-medium text-zinc-500">People</p>
                {team.members.length === 0 ? (
                  <p className="mt-2 text-sm text-zinc-500">No one assigned yet.</p>
                ) : (
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {team.members.map((m) => (
                      <li
                        key={m.slack_user_id}
                        className="inline-flex items-center gap-2 rounded-lg bg-zinc-100 py-1.5 pl-3 pr-1 text-sm text-zinc-900"
                      >
                        <span className="font-medium text-[#0F0F12]">{m.label}</span>
                        <span className="text-zinc-500">@{m.username}</span>
                        <button
                          type="button"
                          onClick={() => removeMember(team.id, m.slack_user_id)}
                          className="rounded-full p-1 text-zinc-400 hover:bg-white hover:text-rose-700"
                          aria-label={`Remove ${m.label}`}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {slackRoster.length ? (
                <div className="mt-4">
                  <p className="text-xs font-medium text-zinc-500">Add from Slack directory</p>
                  <div className="mt-2 max-h-40 overflow-y-auto rounded-xl border border-zinc-100 bg-zinc-50/50 p-2">
                    <ul className="space-y-1">
                      {slackRoster
                        .filter((u) => !team.members.some((m) => m.slack_user_id === u.id))
                        .slice(0, 80)
                        .map((u) => (
                          <li key={u.id}>
                            <button
                              type="button"
                              onClick={() => addMemberFromRoster(team.id, u)}
                              className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-sm hover:bg-white"
                            >
                              <span className="font-medium text-[#0F0F12]">{u.label}</span>
                              <span className="text-xs text-zinc-500">@{u.username}</span>
                            </button>
                          </li>
                        ))}
                    </ul>
                  </div>
                </div>
              ) : slackMembers.isPending ? (
                <p className="mt-4 text-sm text-zinc-500">Loading Slack directory…</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
