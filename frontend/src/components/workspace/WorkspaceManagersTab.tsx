import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
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
import { defaultTeamsFromOnboarding, type ManagerTeam } from "../../lib/workspaceManagerTeams";
import SlackUserAvatar from "./SlackUserAvatar";

export type { ManagerTeam };

/** Renders manager first when set, then the rest in their existing order. */
function membersOrderedWithManagerFirst(team: ManagerTeam): SlackCollaboratorMember[] {
  const mgrId = team.manager_slack_user_id;
  if (!mgrId) {
    return team.members;
  }
  const manager = team.members.find((m) => m.slack_user_id === mgrId);
  if (!manager) {
    return team.members;
  }
  const others = team.members.filter((m) => m.slack_user_id !== mgrId);
  return [manager, ...others];
}

/** Name + at least one member + manager chosen from members (same rules as save validation). */
function isTeamStructurallyComplete(team: ManagerTeam): boolean {
  if (!team.name.trim()) {
    return false;
  }
  if (team.members.length === 0) {
    return false;
  }
  return (
    team.manager_slack_user_id != null &&
    team.members.some((m) => m.slack_user_id === team.manager_slack_user_id)
  );
}

/** Non-null when teams cannot be saved yet. */
function validateTeamsForSave(teams: ManagerTeam[]): string | null {
  for (const t of teams) {
    if (!t.name.trim()) {
      return "Every team needs a name before you can save.";
    }
  }
  for (const t of teams) {
    if (t.members.length === 0) {
      return "Each team needs at least one person from Slack before you can save.";
    }
    const mgrOk =
      t.manager_slack_user_id != null &&
      t.members.some((m) => m.slack_user_id === t.manager_slack_user_id);
    if (!mgrOk) {
      return "Each team needs a manager chosen from its members. Use Team actions → Change team manager if needed.";
    }
  }
  return null;
}

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
}: {
  candidates: SlackWorkspaceMember[];
  onPick: (member: SlackWorkspaceMember) => void;
  /** True when the roster loaded and has zero people (different copy than “all on team”). */
  slackDirectoryEmpty: boolean;
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
        Everyone from your Slack directory is already on this team.
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
          placeholder="Search Slack to add people…"
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

function ManagerPickerModal({
  team,
  rosterById,
  onClose,
  onConfirm,
}: {
  team: ManagerTeam;
  rosterById: Map<string, SlackWorkspaceMember>;
  onClose: () => void;
  onConfirm: (slackUserId: string) => void;
}) {
  const titleId = useId();
  const initial =
    team.members.find((m) => m.slack_user_id === team.manager_slack_user_id)?.slack_user_id ??
    team.members[0]?.slack_user_id ??
    "";
  const [choice, setChoice] = useState(initial);

  useEffect(() => {
    setChoice(
      team.members.find((m) => m.slack_user_id === team.manager_slack_user_id)?.slack_user_id ??
        team.members[0]?.slack_user_id ??
        "",
    );
  }, [team.id, team.manager_slack_user_id, team.members]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const canSave = Boolean(choice && team.members.some((m) => m.slack_user_id === choice));

  return (
    <div className="fixed inset-0 z-[100]" role="presentation">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-zinc-900/40 backdrop-blur-[1px]"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="pointer-events-auto w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.35)]"
        >
          <h2 id={titleId} className="text-lg font-semibold tracking-tight text-[#0F0F12]">
            Choose team manager
          </h2>
          <p className="mt-2 text-base leading-relaxed text-zinc-600">
            Pick who leads this team. They stay listed first with the Manager badge.
          </p>
          <ul className="mt-4 max-h-[min(50vh,20rem)] space-y-2 overflow-y-auto">
            {team.members.map((m) => {
              const row = rosterById.get(m.slack_user_id);
              const display = m.label.trim() || m.username;
              const sel = choice === m.slack_user_id;
              return (
                <li key={m.slack_user_id}>
                  <label
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors ${
                      sel ? "border-zinc-400 bg-zinc-100" : "border-zinc-200 hover:bg-zinc-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`mgr-${team.id}`}
                      className="h-4 w-4 shrink-0 accent-zinc-700"
                      checked={sel}
                      onChange={() => setChoice(m.slack_user_id)}
                    />
                    <SlackUserAvatar imageUrl={row?.image_48 ?? null} name={display} size="md" />
                    <span className="min-w-0 flex-1 text-base font-medium text-[#0F0F12]">{m.label}</span>
                    <span className="shrink-0 text-sm text-zinc-500">@{m.username}</span>
                  </label>
                </li>
              );
            })}
          </ul>
          <div className="mt-6 flex flex-wrap justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-base font-semibold text-zinc-800 hover:bg-zinc-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!canSave}
              onClick={() => {
                if (canSave) {
                  onConfirm(choice);
                }
              }}
              className={workspacePrimaryButtonBase}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
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
  /** Teams showing name field + Slack picker; incomplete teams always behave as editing. */
  const [editingTeamIds, setEditingTeamIds] = useState<Set<string>>(() => new Set());
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);
  const saveDialogTitleId = useId();
  const teamMenuBaseId = useId();
  const [teamActionsMenuId, setTeamActionsMenuId] = useState<string | null>(null);
  const teamActionsMenuRef = useRef<HTMLDivElement | null>(null);
  const [managerModalTeamId, setManagerModalTeamId] = useState<string | null>(null);
  const [saveValidationError, setSaveValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!ob.data?.answers) {
      return;
    }
    const next = defaultTeamsFromOnboarding(ob.data.answers);
    setTeams(next);
    setDirty(false);
    setEditingTeamIds(new Set(next.filter((t) => !isTeamStructurallyComplete(t)).map((t) => t.id)));
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
      const el = teamActionsMenuRef.current;
      if (el && !el.contains(e.target as Node)) {
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

  useEffect(() => {
    if (!managerModalTeamId) {
      return;
    }
    const t = teams.find((x) => x.id === managerModalTeamId);
    if (!t || t.members.length === 0) {
      setManagerModalTeamId(null);
    }
  }, [managerModalTeamId, teams]);

  const addTeam = useCallback(() => {
    const id = crypto.randomUUID();
    setTeams((prev) => [...prev, { id, name: "", members: [], manager_slack_user_id: null }]);
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
        const wasEmpty = t.members.length === 0;
        const nextMembers = [
          ...t.members,
          {
            slack_user_id: member.id,
            username: member.username,
            label: member.label,
          },
        ];
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

  const removeMember = useCallback((teamId: string, slackUserId: string) => {
    let openManagerModalFor: string | null = null;
    setTeams((prev) => {
      const next = prev.map((t) => {
        if (t.id !== teamId) {
          return t;
        }
        const nextMembers = t.members.filter((m) => m.slack_user_id !== slackUserId);
        const clearMgr = t.manager_slack_user_id === slackUserId;
        const nextMgr = clearMgr ? null : t.manager_slack_user_id;
        if (clearMgr && nextMembers.length > 0) {
          openManagerModalFor = teamId;
        }
        return {
          ...t,
          members: nextMembers,
          manager_slack_user_id: nextMgr,
        };
      });
      const updated = next.find((t) => t.id === teamId);
      if (updated && !isTeamStructurallyComplete(updated)) {
        queueMicrotask(() => setEditingTeamIds((e) => new Set(e).add(teamId)));
      }
      return next;
    });
    setDirty(true);
    if (openManagerModalFor) {
      setManagerModalTeamId(openManagerModalFor);
    }
  }, []);

  const setTeamManager = useCallback((teamId: string, slackUserId: string | null) => {
    setTeams((prev) =>
      prev.map((t) => {
        if (t.id !== teamId) {
          return t;
        }
        if (slackUserId === null) {
          return { ...t, manager_slack_user_id: null };
        }
        if (!t.members.some((m) => m.slack_user_id === slackUserId)) {
          return t;
        }
        return { ...t, manager_slack_user_id: slackUserId };
      }),
    );
    setDirty(true);
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
          people to teams.
        </p>
      </div>
    );
  }

  const saveBtnClass = dirty
    ? workspacePrimaryButtonBase
    : "rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-base font-semibold text-zinc-900 enabled:hover:bg-zinc-50 disabled:opacity-40";

  /** One strong primary per toolbar: save when dirty, otherwise “Add team”. */
  const addTeamBtnClass = dirty ? workspaceSecondaryButtonBase : workspacePrimaryButtonToolbar;

  return (
    <div className="space-y-4">
      {slackMembers.isError ? (
        <p className="rounded-lg border-l-4 border-amber-400 bg-amber-50 py-2.5 pl-3 pr-3 text-base leading-snug text-amber-950">
          Could not load Slack members. Check the Slack connection and try again.
        </p>
      ) : null}

      {dirty ? (
        <p
          className="rounded-lg border border-amber-200/90 bg-amber-50 px-4 py-3 text-base leading-relaxed text-amber-950"
          role="status"
        >
          You have unsaved changes. Click <span className="font-semibold">Save changes</span> to update teams for
          everyone in this workspace—or refresh to discard edits.
        </p>
      ) : null}

      {saveValidationError ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-base leading-snug text-rose-950" role="alert">
          {saveValidationError}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="min-w-0 text-xl font-bold tracking-tight text-zinc-900">Teams</h2>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <button type="button" onClick={addTeam} className={addTeamBtnClass}>
            Add team
          </button>
          <button
            type="button"
            disabled={!dirty || saveMut.isPending}
            onClick={() => {
              const err = validateTeamsForSave(teams);
              if (err) {
                setSaveValidationError(err);
                return;
              }
              setSaveValidationError(null);
              setSaveConfirmOpen(true);
            }}
            className={saveBtnClass}
          >
            {saveMut.isPending ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>

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
              Save team changes?
            </h2>
            <p className="mt-2 text-base leading-relaxed text-zinc-600">
              This updates team names, managers, and members for <span className="font-medium text-zinc-800">everyone</span>{" "}
              in this workspace.
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
                  const err = validateTeamsForSave(teams);
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

      {teams.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 px-4 py-8 text-center text-base text-zinc-600">
          No teams yet. Add one, then pick people from your Slack directory.
        </p>
      ) : (
        <ul className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {teams.map((team) => {
            const complete = isTeamStructurallyComplete(team);
            const editing = editingTeamIds.has(team.id);
            const showEditor = !complete || editing;
            return (
              <li
                key={team.id}
                className={`${workspaceFlatPanel} relative flex flex-col px-5 pb-5 pt-3 sm:px-6 sm:pb-6 sm:pt-3`}
              >
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    {showEditor ? (
                      <>
                        <label htmlFor={`team-name-${team.id}`} className="sr-only">
                          Team name
                        </label>
                        <input
                          id={`team-name-${team.id}`}
                          type="text"
                          value={team.name}
                          onChange={(e) => updateTeamName(team.id, e.target.value)}
                          placeholder="Team name"
                          className={inputBase}
                        />
                      </>
                    ) : (
                      <h3 className="truncate pt-1.5 text-lg font-semibold tracking-tight text-zinc-900">
                        {team.name.trim()}
                      </h3>
                    )}
                  </div>
                  <div
                    ref={teamActionsMenuId === team.id ? teamActionsMenuRef : undefined}
                    className="relative z-20 shrink-0"
                  >
                    <button
                      type="button"
                      className="flex h-10 w-10 items-center justify-center rounded-lg text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-400"
                      aria-expanded={teamActionsMenuId === team.id}
                      aria-haspopup="menu"
                      aria-controls={
                        teamActionsMenuId === team.id ? `${teamMenuBaseId}-menu-${team.id}` : undefined
                      }
                      aria-label="Team actions"
                      onClick={() =>
                        setTeamActionsMenuId((cur) => (cur === team.id ? null : team.id))
                      }
                    >
                      <ChevronDownIcon open={teamActionsMenuId === team.id} />
                    </button>
                    {teamActionsMenuId === team.id ? (
                      <div
                        id={`${teamMenuBaseId}-menu-${team.id}`}
                        role="menu"
                        aria-label="Team actions"
                        className="absolute right-0 top-full z-30 mt-1.5 min-w-[14rem] rounded-xl border border-zinc-200/90 bg-white py-1 shadow-[0_12px_40px_-12px_rgba(15,23,42,0.2)] ring-1 ring-zinc-950/5"
                      >
                        <Link
                          to={`/app/teams/${team.id}`}
                          role="menuitem"
                          className="flex w-full items-center px-3 py-2.5 text-left text-base font-medium text-zinc-800 no-underline hover:bg-zinc-50"
                          onClick={() => setTeamActionsMenuId(null)}
                        >
                          Team space
                        </Link>
                        {!showEditor ? (
                          <button
                            type="button"
                            role="menuitem"
                            className="flex w-full items-center px-3 py-2.5 text-left text-base font-medium text-zinc-800 hover:bg-zinc-50"
                            onClick={() => {
                              setTeamActionsMenuId(null);
                              setEditingTeamIds((prev) => new Set(prev).add(team.id));
                            }}
                          >
                            Edit team
                          </button>
                        ) : null}
                        <button
                          type="button"
                          role="menuitem"
                          disabled={team.members.length === 0}
                          title={team.members.length === 0 ? "Add at least one person from Slack first" : undefined}
                          className="flex w-full items-center px-3 py-2.5 text-left text-base font-medium text-zinc-800 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
                          onClick={() => {
                            if (team.members.length === 0) {
                              return;
                            }
                            setTeamActionsMenuId(null);
                            setManagerModalTeamId(team.id);
                          }}
                        >
                          Change team manager
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
                          Remove team
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="mt-4">
                  <p className={labelClass}>Members</p>
                  {team.members.length === 0 ? (
                    <p className="mt-2 text-base text-zinc-500">None yet.</p>
                  ) : (
                    <ul className="mt-2 flex flex-wrap gap-2">
                      {membersOrderedWithManagerFirst(team).map((m) => {
                        const rosterRow = rosterById.get(m.slack_user_id);
                        const avatarUrl = rosterRow?.image_48 ?? null;
                        const display = m.label.trim() || m.username;
                        const isManager =
                          team.manager_slack_user_id !== null &&
                          m.slack_user_id === team.manager_slack_user_id;
                        return (
                          <li
                            key={m.slack_user_id}
                            className="inline-flex max-w-full items-center gap-2 rounded-lg bg-zinc-100 py-1.5 pl-1.5 pr-1.5 text-zinc-900"
                          >
                            <SlackUserAvatar imageUrl={avatarUrl} name={display} size="md" />
                            <span className="min-w-0 truncate text-base font-medium text-[#0F0F12]">{m.label}</span>
                            <span className="shrink-0 text-sm text-zinc-500">@{m.username}</span>
                            {isManager ? (
                              <span className="shrink-0 rounded-sm bg-zinc-200/55 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600 sm:text-[11px]">
                                Manager
                              </span>
                            ) : null}
                            {showEditor ? (
                              <button
                                type="button"
                                onClick={() => removeMember(team.id, m.slack_user_id)}
                                className="flex h-8 min-w-8 shrink-0 items-center justify-center rounded text-lg leading-none text-zinc-400 hover:bg-white/85 hover:text-rose-700"
                                aria-label={`Remove ${m.label} from team`}
                              >
                                ×
                              </button>
                            ) : null}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                {showEditor ? (
                  slackMembers.isPending ? (
                    <p className="mt-3 text-base text-zinc-500">Loading Slack directory…</p>
                  ) : (
                    <SlackMemberCombobox
                      candidates={rosterSanitized.filter(
                        (u) => !team.members.some((m) => m.slack_user_id === u.id),
                      )}
                      slackDirectoryEmpty={rosterSanitized.length === 0}
                      onPick={(m) => addMemberFromRoster(team.id, m)}
                    />
                  )
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {managerModalTeamId
        ? (() => {
            const tm = teams.find((t) => t.id === managerModalTeamId);
            if (!tm || tm.members.length === 0) {
              return null;
            }
            return (
              <ManagerPickerModal
                team={tm}
                rosterById={rosterById}
                onClose={() => setManagerModalTeamId(null)}
                onConfirm={(id) => {
                  setTeamManager(tm.id, id);
                  setManagerModalTeamId(null);
                }}
              />
            );
          })()
        : null}
    </div>
  );
}
