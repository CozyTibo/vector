import { landingSubtleLineH } from "../../components/landing/landingBrandPalette";
import { marketingBody, marketingCard, marketingKicker, marketingPageTitle } from "../../components/marketing/marketingStyles";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

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

const connectorRowClass =
  "flex items-center gap-3 rounded-2xl border border-zinc-200/90 bg-white/90 px-4 py-3 shadow-[0_8px_28px_-22px_rgba(15,23,42,0.12)] ring-1 ring-zinc-950/[0.03]";

export default function AppHomePage() {
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);

  const connected = me.data?.connected_connectors ?? [];

  if (me.isPending || !me.data) {
    return (
      <main className="relative mx-auto flex min-h-0 max-w-3xl flex-1 flex-col items-center justify-center overflow-y-auto px-5 py-16 sm:px-8">
        <div
          className="h-9 w-9 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
        <p className={`${marketingBody} mt-5 text-center`}>Loading your workspace…</p>
      </main>
    );
  }

  const { company_name, tenant_slug, email, full_name, role, use_mock_connectors } = me.data;
  const first = firstNameFromMe(full_name, email);
  const roleLabel = formatMembershipRole(role);

  return (
    <main className="relative mx-auto max-w-3xl min-h-0 flex-1 overflow-y-auto px-5 py-10 sm:px-8 sm:py-14">
      <div className="relative space-y-7 sm:space-y-8">
        {/* Workspace identity */}
        <section className={`${marketingCard} overflow-hidden !p-0 sm:!p-0`}>
          <div className={`h-1 w-full ${landingSubtleLineH}`} aria-hidden />
          <div className="px-7 py-8 sm:px-10 sm:py-10">
            <p className={marketingKicker}>Your workspace</p>
            <h1 className={`${marketingPageTitle} mt-3`}>
              {company_name?.trim() ? company_name : "Your company"}
            </h1>
            <p className={`${marketingBody} mt-4`}>
              You&apos;re signed in as <span className="font-semibold text-[#0F0F12]">{first}</span>
              <span className="text-zinc-400"> · </span>
              <span className="text-[#52525B]">{email}</span>
            </p>
            <dl className="mt-8 flex flex-wrap gap-x-10 gap-y-4 border-t border-zinc-200/80 pt-8 text-sm">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-[#52525B]">Access</dt>
                <dd className="mt-1 font-medium text-[#0F0F12]">{roleLabel}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-[#52525B]">
                  Workspace ID
                </dt>
                <dd className="mt-1 font-mono text-xs text-[#52525B]">{tenant_slug}</dd>
              </div>
            </dl>
          </div>
        </section>

        {/* Connected tools */}
        <section className={marketingCard}>
          <h2 className={marketingKicker}>Connected tools</h2>
          {use_mock_connectors ? (
            <p className="mt-4 rounded-2xl border border-rose-200/80 bg-rose-50/90 px-4 py-3 text-sm text-rose-900">
              Development mode: mock connectors are enabled. Data may be sample-only.
            </p>
          ) : null}
          {connected.length === 0 ? (
            <p className={`${marketingBody} mt-4`}>
              No tools linked yet. Connect at least one source so we can learn how your team ships.
            </p>
          ) : (
            <ul className="mt-5 grid gap-3 sm:grid-cols-2">
              {connected.map((id) => (
                <li key={id} className={connectorRowClass}>
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#FDF4F8] text-sm font-semibold text-[#E878BE] ring-1 ring-[#E878BE]/25"
                    aria-hidden
                  >
                    ✓
                  </span>
                  <span className="text-sm font-semibold text-[#0F0F12]">{labelForProvider(id)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
