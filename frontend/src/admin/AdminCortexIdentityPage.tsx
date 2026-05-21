import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { PhaseRerunCta } from "./cortex/PhaseRerunCta";

type IdentitySummary = PhaseSummaryPayload & {
  cards?: Record<string, { value?: number | string; histogram?: Record<string, number> }>;
  certification_warnings?: string[];
};

const CARD_LABELS: Array<{ key: string; title: string }> = [
  { key: "org_handles", title: "Orgs" },
  { key: "persona_bindings", title: "Persona bindings" },
  { key: "authoritative_links", title: "Authoritative links" },
  { key: "candidate_links", title: "Candidate links" },
  { key: "ambiguous_identities", title: "Open ambiguities" },
  { key: "pending_merges", title: "Pending merges" },
];

function IdentitySummaryBody({ summary }: { summary: IdentitySummary }) {
  const cards = summary.cards ?? {};
  return (
    <>
      {(summary.certification_warnings ?? []).length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-amber-950">Certification warnings</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {summary.certification_warnings!.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <PhaseRerunCta
        phase="identity"
        label="Rebuild identities"
        description="Enqueues execution from the identity phase (same as Overview → Start from step → Identity)."
      />
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {CARD_LABELS.map(({ key, title }) => {
          const card = cards[key];
          const val = card?.value ?? "—";
          return (
            <div key={key} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-stone-500">{title}</p>
              <p className="mt-1 text-lg font-semibold tabular-nums">{String(val)}</p>
            </div>
          );
        })}
      </section>
    </>
  );
}

export default function AdminCortexIdentityPage() {
  return (
    <PhasePageShell
      phase="identity"
      title="Identity"
      description="Orgs, people, anchors, and merge queue. Certification warnings are inline — no separate certification tab."
      summaryContent={(s) => <IdentitySummaryBody summary={s as IdentitySummary} />}
      explorerContent={<PhaseExplorer phase="identity" />}
    />
  );
}
