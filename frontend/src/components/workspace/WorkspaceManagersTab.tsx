import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { marketingBody, workspaceFlatPanel } from "../marketing/marketingStyles";
import {
  workspaceInputFocusRing,
  workspacePrimaryButtonBase,
  workspacePrimaryButtonToolbar,
  workspaceSecondaryButtonBase,
  workspaceSpinnerMd,
} from "./workspaceUiTokens";
import {
  filterSlackMembersByQuery,
  rosterWithoutSlackbot,
  slackMemberPickerPrimary,
  slackMemberPickerSecondary,
} from "../onboarding/slackMemberSearchUtils";
import {
  fetchOnboarding,
  fetchSlackWorkspaceMembers,
  patchOnboarding,
  type SlackCollaboratorMember,
  type SlackWorkspaceMember,
} from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";
import { workspaceAccessGroupPath } from "../../lib/workspaceAccess";
import {
  defaultTeamsFromOnboarding,
  legacyVectorCompanyWideUsersFromTeams,
  legacyVectorManagerAccessModeFromTeams,
  teamsForOnboardingApi,
  type ManagerAccessScope,
  type ManagerTeam,
} from "../../lib/workspaceManagerTeams";
import SlackUserAvatar from "./SlackUserAvatar";

export type { ManagerTeam };

/** Whether a row satisfies save rules (manager set, in members, scope member counts). */
function isTeamStructurallyComplete(team: ManagerTeam): boolean {
  if (team.manager_slack_user_id == null) {
    return false;
  }
  if (!team.members.some((m) => m.slack_user_id === team.manager_slack_user_id)) {
    return false;
  }
  if (team.access_scope === "all") {
    return team.members.length === 1;
  }
  return team.members.length >= 2;
}

/** Non-null when the manager list cannot be saved yet. */
function validateWorkspaceAccessSave(teams: ManagerTeam[]): string | null {
  if (teams.length === 0) {
    return "Add at least one manager.";
  }
  for (const t of teams) {
    if (t.manager_slack_user_id == null) {
      return "Each row needs a manager chosen from Slack.";
    }
    if (!t.members.some((m) => m.slack_user_id === t.manager_slack_user_id)) {
      return "Each row’s manager must be included in that row’s Slack people (open Edit on the row to fix).";
    }
    if (!isTeamStructurallyComplete(t)) {
      if (t.access_scope === "all") {
        return "All access rows must include only the manager. Remove extra people or switch to scoped access.";
      }
      return "Scoped access needs the manager plus at least one other person in scope.";
    }
  }
  return null;
}

function managerMember(team: ManagerTeam): SlackCollaboratorMember | undefined {
  const mgr = team.manager_slack_user_id;
  return mgr ? team.members.find((m) => m.slack_user_id === mgr) : undefined;
}

/** Scoped rows: people in scope excluding the manager (for table “People” column). */
function scopedMembersExcludingManager(team: ManagerTeam): SlackCollaboratorMember[] {
  const mgr = team.manager_slack_user_id;
  if (!mgr || team.access_scope !== "scoped") {
    return [];
  }
  return team.members.filter((m) => m.slack_user_id !== mgr);
}

/** Slack picks for manager: full roster minus people who are already managers on other rows (current row’s manager stays selectable). */
function slackCandidatesForManagerPicker(
  roster: SlackWorkspaceMember[],
  teams: ManagerTeam[],
  teamId: string,
  currentManagerId: string | null,
): SlackWorkspaceMember[] {
  const usedElsewhere = new Set(
    teams
      .filter((t) => t.id !== teamId && t.manager_slack_user_id)
      .map((t) => t.manager_slack_user_id as string),
  );
  return roster.filter(
    (u) => !usedElsewhere.has(u.id) || (currentManagerId !== null && u.id === currentManagerId),
  );
}

/** Scoped team members only: full Slack roster minus this row’s manager and people already in scope. */
function slackCandidatesForScopeMembers(roster: SlackWorkspaceMember[], team: ManagerTeam): SlackWorkspaceMember[] {
  const mgr = team.manager_slack_user_id;
  const inScope = new Set(scopedMembersExcludingManager(team).map((m) => m.slack_user_id));
  return roster.filter((u) => (mgr == null || u.id !== mgr) && !inScope.has(u.id));
}

const rowCtaQuietClass =
  "rounded-lg px-2.5 py-1.5 text-xs font-semibold text-zinc-600 transition hover:bg-zinc-100 hover:text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40 sm:text-sm";

const inputBase = `w-full rounded-lg border border-zinc-200 bg-white px-3.5 py-2.5 text-base font-medium leading-snug text-[#0F0F12] outline-none transition-[border-color,box-shadow] placeholder:text-zinc-400 ${workspaceInputFocusRing}`;

const labelClass = "text-sm font-semibold text-zinc-600";

/** Chevron down — dropdown trigger for per-team actions. */
function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width={18}
      height={18}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M21 21l-4.35-4.35M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14Z"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Slack roster search + pick; keeps the card compact vs. a full scroll list. */
function SlackMemberCombobox({
  candidates,
  onPick,
  slackDirectoryEmpty,
  placeholder = "Search Slack to add people…",
}: {
  candidates: SlackWorkspaceMember[];
  onPick: (member: SlackWorkspaceMember) => void;
  /** True when the roster loaded and has zero people (different copy than “all on team”). */
  slackDirectoryEmpty: boolean;
  /** Input placeholder (e.g. choose manager vs add to scope). */
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputId = useId();
  const listboxId = useId();

  const filtered = useMemo(() => filterSlackMembersByQuery(candidates, query), [candidates, query]);

  useEffect(() => {
    setHighlight(0);
  }, [query, filtered.length]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const pick = useCallback(
    (m: SlackWorkspaceMember) => {
      onPick(m);
      setQuery("");
      setOpen(false);
    },
    [onPick],
  );

  if (slackDirectoryEmpty) {
    return (
      <p className="mt-3 text-sm leading-snug text-zinc-500">No Slack members available in the directory yet.</p>
    );
  }

  if (candidates.length === 0) {
    return (
      <p className="mt-3 text-sm leading-snug text-zinc-500">
        Everyone from your Slack directory is already in this group.
      </p>
    );
  }

  return (
    <div ref={rootRef} className="relative mt-3">
      <label htmlFor={inputId} className="sr-only">
        Search Slack to add people
      </label>
      <div className="relative">
        <input
          id={inputId}
          type="search"
          autoComplete="off"
          spellCheck={false}
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setHighlight((h) => Math.min(h + 1, Math.max(0, filtered.length - 1)));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHighlight((h) => Math.max(h - 1, 0));
            } else if (e.key === "Enter" && open && filtered.length > 0) {
              e.preventDefault();
              const m = filtered[highlight];
              if (m) {
                pick(m);
              }
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          className={`${inputBase} pr-10`}
          aria-controls={open && filtered.length > 0 ? listboxId : undefined}
          aria-expanded={open && filtered.length > 0}
          aria-autocomplete="list"
          role="combobox"
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400">
          <SearchIcon />
        </span>
      </div>
      {open && filtered.length > 0 ? (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute left-0 right-0 top-full z-20 mt-1 max-h-[13rem] overflow-y-auto rounded-xl border border-zinc-200 bg-white py-1 shadow-[0_16px_40px_-16px_rgba(15,23,42,0.18)] ring-1 ring-zinc-950/[0.04]"
        >
          {filtered.map((u, i) => {
            const secondary = slackMemberPickerSecondary(u);
            const active = i === highlight;
            return (
              <li key={u.id} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors sm:text-base ${
                    active ? "bg-zinc-100" : "hover:bg-zinc-50"
                  }`}
                  onMouseEnter={() => setHighlight(i)}
                  onMouseDown={(ev) => ev.preventDefault()}
                  onClick={() => pick(u)}
                >
                  <SlackUserAvatar imageUrl={u.image_48} name={slackMemberPickerPrimary(u)} size="md" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-[#0F0F12]">
                      {slackMemberPickerPrimary(u)}
                    </span>
                    {secondary ? (
                      <span className="block truncate text-xs text-zinc-500 sm:text-sm">{secondary}</span>
                    ) : null}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {open && query.trim() && filtered.length === 0 ? (
        <div className="absolute left-0 right-0 top-full z-20 mt-1 rounded-xl border border-zinc-200 bg-white px-3 py-2.5 text-sm text-zinc-500 shadow-md">
          No matches in your Slack directory.
        </div>
      ) : null}
    </div>
  );
}

function ChevronDownIcon({ className, open }: { className?: string; open?: boolean }) {
  return (
    <svg
      className={`${className ?? ""} transition-transform duration-200 ${open ? "rotate-180" : ""}`.trim()}
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="m6 9 6 6 6-6"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
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
  const rosterSanitized = useMemo(() => rosterWithoutSlackbot(slackRoster), [slackRoster]);

  const rosterById = useMemo(() => {
    const m = new Map<string, SlackWorkspaceMember>();
    for (const u of slackRoster) {
      m.set(u.id, u);
    }
    return m;
  }, [slackRoster]);

  const [teams, setTeams] = useState<ManagerTeam[]>([]);
  const [dirty, setDirty] = useState(false);
  /** Row ids with the detailed form expanded (Edit / new row via Add manager). */
  const [editingTeamIds, setEditingTeamIds] = useState<Set<string>>(() => new Set());
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);
  const saveDialogTitleId = useId();
  const teamMenuBaseId = useId();
  const [teamActionsMenuId, setTeamActionsMenuId] = useState<string | null>(null);
  const teamActionsMenuRef = useRef<HTMLDivElement | null>(null);
  const [saveValidationError, setSaveValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!ob.data?.answers) {
      return;
    }
    const next = defaultTeamsFromOnboarding(ob.data.answers);
    setTeams(next);
    setEditingTeamIds(new Set());
    setDirty(false);
  }, [ob.data?.id, ob.data?.version, ob.data?.answers]);

  const saveMut = useMutation({
    mutationFn: async () => {
      const apiTeams = teamsForOnboardingApi(teams);
      await patchOnboarding(apiBase, {
        answers: {
          workspace_manager_teams: { teams: apiTeams },
          vector_manager_access_mode: legacyVectorManagerAccessModeFromTeams(teams),
          vector_company_wide_users: legacyVectorCompanyWideUsersFromTeams(teams),
        },
      });
    },
    onSuccess: async () => {
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: ["onboarding", apiBase, tenantId] });
      }
      setDirty(false);
      setSaveConfirmOpen(false);
      setEditingTeamIds(new Set());
    },
  });

  useEffect(() => {
    if (!saveConfirmOpen) {
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !saveMut.isPending) {
        setSaveConfirmOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [saveConfirmOpen, saveMut.isPending]);

  useEffect(() => {
    if (teamActionsMenuId === null) {
      return;
    }
    const onDocPointer = (e: MouseEvent | TouchEvent) => {
      const t = e.target as Node;
      const moreEl = teamActionsMenuRef.current;
      if (moreEl && !moreEl.contains(t)) {
        setTeamActionsMenuId(null);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setTeamActionsMenuId(null);
      }
    };
    document.addEventListener("mousedown", onDocPointer);
    document.addEventListener("touchstart", onDocPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocPointer);
      document.removeEventListener("touchstart", onDocPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [teamActionsMenuId]);

  useEffect(() => {
    setSaveValidationError(null);
  }, [teams]);

  const addTeam = useCallback(() => {
    const id = crypto.randomUUID();
    setTeams((prev) => [
      ...prev,
      { id, name: "", members: [], manager_slack_user_id: null, access_scope: "scoped" },
    ]);
    setEditingTeamIds((prev) => new Set(prev).add(id));
    setDirty(true);
  }, []);

  const removeTeam = useCallback((id: string) => {
    setTeams((prev) => prev.filter((t) => t.id !== id));
    setEditingTeamIds((prev) => {
      const n = new Set(prev);
      n.delete(id);
      return n;
    });
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
        const collab = {
          slack_user_id: member.id,
          username: member.username,
          label: member.label,
        };
        if (t.access_scope === "scoped") {
          if (t.manager_slack_user_id == null) {
            return t;
          }
          if (member.id === t.manager_slack_user_id) {
            return t;
          }
          return { ...t, members: [...t.members, collab] };
        }
        if (t.access_scope === "all" && t.members.length >= 1) {
          const nextMembers = [...t.members, collab];
          return {
            ...t,
            access_scope: "scoped",
            members: nextMembers,
            manager_slack_user_id: t.manager_slack_user_id ?? member.id,
          };
        }
        const wasEmpty = t.members.length === 0;
        const nextMembers = [...t.members, collab];
        return {
          ...t,
          members: nextMembers,
          manager_slack_user_id:
            wasEmpty && t.manager_slack_user_id == null ? member.id : t.manager_slack_user_id,
        };
      }),
    );
    setDirty(true);
  }, []);

  const assignManagerFromRoster = useCallback(
    (teamId: string, member: SlackWorkspaceMember): boolean => {
      if (teams.some((t) => t.id !== teamId && t.manager_slack_user_id === member.id)) {
        setSaveValidationError("That Slack user is already the manager on another row.");
        return false;
      }
      setSaveValidationError(null);
      const collab: SlackCollaboratorMember = {
        slack_user_id: member.id,
        username: member.username,
        label: member.label,
      };
      setTeams((prev) =>
        prev.map((t) => {
          if (t.id !== teamId) {
            return t;
          }
          if (t.access_scope === "all") {
            return {
              ...t,
              manager_slack_user_id: member.id,
              members: [collab],
            };
          }
          const oldMgr = t.manager_slack_user_id;
          const rest = t.members.filter(
            (m) =>
              (oldMgr == null || m.slack_user_id !== oldMgr) && m.slack_user_id !== member.id,
          );
          return {
            ...t,
            manager_slack_user_id: member.id,
            members: [collab, ...rest],
          };
        }),
      );
      setDirty(true);
      return true;
    },
    [teams],
  );

  const setTeamAccessScope = useCallback((teamId: string, scope: ManagerAccessScope) => {
    setTeams((prev) =>
      prev.map((t) => {
        if (t.id !== teamId) {
          return t;
        }
        if (scope === "all") {
          const mgr = t.manager_slack_user_id;
          const row = mgr ? t.members.find((m) => m.slack_user_id === mgr) : undefined;
          return {
            ...t,
            access_scope: "all",
            members: row ? [row] : [],
            manager_slack_user_id: row ? mgr : null,
          };
        }
        return { ...t, access_scope: "scoped" };
      }),
    );
    setDirty(true);
  }, []);

  const removeMember = useCallback((teamId: string, slackUserId: string) => {
    let expandEditorFor: string | null = null;
    setTeams((prev) => {
      const next = prev.map((t) => {
        if (t.id !== teamId) {
          return t;
        }
        const nextMembers = t.members.filter((m) => m.slack_user_id !== slackUserId);
        const clearMgr = t.manager_slack_user_id === slackUserId;
        const nextMgr = clearMgr ? null : t.manager_slack_user_id;
        if (clearMgr && nextMembers.length > 0) {
          expandEditorFor = teamId;
        }
        return {
          ...t,
          members: nextMembers,
          manager_slack_user_id: nextMgr,
        };
      });
      return next;
    });
    setDirty(true);
    const teamIdToExpand = expandEditorFor;
    if (teamIdToExpand) {
      setEditingTeamIds((prev) => new Set(prev).add(teamIdToExpand));
    }
  }, []);

  if (ob.isPending || !ob.data) {
    return (
      <div className="flex min-h-[120px] items-center justify-center">
        <div className={workspaceSpinnerMd} aria-hidden />
      </div>
    );
  }

  if (!ob.data.slack_connected) {
    return (
      <div className={`${workspaceFlatPanel} p-4 sm:p-5`}>
        <p className={`${marketingBody} text-base text-zinc-600`}>
          Connect Slack from <span className="font-medium text-zinc-800">Signals</span> to load your roster and assign
          Vector users on this page.
        </p>
      </div>
    );
  }

  const saveBtnClass = dirty
    ? workspacePrimaryButtonBase
    : "rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-base font-semibold text-zinc-900 enabled:hover:bg-zinc-50 disabled:opacity-40";

  /** One strong primary per toolbar: save when dirty, otherwise “Add access group”. */
  const addTeamBtnClass = dirty ? workspaceSecondaryButtonBase : workspacePrimaryButtonToolbar;

  const saveValidationBlock = validateWorkspaceAccessSave(teams);
  const canSaveChanges = Boolean(dirty && !saveMut.isPending && saveValidationBlock === null);
  /** New rows only after every existing row has a manager (empty list is allowed so the first row can be added). */
  const canAddManagerRow =
    !saveMut.isPending && teams.every((t) => t.manager_slack_user_id != null);

  return (
    <div className="space-y-4">
      {slackMembers.isError ? (
        <p className="rounded-lg border-l-4 border-amber-400 bg-amber-50 py-2.5 pl-3 pr-3 text-base leading-snug text-amber-950">
          Could not load Slack members. Check the Slack connection and try again.
        </p>
      ) : null}

      <section className={workspaceFlatPanel}>
        <header className="border-b border-zinc-100 bg-zinc-50/60 px-5 py-5 sm:px-8 sm:py-6">
          <h2 className="text-xl font-bold tracking-tight text-zinc-900">Workspace access</h2>
        </header>

        <div className="space-y-8 px-5 py-6 sm:px-8 sm:py-8">
          {saveValidationError ? (
            <p
              className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-base leading-snug text-rose-950"
              role="alert"
            >
              {saveValidationError}
            </p>
          ) : null}

          <div>
            <h3 className="text-base font-semibold text-zinc-900">Managers</h3>
            <p className="mt-1 text-sm leading-relaxed text-zinc-600">
              <span className="font-medium text-zinc-800">All access</span> gives that manager full org context in
              Vector. <span className="font-medium text-zinc-800">Scoped access</span> means they only see data about the
              people you choose for that row.
            </p>

            <div className="mt-6 space-y-6">
              {teams.length === 0 ? (
                <div className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/40 px-4 py-10 text-center sm:px-8">
                  <p className="text-base font-medium text-zinc-800">No managers yet</p>
                  <p className="mt-2 text-sm text-zinc-600">
                    Use <span className="font-medium text-zinc-800">Add manager</span> below, then fill in each row in
                    the table.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-zinc-100">
                  <table className="w-full min-w-0 border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-zinc-200 bg-zinc-50/90 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">
                        <th className="whitespace-nowrap px-4 py-3 sm:px-5">Manager</th>
                        <th className="whitespace-nowrap px-4 py-3 sm:px-5">Access</th>
                        <th className="min-w-[8rem] px-4 py-3 sm:px-5">People in scope</th>
                        <th className="whitespace-nowrap px-4 py-3 text-right sm:px-5">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 bg-white">
                      {teams.map((team) => {
                        const editing = editingTeamIds.has(team.id);
                        const expanded = editing;
                        const mgr = managerMember(team);
                        const others = scopedMembersExcludingManager(team);
                        const peopleSummary =
                          team.access_scope === "all"
                            ? "Full workspace"
                            : others.length === 0
                              ? "Manager only"
                              : others.map((m) => m.label.trim() || m.username).join(", ");
                        const scopeSegment = (scope: ManagerAccessScope, label: string, hint: string) => (
                          <button
                            key={scope}
                            type="button"
                            onClick={() => setTeamAccessScope(team.id, scope)}
                            className={`flex-1 rounded-lg px-3 py-2.5 text-left text-sm font-semibold transition sm:px-4 ${
                              team.access_scope === scope
                                ? "border border-[#E878BE] bg-white text-zinc-900 shadow-sm ring-1 ring-[#E878BE]/25"
                                : "border border-transparent text-zinc-600 hover:bg-white/80"
                            }`}
                          >
                            <span className="block">{label}</span>
                            <span className="mt-0.5 block text-xs font-normal leading-snug text-zinc-500">{hint}</span>
                          </button>
                        );
                        const toggleRowEditor = () => {
                          setEditingTeamIds((prev) => {
                            const n = new Set(prev);
                            if (n.has(team.id)) {
                              n.delete(team.id);
                            } else {
                              n.add(team.id);
                            }
                            return n;
                          });
                        };
                        return (
                          <Fragment key={team.id}>
                            <tr className={expanded ? "bg-zinc-50/90" : "hover:bg-zinc-50/60"}>
                              <td className="max-w-[12rem] px-4 py-3 align-middle sm:max-w-none sm:px-5">
                                {mgr ? (
                                  <div className="flex min-w-0 items-center gap-2">
                                    <SlackUserAvatar
                                      imageUrl={rosterById.get(mgr.slack_user_id)?.image_48 ?? null}
                                      name={mgr.label.trim() || mgr.username}
                                      size="md"
                                    />
                                    <div className="min-w-0">
                                      <p className="truncate font-semibold text-zinc-900">{mgr.label}</p>
                                      <p className="truncate text-xs text-zinc-500">@{mgr.username}</p>
                                    </div>
                                  </div>
                                ) : (
                                  <span className="text-zinc-400">Not set</span>
                                )}
                              </td>
                              <td className="whitespace-nowrap px-4 py-3 align-middle sm:px-5">
                                <span className="text-sm font-medium text-zinc-800">
                                  {team.access_scope === "all" ? "All access" : "Scoped"}
                                </span>
                              </td>
                              <td className="max-w-[14rem] px-4 py-3 align-middle text-zinc-700 sm:max-w-md sm:px-5">
                                <p className="line-clamp-2 text-sm leading-snug" title={peopleSummary}>
                                  {peopleSummary}
                                </p>
                              </td>
                              <td className="px-4 py-3 align-middle sm:px-5">
                                <div className="flex flex-col items-stretch gap-1.5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2">
                                  <div
                                    ref={teamActionsMenuId === team.id ? teamActionsMenuRef : undefined}
                                    className="relative flex justify-end sm:inline-flex"
                                  >
                                    <button
                                      type="button"
                                      className={`${rowCtaQuietClass} flex w-full items-center justify-center gap-1 sm:w-auto`}
                                      aria-expanded={teamActionsMenuId === team.id}
                                      aria-haspopup="menu"
                                      aria-controls={
                                        teamActionsMenuId === team.id ? `${teamMenuBaseId}-menu-${team.id}` : undefined
                                      }
                                      aria-label="More actions"
                                      onClick={() => {
                                        setTeamActionsMenuId((cur) => (cur === team.id ? null : team.id));
                                      }}
                                    >
                                      More
                                      <ChevronDownIcon
                                        className="h-4 w-4 shrink-0 opacity-70"
                                        open={teamActionsMenuId === team.id}
                                      />
                                    </button>
                                    {teamActionsMenuId === team.id ? (
                                      <div
                                        id={`${teamMenuBaseId}-menu-${team.id}`}
                                        role="menu"
                                        aria-label="More actions"
                                        className="absolute right-0 bottom-full z-[80] mb-1.5 min-w-[12rem] rounded-xl border border-zinc-200/90 bg-white py-1 shadow-[0_12px_40px_-12px_rgba(15,23,42,0.2)] ring-1 ring-zinc-950/5"
                                      >
                                        <Link
                                          to={workspaceAccessGroupPath(team.id)}
                                          role="menuitem"
                                          className="flex w-full items-center px-3 py-2.5 text-left text-base font-medium text-zinc-800 no-underline hover:bg-zinc-50"
                                          onClick={() => setTeamActionsMenuId(null)}
                                        >
                                          Manager space
                                        </Link>
                                        <button
                                          type="button"
                                          role="menuitem"
                                          className="flex w-full items-center px-3 py-2.5 text-left text-base font-medium text-zinc-800 hover:bg-zinc-50"
                                          onClick={() => {
                                            setTeamActionsMenuId(null);
                                            toggleRowEditor();
                                          }}
                                        >
                                          {editing ? "Close editor" : "Edit"}
                                        </button>
                                        <button
                                          type="button"
                                          role="menuitem"
                                          className="flex w-full items-center px-3 py-2.5 text-left text-base font-medium text-rose-700 hover:bg-rose-50"
                                          onClick={() => {
                                            setTeamActionsMenuId(null);
                                            removeTeam(team.id);
                                          }}
                                        >
                                          Remove manager
                                        </button>
                                      </div>
                                    ) : null}
                                  </div>
                                </div>
                              </td>
                            </tr>
                            {expanded ? (
                              <tr className="bg-zinc-50/80">
                                <td colSpan={4} className="px-4 py-5 sm:px-6">
                                  <div className="mx-auto max-w-3xl space-y-5">
                                    <div className="rounded-xl border border-zinc-100 bg-white p-4 sm:p-5">
                                      <p className={labelClass}>Pick Manager</p>
                                      {team.manager_slack_user_id ? (
                                        <ul className="mt-2 flex flex-wrap gap-2">
                                          {(() => {
                                            const m = team.members.find(
                                              (x) => x.slack_user_id === team.manager_slack_user_id,
                                            );
                                            if (!m) {
                                              return null;
                                            }
                                            const rosterRow = rosterById.get(m.slack_user_id);
                                            const display = m.label.trim() || m.username;
                                            return (
                                              <li
                                                key={m.slack_user_id}
                                                className="inline-flex max-w-full items-center gap-2 rounded-lg bg-zinc-100 py-1.5 pl-1.5 pr-1.5 text-zinc-900"
                                              >
                                                <SlackUserAvatar
                                                  imageUrl={rosterRow?.image_48 ?? null}
                                                  name={display}
                                                  size="md"
                                                />
                                                <span className="min-w-0 truncate text-base font-medium text-[#0F0F12]">
                                                  {m.label}
                                                </span>
                                                <span className="shrink-0 text-sm text-zinc-500">@{m.username}</span>
                                                <span className="shrink-0 rounded-sm bg-zinc-200/55 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600 sm:text-[11px]">
                                                  Manager
                                                </span>
                                              </li>
                                            );
                                          })()}
                                        </ul>
                                      ) : (
                                        <p className="mt-2 text-base text-zinc-500">Pick who leads this row.</p>
                                      )}
                                      {slackMembers.isPending ? (
                                        <p className="mt-3 text-base text-zinc-500">Loading Slack directory…</p>
                                      ) : (
                                        <div className="mt-3">
                                          <SlackMemberCombobox
                                            candidates={slackCandidatesForManagerPicker(
                                              rosterSanitized,
                                              teams,
                                              team.id,
                                              team.manager_slack_user_id,
                                            )}
                                            slackDirectoryEmpty={rosterSanitized.length === 0}
                                            onPick={(m) => assignManagerFromRoster(team.id, m)}
                                            placeholder="Search Slack to choose or change manager…"
                                          />
                                        </div>
                                      )}
                                    </div>
                                    <div>
                                      <p className={labelClass}>Scope</p>
                                      <div
                                        className="mt-2 flex flex-col gap-2 rounded-xl border border-zinc-200 bg-white p-1.5 sm:flex-row"
                                        role="group"
                                        aria-label="Scope"
                                      >
                                        {scopeSegment("all", "All access", "Full workspace context for this manager.")}
                                        {scopeSegment(
                                          "scoped",
                                          "Scoped",
                                          "This manager only sees data about the people you select for this row.",
                                        )}
                                      </div>
                                    </div>
                                    <div>
                                      <label htmlFor={`team-name-${team.id}`} className={labelClass}>
                                        Manager&apos;s team / scope <span className="font-normal text-zinc-400">(optional)</span>
                                      </label>
                                      <input
                                        id={`team-name-${team.id}`}
                                        type="text"
                                        value={team.name}
                                        onChange={(e) => updateTeamName(team.id, e.target.value)}
                                        placeholder="e.g. Design leadership"
                                        className={`${inputBase} mt-1.5`}
                                      />
                                    </div>
                                    {team.access_scope === "scoped" ? (
                                      <div>
                                        <p className={labelClass}>Team members in scope</p>
                                        <p className="mt-1 text-sm leading-relaxed text-zinc-500">
                                          Whose data they can access besides their own.
                                        </p>
                                        {team.manager_slack_user_id == null ? (
                                          <p className="mt-2 text-base text-zinc-500">
                                            Choose a manager above before adding other people.
                                          </p>
                                        ) : scopedMembersExcludingManager(team).length === 0 ? null : (
                                          <ul className="mt-2 flex flex-wrap gap-2">
                                            {scopedMembersExcludingManager(team).map((m) => {
                                              const rosterRow = rosterById.get(m.slack_user_id);
                                              const avatarUrl = rosterRow?.image_48 ?? null;
                                              const display = m.label.trim() || m.username;
                                              return (
                                                <li
                                                  key={m.slack_user_id}
                                                  className="inline-flex max-w-full items-center gap-2 rounded-lg bg-zinc-100 py-1.5 pl-1.5 pr-1.5 text-zinc-900"
                                                >
                                                  <SlackUserAvatar imageUrl={avatarUrl} name={display} size="md" />
                                                  <span className="min-w-0 truncate text-base font-medium text-[#0F0F12]">
                                                    {m.label}
                                                  </span>
                                                  <span className="shrink-0 text-sm text-zinc-500">@{m.username}</span>
                                                  <button
                                                    type="button"
                                                    onClick={() => removeMember(team.id, m.slack_user_id)}
                                                    className="flex h-8 min-w-8 shrink-0 items-center justify-center rounded text-lg leading-none text-zinc-400 hover:bg-white/85 hover:text-rose-700"
                                                    aria-label={`Remove ${m.label} from scope`}
                                                  >
                                                    ×
                                                  </button>
                                                </li>
                                              );
                                            })}
                                          </ul>
                                        )}
                                        {slackMembers.isPending ? (
                                          <p className="mt-3 text-base text-zinc-500">Loading Slack directory…</p>
                                        ) : team.manager_slack_user_id == null ? null : (
                                          <div className="mt-3">
                                            <SlackMemberCombobox
                                              candidates={slackCandidatesForScopeMembers(rosterSanitized, team)}
                                              slackDirectoryEmpty={rosterSanitized.length === 0}
                                              onPick={(m) => addMemberFromRoster(team.id, m)}
                                              placeholder="Search Slack to add people in scope…"
                                            />
                                          </div>
                                        )}
                                      </div>
                                    ) : null}
                                  </div>
                                </td>
                              </tr>
                            ) : null}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-4 border-t border-zinc-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
              <p
                className={`text-sm leading-snug sm:max-w-md ${dirty ? "font-medium text-amber-900" : "text-zinc-500"}`}
                role={dirty ? "status" : undefined}
              >
                {dirty
                  ? "Unsaved changes—save to apply for everyone in this workspace, or refresh to discard."
                  : "Changes are local until you save."}
              </p>
              <div className="flex flex-wrap items-center justify-end gap-2 sm:shrink-0">
                <button
                  type="button"
                  disabled={!canAddManagerRow}
                  title={
                    canAddManagerRow
                      ? undefined
                      : "Choose a Slack manager on each row before adding another."
                  }
                  onClick={addTeam}
                  className={`${addTeamBtnClass} disabled:cursor-not-allowed disabled:opacity-40`}
                >
                  Add manager
                </button>
                <button
                  type="button"
                  disabled={!canSaveChanges}
                  title={
                    canSaveChanges || !dirty
                      ? undefined
                      : saveValidationBlock ?? "Fix the manager list before saving."
                  }
                  onClick={() => {
                    if (saveValidationBlock) {
                      setSaveValidationError(saveValidationBlock);
                      return;
                    }
                    setSaveValidationError(null);
                    setSaveConfirmOpen(true);
                  }}
                  className={`${saveBtnClass} disabled:cursor-not-allowed disabled:opacity-40`}
                >
                  {saveMut.isPending ? "Saving…" : "Save changes"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {saveConfirmOpen ? (
        <div className="fixed inset-0 z-[100]" role="presentation">
          <button
            type="button"
            className="absolute inset-0 z-0 bg-zinc-900/40 backdrop-blur-[1px]"
            aria-label="Close dialog"
            onClick={() => !saveMut.isPending && setSaveConfirmOpen(false)}
          />
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby={saveDialogTitleId}
              className="pointer-events-auto w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.35)]"
            >
              <h2 id={saveDialogTitleId} className="text-lg font-semibold tracking-tight text-[#0F0F12]">
                Save roster?
              </h2>
              <p className="mt-2 text-base leading-relaxed text-zinc-600">
                This saves each manager&apos;s access type (all vs scoped) and Slack roster for{" "}
                <span className="font-medium text-zinc-800">everyone</span> in this workspace.
              </p>
              <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
                <button
                  type="button"
                  disabled={saveMut.isPending}
                  onClick={() => setSaveConfirmOpen(false)}
                  className="rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-base font-semibold text-zinc-800 transition hover:bg-zinc-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={saveMut.isPending}
                  onClick={() => {
                    const err = validateWorkspaceAccessSave(teams);
                    if (err) {
                      setSaveValidationError(err);
                      setSaveConfirmOpen(false);
                      return;
                    }
                    setSaveValidationError(null);
                    saveMut.mutate();
                  }}
                  className={`${workspacePrimaryButtonBase} disabled:opacity-50`}
                >
                  {saveMut.isPending ? "Saving…" : "Yes, save"}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
