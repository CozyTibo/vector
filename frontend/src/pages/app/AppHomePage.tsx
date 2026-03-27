import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchMe, productApiBase } from "../../lib/meApi";

const CONNECTOR_LABELS: Record<string, string> = {
  github: "GitHub",
  linear: "Linear",
};

function labelForProvider(id: string): string {
  const key = id.toLowerCase();
  return CONNECTOR_LABELS[key] ?? id.charAt(0).toUpperCase() + id.slice(1);
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
      <main className="mx-auto max-w-2xl px-4 py-12">
        <p className="text-stone-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-12">
      <header className="mb-10">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900 sm:text-3xl">
          Vector is getting your workspace ready
        </h1>
        <p className="mt-4 text-base leading-relaxed text-stone-600">
          Your tools are connected and data is syncing. We&apos;re preparing the first version of the execution
          interface.
        </p>
      </header>

      <section className="mb-10 rounded-2xl border border-stone-200 bg-white px-6 py-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">Connected tools</h2>
        {connected.length === 0 ? (
          <p className="mt-4 text-sm text-stone-600">
            No tools linked yet. Use the button below to connect GitHub, Linear, or more.
          </p>
        ) : (
          <ul className="mt-4 space-y-2.5">
            {connected.map((id) => (
              <li key={id} className="flex items-center gap-2 text-stone-800">
                <span className="text-green-600" aria-hidden>
                  ✓
                </span>
                <span className="font-medium">{labelForProvider(id)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-10 rounded-2xl border border-stone-200 bg-stone-50 px-6 py-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">Design partner</h2>
        <div className="mt-4 space-y-3 text-sm leading-relaxed text-stone-700">
          <p className="font-medium text-stone-900">You&apos;re early.</p>
          <p>
            We&apos;re working with a small group of teams to build Vector&apos;s execution intelligence system.
          </p>
          <p>Your data is syncing in the background and helping us shape the product.</p>
          <p>We&apos;ll reach out soon when the first features are ready.</p>
        </div>
      </section>

      <section className="rounded-2xl border border-stone-200 bg-white px-6 py-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">Improve your workspace</h2>
        <p className="mt-3 text-sm text-stone-600">Link more tools so we can learn from more of how your team ships.</p>
        <Link
          to="/app/connectors"
          className="mt-5 inline-flex rounded-xl bg-stone-900 px-5 py-2.5 text-sm font-medium text-white no-underline hover:bg-stone-800"
        >
          Connect more tools
        </Link>
      </section>
    </main>
  );
}
