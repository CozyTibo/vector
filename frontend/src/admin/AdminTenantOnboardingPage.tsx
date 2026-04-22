import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { AdminOnboardingStyleThread, adminOnboardingRowsToChatMessages } from "./adminChatTranscript";
import { CollapsibleDebug, OperatorIntro, OperatorSection } from "./ui/OperatorSections";

type ChatMsg = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

type SlackStakeholdersSnap = {
  raw_text: string | null;
  slack_user_ids: string[];
};

type OnboardingSnap = {
  status: string;
  current_step: string;
  started_at: string | null;
  completed_at: string | null;
  abandoned_at: string | null;
  profile_phase: string | null;
  /** Remaining in-product OAuth queue from answers_json (Linear → GitHub → Slack). */
  connect_queue: string[];
  connect_plan: string[];
  tools_interest: string[];
  company_domain: string | null;
  company_website: string | null;
  company_size: string | null;
  user_role: string | null;
  tools_engineering: string[];
  tools_pm: string[];
  tools_communication: string[];
  tools_calls?: string[];
  tools_calendars?: string[];
  tools_docs: string[];
  tools_stack: Record<string, unknown> | null;
  slack_stakeholders: SlackStakeholdersSnap | null;
  chat_messages: ChatMsg[];
};

type TenantDetail = {
  id: string;
  company_name: string;
  member_full_name: string | null;
  member_email: string | null;
  onboarding: OnboardingSnap | null;
  connected_connectors: string[];
};

type AdminToolOptionItem = { id: string; label: string };

type AdminOnboardingOptions = {
  profile_roles: string[];
  tools_by_category: Record<string, AdminToolOptionItem[]>;
};

type CollectedPatch = Record<string, string | string[] | null>;

function splitCsv(s: string): string[] {
  return s
    .split(/[,;\n]+/)
    .map((x) => x.trim())
    .filter(Boolean);
}

const collectedSubheadingClass =
  "text-xs font-semibold uppercase tracking-wide text-stone-500 border-b border-stone-200 pb-2";

const collectedDlClass = "mt-4 grid max-w-2xl grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm";

function flattenToolOptions(opts: AdminOnboardingOptions): AdminToolOptionItem[] {
  const seen = new Set<string>();
  const out: AdminToolOptionItem[] = [];
  for (const group of Object.values(opts.tools_by_category)) {
    for (const it of group) {
      if (seen.has(it.id)) {
        continue;
      }
      seen.add(it.id);
      out.push(it);
    }
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  return out;
}

function CollectedSelectRow({
  label,
  fieldKey,
  patchKey,
  value,
  options,
  emptyLabel,
  commitPatch,
  patchPending,
}: {
  label: string;
  fieldKey: string;
  patchKey: string;
  value: string | null;
  options: string[];
  emptyLabel: string;
  commitPatch: (body: CollectedPatch) => Promise<unknown>;
  patchPending: boolean;
}) {
  const v = value?.trim() ? value : "";
  const orphan = Boolean(v && !options.includes(v));
  return (
    <Fragment key={fieldKey}>
      <dt className="text-stone-500">{label}</dt>
      <dd className="min-w-0 text-stone-900">
        <select
          className="max-w-md rounded-md border border-stone-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-stone-500 focus:outline-none focus:ring-1 focus:ring-stone-400 disabled:opacity-50"
          disabled={patchPending}
          value={v}
          aria-label={label}
          onChange={(ev) => {
            const raw = ev.target.value;
            const next = raw === "" ? null : raw;
            void commitPatch({ [patchKey]: next });
          }}
        >
          <option value="">{emptyLabel}</option>
          {orphan ? (
            <option value={v}>
              {v} (stored — pick a standard value or clear)
            </option>
          ) : null}
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </dd>
    </Fragment>
  );
}

function CollectedToolsMultiRow({
  label,
  fieldKey,
  patchKey,
  items,
  selectedIds,
  commitPatch,
  patchPending,
}: {
  label: string;
  fieldKey: string;
  patchKey: string;
  items: AdminToolOptionItem[];
  selectedIds: string[];
  commitPatch: (body: CollectedPatch) => Promise<unknown>;
  patchPending: boolean;
}) {
  const allowed = useMemo(() => new Set(items.map((i) => i.id)), [items]);
  const unknownStored = selectedIds.filter((id) => !allowed.has(id));
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Set<string>>(() => new Set());
  const skipBlurCancel = useRef(false);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (editing) {
      setDraft(new Set(selectedIds.filter((id) => allowed.has(id))));
    }
  }, [editing, selectedIds, allowed]);

  const toggle = useCallback((id: string) => {
    setDraft((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const display =
    selectedIds.length === 0
      ? "—"
      : selectedIds
          .map((id) => items.find((i) => i.id === id)?.label ?? id)
          .join(", ");

  const cancelEdit = useCallback(() => {
    setEditing(false);
  }, []);

  useEffect(() => {
    if (!editing) {
      return;
    }
    const onDocPointerDown = (e: PointerEvent) => {
      const root = panelRef.current;
      if (!root || root.contains(e.target as Node)) {
        return;
      }
      if (skipBlurCancel.current) {
        skipBlurCancel.current = false;
        return;
      }
      cancelEdit();
    };
    const onDocKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape") {
        return;
      }
      e.preventDefault();
      cancelEdit();
    };
    document.addEventListener("pointerdown", onDocPointerDown, true);
    document.addEventListener("keydown", onDocKeyDown, true);
    return () => {
      document.removeEventListener("pointerdown", onDocPointerDown, true);
      document.removeEventListener("keydown", onDocKeyDown, true);
    };
  }, [editing, cancelEdit]);

  const commit = useCallback(async () => {
    const out = [...draft].sort();
    try {
      await commitPatch({ [patchKey]: out });
    } finally {
      skipBlurCancel.current = false;
    }
    setEditing(false);
  }, [commitPatch, draft, patchKey]);

  const onBlurPanel = useCallback(() => {
    if (skipBlurCancel.current) {
      skipBlurCancel.current = false;
      return;
    }
    cancelEdit();
  }, [cancelEdit]);

  const onKeyDownPanel = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        cancelEdit();
        return;
      }
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        skipBlurCancel.current = true;
        void commit();
      }
    },
    [cancelEdit, commit],
  );

  return (
    <Fragment key={fieldKey}>
      <dt className="text-stone-500">{label}</dt>
      <dd className="min-w-0 text-stone-900">
        {!editing ? (
          <div className="space-y-1">
            <button
              type="button"
              disabled={patchPending}
              className="w-full cursor-pointer rounded border border-transparent px-1 py-0.5 text-left text-sm hover:border-stone-200 hover:bg-stone-50 disabled:cursor-wait disabled:opacity-60"
              onClick={() => setEditing(true)}
            >
              {display}
            </button>
            {unknownStored.length > 0 ? (
              <p className="text-xs text-amber-800">
                Stored ids are not in the product catalog and will be removed if you save this row
                without them: {unknownStored.join(", ")}
              </p>
            ) : null}
          </div>
        ) : (
          <div
            ref={panelRef}
            className="space-y-2 rounded-md border border-stone-200 bg-stone-50/80 p-3"
            tabIndex={-1}
            onBlur={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
                onBlurPanel();
              }
            }}
            onKeyDown={onKeyDownPanel}
          >
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {items.map((it) => (
                <label key={it.id} className="inline-flex cursor-pointer items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    className="rounded border-stone-300"
                    checked={draft.has(it.id)}
                    disabled={patchPending}
                    onChange={() => toggle(it.id)}
                  />
                  <span>{it.label}</span>
                </label>
              ))}
            </div>
            <p className="text-[11px] text-stone-500">
              ⌘ Enter or Ctrl+Enter to save · Esc or click outside to cancel
            </p>
            <button
              type="button"
              disabled={patchPending}
              className="rounded border border-stone-300 bg-white px-2 py-1 text-xs font-medium text-stone-800 hover:bg-stone-100 disabled:opacity-50"
              onClick={() => {
                skipBlurCancel.current = true;
                void commit();
              }}
            >
              Save selection
            </button>
          </div>
        )}
      </dd>
    </Fragment>
  );
}

function CollectedEditableRow({
  label,
  fieldKey,
  kind,
  valueText,
  patchKey,
  commitPatch,
  patchPending,
}: {
  label: string;
  fieldKey: string;
  kind: "string" | "csv" | "multiline";
  valueText: string;
  patchKey: string;
  commitPatch: (body: CollectedPatch) => Promise<unknown>;
  patchPending: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const skipBlurCancel = useRef(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      if (inputRef.current instanceof HTMLInputElement) {
        inputRef.current.select();
      }
    }
  }, [editing]);

  const beginEdit = useCallback(() => {
    setDraft(valueText);
    setEditing(true);
  }, [valueText]);

  const cancelEdit = useCallback(() => {
    setEditing(false);
    setDraft("");
  }, []);

  const buildPatch = useCallback((): CollectedPatch => {
    if (kind === "csv") {
      return { [patchKey]: splitCsv(draft) };
    }
    if (kind === "multiline") {
      if (draft.trim() === "") {
        return { [patchKey]: null };
      }
      return { [patchKey]: draft };
    }
    const t = draft.trim();
    return { [patchKey]: t === "" ? null : t };
  }, [draft, kind, patchKey]);

  const commit = useCallback(async () => {
    try {
      await commitPatch(buildPatch());
    } finally {
      skipBlurCancel.current = false;
    }
    setEditing(false);
    setDraft("");
  }, [buildPatch, commitPatch]);

  const onBlur = useCallback(() => {
    if (skipBlurCancel.current) {
      skipBlurCancel.current = false;
      return;
    }
    cancelEdit();
  }, [cancelEdit]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        cancelEdit();
        return;
      }
      if (kind === "multiline") {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          e.preventDefault();
          void commit();
        }
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        skipBlurCancel.current = true;
        void commit();
      }
    },
    [cancelEdit, commit, kind],
  );

  const display = valueText.trim() === "" ? "—" : valueText;

  return (
    <Fragment key={fieldKey}>
      <dt className="text-stone-500">{label}</dt>
      <dd className="min-w-0 text-stone-900">
        {!editing ? (
          <button
            type="button"
            disabled={patchPending}
            className="w-full cursor-pointer rounded border border-transparent px-1 py-0.5 text-left text-sm hover:border-stone-200 hover:bg-stone-50 disabled:cursor-wait disabled:opacity-60"
            onClick={beginEdit}
          >
            {display}
          </button>
        ) : kind === "multiline" ? (
          <div className="space-y-1">
            <textarea
              ref={inputRef as React.RefObject<HTMLTextAreaElement>}
              rows={4}
              className="w-full resize-y rounded-md border border-stone-300 px-2 py-1.5 font-sans text-sm shadow-sm focus:border-stone-500 focus:outline-none focus:ring-1 focus:ring-stone-400"
              value={draft}
              disabled={patchPending}
              onChange={(ev) => setDraft(ev.target.value)}
              onBlur={onBlur}
              onKeyDown={onKeyDown}
              aria-label={`Edit ${label}`}
            />
            <p className="text-[11px] text-stone-500">
              ⌘ Enter or Ctrl+Enter to save · Esc or click outside to cancel
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            <input
              ref={inputRef as React.RefObject<HTMLInputElement>}
              type="text"
              className="w-full rounded-md border border-stone-300 px-2 py-1 text-sm shadow-sm focus:border-stone-500 focus:outline-none focus:ring-1 focus:ring-stone-400"
              value={draft}
              disabled={patchPending}
              onChange={(ev) => setDraft(ev.target.value)}
              onBlur={onBlur}
              onKeyDown={onKeyDown}
              aria-label={`Edit ${label}`}
            />
            <p className="text-[11px] text-stone-500">
              Enter to save · Esc or click outside to cancel
              {kind === "csv" ? " · Separate values with commas" : null}
            </p>
          </div>
        )}
      </dd>
    </Fragment>
  );
}

export default function AdminTenantOnboardingPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const optQ = useQuery({
    queryKey: ["admin-onboarding-answer-options"],
    queryFn: () => adminJson<AdminOnboardingOptions>("/admin/meta/onboarding-answer-options"),
    staleTime: 60 * 60 * 1000,
  });

  const q = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminJson<TenantDetail>(`/admin/tenants/${tenantId}`),
    enabled: Boolean(tenantId),
  });

  const patchMut = useMutation({
    mutationFn: async (body: CollectedPatch) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/onboarding/collected-data`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<TenantDetail>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
    },
  });

  const memberFullNameMut = useMutation({
    mutationFn: async (member_full_name: string | null) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/primary-member-full-name`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ member_full_name: member_full_name }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<TenantDetail>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
    },
  });

  const commitPatch = patchMut.mutateAsync.bind(patchMut);
  const commitMemberFullNameFromPatch = useCallback(
    async (body: CollectedPatch) => {
      const raw = body.member_full_name;
      const normalized =
        raw === null || raw === undefined
          ? null
          : typeof raw === "string"
            ? raw.trim() === ""
              ? null
              : raw.trim()
            : null;
      await memberFullNameMut.mutateAsync(normalized);
    },
    [memberFullNameMut],
  );

  const patchErr = patchMut.error as Error | null;
  const memberFullNameErr = memberFullNameMut.error as Error | null;
  const patchPending = patchMut.isPending || memberFullNameMut.isPending;

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading onboarding…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const t = q.data;
  const ob = t.onboarding;
  const userLabel = t.member_full_name?.trim() || "User";
  const chatMessages = ob ? adminOnboardingRowsToChatMessages(ob.chat_messages) : [];
  const opts = optQ.data;
  const flatTools = opts ? flattenToolOptions(opts) : [];

  return (
    <div className="space-y-8">
      <OperatorIntro title="Website onboarding">
        Structured answers first, then the in-app chat transcript (same order as the product flow:
        what we stored, then how we got there).         Role in company and tool fields use the same allowed values as the product; company size and
        other free-text fields use click-to-edit (Enter saves, Esc or click outside cancels). Slack
        handoff is read-only here.
      </OperatorIntro>

      {optQ.isError ? (
        <p className="text-sm text-red-700">Could not load field options: {(optQ.error as Error).message}</p>
      ) : null}

      {!ob ? (
        <OperatorSection title="Status" description="No onboarding session in the database.">
          <p className="text-sm text-stone-600">
            This workspace has not opened product onboarding yet, or data was never created.
          </p>
        </OperatorSection>
      ) : (
        <>
          <OperatorSection
            title="Collected data"
            description="Grouped by onboarding state, the primary workspace member, and company answers from onboarding. Name and email come from the membership record (not the onboarding chat transcript)."
          >
            {patchErr ? <p className="mb-3 text-sm text-red-700">{patchErr.message}</p> : null}
            {memberFullNameErr ? (
              <p className="mb-3 text-sm text-red-700">{memberFullNameErr.message}</p>
            ) : null}

            <div className="space-y-8">
              <div>
                <h3 className={collectedSubheadingClass}>State &amp; onboarding</h3>
                <dl className={collectedDlClass}>
                  <dt className="text-stone-500">Status</dt>
                  <dd className="text-stone-900">{ob.status}</dd>
                  <dt className="text-stone-500">Current step</dt>
                  <dd className="text-stone-900">{ob.current_step}</dd>
                  <dt className="text-stone-500">Connector queue</dt>
                  <dd className="font-mono text-xs text-stone-800">
                    {(ob.connect_queue?.length ?? 0) > 0 ? (ob.connect_queue ?? []).join(" → ") : "—"}
                  </dd>
                  <dt className="text-stone-500">Connector plan</dt>
                  <dd className="font-mono text-xs text-stone-800">
                    {(ob.connect_plan?.length ?? 0) > 0 ? (ob.connect_plan ?? []).join(" → ") : "—"}
                  </dd>
                  <dt className="text-stone-500">Profile phase</dt>
                  <dd>{ob.profile_phase ?? "—"}</dd>
                  <dt className="text-stone-500">Started</dt>
                  <dd>{ob.started_at ? new Date(ob.started_at).toLocaleString() : "—"}</dd>
                  <dt className="text-stone-500">Completed</dt>
                  <dd>{ob.completed_at ? new Date(ob.completed_at).toLocaleString() : "—"}</dd>
                  <dt className="text-stone-500">Abandoned</dt>
                  <dd>{ob.abandoned_at ? new Date(ob.abandoned_at).toLocaleString() : "—"}</dd>
                  <dt className="text-stone-500">Workspace connectors linked</dt>
                  <dd className="text-stone-900">
                    {t.connected_connectors?.length ? t.connected_connectors.join(", ") : "—"}
                  </dd>
                </dl>
              </div>

              <div>
                <h3 className={collectedSubheadingClass}>User</h3>
                <p className="mt-2 text-xs text-stone-500">
                  Primary member on this workspace (oldest membership). Full name updates the user
                  record; email is read-only here.
                </p>
                <dl className={collectedDlClass}>
                  <CollectedEditableRow
                    label="Full name"
                    fieldKey="member_full_name"
                    patchKey="member_full_name"
                    kind="string"
                    valueText={t.member_full_name ?? ""}
                    commitPatch={commitMemberFullNameFromPatch}
                    patchPending={patchPending}
                  />
                  <dt className="text-stone-500">Email</dt>
                  <dd className="break-all text-stone-900">{t.member_email ?? "—"}</dd>
                  {opts ? (
                    <CollectedSelectRow
                      label="Role in company"
                      fieldKey="user_role"
                      patchKey="user_role"
                      value={ob.user_role}
                      options={opts.profile_roles}
                      emptyLabel="— Clear —"
                      commitPatch={commitPatch}
                      patchPending={patchPending}
                    />
                  ) : (
                    <>
                      <dt className="text-stone-500">Role in company</dt>
                      <dd className="text-stone-500">Loading options…</dd>
                    </>
                  )}
                </dl>
              </div>

              <div>
                <h3 className={collectedSubheadingClass}>Company</h3>
                <dl className={collectedDlClass}>
                  <CollectedEditableRow
                    label="Company website"
                    fieldKey="company_website"
                    patchKey="company_website"
                    kind="string"
                    valueText={ob.company_website ?? ""}
                    commitPatch={commitPatch}
                    patchPending={patchPending}
                  />

                  <CollectedEditableRow
                    label="Company size"
                    fieldKey="company_size"
                    patchKey="company_size"
                    kind="string"
                    valueText={ob.company_size ?? ""}
                    commitPatch={commitPatch}
                    patchPending={patchPending}
                  />

                  {opts ? (
                    <CollectedToolsMultiRow
                      label="Tools interest"
                      fieldKey="tools_interest"
                      patchKey="tools_interest"
                      items={flatTools}
                      selectedIds={ob.tools_interest}
                      commitPatch={commitPatch}
                      patchPending={patchPending}
                    />
                  ) : (
                    <>
                      <dt className="text-stone-500">Tools interest</dt>
                      <dd className="text-stone-500">Loading options…</dd>
                    </>
                  )}

                  <CollectedEditableRow
                    label="Company domain (legacy)"
                    fieldKey="company_domain"
                    patchKey="company_domain"
                    kind="string"
                    valueText={ob.company_domain ?? ""}
                    commitPatch={commitPatch}
                    patchPending={patchPending}
                  />

                  {opts ? (
                    <>
                      <CollectedToolsMultiRow
                        label="Communication"
                        fieldKey="tools_communication"
                        patchKey="tools_communication"
                        items={opts.tools_by_category.communication ?? []}
                        selectedIds={ob.tools_communication}
                        commitPatch={commitPatch}
                        patchPending={patchPending}
                      />
                      <CollectedToolsMultiRow
                        label="Project management"
                        fieldKey="tools_pm"
                        patchKey="tools_pm"
                        items={opts.tools_by_category.pm ?? []}
                        selectedIds={ob.tools_pm}
                        commitPatch={commitPatch}
                        patchPending={patchPending}
                      />
                      <CollectedToolsMultiRow
                        label="Engineering"
                        fieldKey="tools_engineering"
                        patchKey="tools_engineering"
                        items={opts.tools_by_category.engineering ?? []}
                        selectedIds={ob.tools_engineering}
                        commitPatch={commitPatch}
                        patchPending={patchPending}
                      />
                      <CollectedToolsMultiRow
                        label="Video calls"
                        fieldKey="tools_calls"
                        patchKey="tools_calls"
                        items={opts.tools_by_category.calls ?? []}
                        selectedIds={ob.tools_calls ?? []}
                        commitPatch={commitPatch}
                        patchPending={patchPending}
                      />
                      <CollectedToolsMultiRow
                        label="Documentation"
                        fieldKey="tools_docs"
                        patchKey="tools_docs"
                        items={opts.tools_by_category.docs ?? []}
                        selectedIds={ob.tools_docs}
                        commitPatch={commitPatch}
                        patchPending={patchPending}
                      />
                      <CollectedToolsMultiRow
                        label="Calendars"
                        fieldKey="tools_calendars"
                        patchKey="tools_calendars"
                        items={opts.tools_by_category.calendars ?? []}
                        selectedIds={ob.tools_calendars ?? []}
                        commitPatch={commitPatch}
                        patchPending={patchPending}
                      />
                    </>
                  ) : (
                    <>
                      <dt className="text-stone-500">Tool pickers</dt>
                      <dd className="text-stone-500">
                        Loading catalog (tools by category)…
                      </dd>
                    </>
                  )}
                </dl>
              </div>
            </div>

            <div className="mt-8 space-y-4 border-t border-stone-200 pt-6">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-400">Slack handoff</h3>
                <p className="mt-1 text-xs text-stone-500">
                  Read-only — set during product onboarding (Slack stakeholder step).
                </p>
                {ob.slack_stakeholders &&
                (ob.slack_stakeholders.raw_text || (ob.slack_stakeholders.slack_user_ids?.length ?? 0) > 0) ? (
                  <div className="mt-2 space-y-2 rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm text-stone-800">
                    {ob.slack_stakeholders.raw_text ? (
                      <p className="whitespace-pre-wrap break-words">{ob.slack_stakeholders.raw_text}</p>
                    ) : null}
                    {(ob.slack_stakeholders.slack_user_ids?.length ?? 0) > 0 ? (
                      <p className="font-mono text-xs text-stone-600">
                        Slack user IDs: {ob.slack_stakeholders.slack_user_ids.join(", ")}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-stone-500">—</p>
                )}
              </div>
              {ob.tools_stack && Object.keys(ob.tools_stack).length > 0 ? (
                <details className="rounded-lg border border-stone-200 bg-white">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-stone-700">
                    Tools stack (legacy JSON)
                  </summary>
                  <pre className="max-h-72 overflow-auto border-t border-stone-100 p-4 text-xs text-stone-800">
                    {JSON.stringify(ob.tools_stack, null, 2)}
                  </pre>
                </details>
              ) : null}
            </div>
          </OperatorSection>

          <OperatorSection
            title="Conversation"
            description="Chronological transcript: Vector on the left, signed-in user on the right (same layout as the product)."
          >
            <AdminOnboardingStyleThread
              messages={chatMessages}
              userDisplayName={userLabel}
              maxHeightClass="max-h-[min(44rem,85vh)]"
            />
          </OperatorSection>
        </>
      )}

      <CollapsibleDebug title="Debug: raw tenant JSON (API response)">
        <pre className="max-h-64 overflow-auto text-xs text-stone-700">{JSON.stringify(t, null, 2)}</pre>
      </CollapsibleDebug>
    </div>
  );
}
