import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  landingAccentText,
  landingSubtleLineH,
} from "../../components/landing/landingBrandPalette";
import { fetchMe, productApiBase } from "../../lib/meApi";

const CONNECTOR_LABELS: Record<string, string> = {
  github: "GitHub",
  linear: "Linear",
  slack: "Slack",
};

function labelForProvider(id: string): string {
  const key = id.toLowerCase();
  return CONNECTOR_LABELS[key] ?? id.charAt(0).toUpperCase() + id.slice(1);
}

function firstNameFromMe(fullName: string | null | undefined, email: string): string {
  if (fullName?.trim()) {
    return fullName.trim().split(/\s+/)[0] ?? fullName.trim();
  }
  const local = email.split("@")[0] ?? "";
  return local || "there";
}

function formatMembershipRole(role: string): string {
  const r = role.trim();
  if (!r) {
    return "Member";
  }
  return r
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

export default function AppHomePage() {
  const apiBase = productApiBase();
  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });

  const connected = me.data?.connected_connectors ?? [];

  if (me.isPending || !me.data) {
    return (
      <main className="mx-auto max-w-3xl min-h-0 flex-1 overflow-y-auto px-4 py-10 sm:px-6 sm:py-14">
        <p className="text-center text-sm font-medium text-stone-500">Loading your workspace…</p>
      </main>
    );
  }

  const { company_name, tenant_slug, email, full_name, role, use_mock_connectors } = me.data;
  const first = firstNameFromMe(full_name, email);
  const roleLabel = formatMembershipRole(role);

  return (
    <main className="relative mx-auto max-w-3xl min-h-0 flex-1 overflow-y-auto px-4 py-8 sm:px-6 sm:py-12">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-[#FDF4F8]/90 to-transparent"
        aria-hidden
      />

      <div className="relative space-y-8">
        {/* Workspace identity */}
        <section className="overflow-hidden rounded-2xl border border-stone-200/90 bg-white shadow-[0_20px_50px_-28px_rgba(15,23,42,0.12)] ring-1 ring-stone-950/[0.03]">
          <div className={`h-1 w-full ${landingSubtleLineH}`} aria-hidden />
          <div className="px-5 py-6 sm:px-8 sm:py-8">
            <p className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${landingAccentText}`}>
              Your workspace
            </p>
            <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight text-stone-900 sm:text-3xl">
              {company_name?.trim() ? company_name : "Your company"}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-stone-600">
              You&apos;re signed in as <span className="font-medium text-stone-800">{first}</span>
              <span className="text-stone-400"> · </span>
              <span className="text-stone-600">{email}</span>
            </p>
            <dl className="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-stone-100 pt-5 text-xs text-stone-500">
              <div>
                <dt className="font-medium text-stone-400">Access</dt>
                <dd className="mt-0.5 text-stone-700">{roleLabel}</dd>
              </div>
              <div>
                <dt className="font-medium text-stone-400">Workspace ID</dt>
                <dd className="mt-0.5 font-mono text-[11px] text-stone-600">{tenant_slug}</dd>
              </div>
            </dl>
          </div>
        </section>

        {/* Status — what’s happening */}
        <section className="rounded-2xl border border-stone-200 bg-white px-5 py-6 shadow-sm sm:px-7">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">
                What&apos;s happening
              </h2>
              <p className="mt-3 text-base font-medium leading-snug text-stone-900">
                We&apos;re preparing your executive view
              </p>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
                Onboarding is complete for this workspace. Vector is pulling light activity from your connected
                tools and syncing in the background. You&apos;re on the design-partner track while we ship the
                first insights.
              </p>
            </div>
            <span className="inline-flex w-fit shrink-0 items-center rounded-full border border-emerald-200/90 bg-emerald-50/90 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-900">
              Workspace active
            </span>
          </div>
          {use_mock_connectors ? (
            <p className="mt-4 rounded-lg border border-amber-200/80 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
              Development mode: mock connectors are enabled. Data may be sample-only.
            </p>
          ) : null}
        </section>

        {/* Connected tools */}
        <section className="rounded-2xl border border-stone-200 bg-white px-5 py-6 shadow-sm sm:px-7">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">Connected tools</h2>
          {connected.length === 0 ? (
            <p className="mt-4 text-sm leading-relaxed text-stone-600">
              No tools linked yet. Connect at least one source so we can learn how your team ships.
            </p>
          ) : (
            <ul className="mt-4 grid gap-2 sm:grid-cols-2">
              {connected.map((id) => (
                <li
                  key={id}
                  className="flex items-center gap-3 rounded-xl border border-stone-100 bg-stone-50/80 px-3 py-2.5"
                >
                  <span
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-sm text-emerald-600 shadow-sm ring-1 ring-stone-200/80"
                    aria-hidden
                  >
                    ✓
                  </span>
                  <span className="text-sm font-medium text-stone-800">{labelForProvider(id)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Design partner + CTA */}
        <section className="rounded-2xl border border-stone-200 bg-gradient-to-b from-stone-50/90 to-white px-5 py-6 sm:px-7">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">Design partner</h2>
          <p className="mt-3 text-sm font-semibold text-stone-900">You&apos;re early — thank you.</p>
          <p className="mt-2 text-sm leading-relaxed text-stone-600">
            We&apos;re building Vector with a small set of teams. Your connected data helps shape what we ship
            next; we&apos;ll reach out when the first features are ready.
          </p>
          <div className="mt-6 border-t border-stone-200/80 pt-6">
            <p className="text-sm font-medium text-stone-800">Improve coverage</p>
            <p className="mt-1 text-sm text-stone-600">
              Link more tools so we see more of how work moves across your org.
            </p>
            <Link
              to="/app/connectors"
              className="mt-4 inline-flex rounded-full bg-stone-900 px-5 py-2.5 text-sm font-semibold text-white no-underline transition hover:bg-stone-800"
            >
              Connect more tools
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
