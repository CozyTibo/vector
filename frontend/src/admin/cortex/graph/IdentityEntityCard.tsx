import type {
  IdentityContinuityCandidate,
  IdentityContinuityEntityInspector,
} from "./identityContinuityTypes";

type Props = {
  data: IdentityContinuityEntityInspector;
};

export function IdentityEntityCard({ data }: Props) {
  const entity = data.entity;
  const summary = data.evidence_summary;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Identity card</h3>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <Field label="Entity id" value={String(entity.id ?? "—")} mono />
          <Field label="Entity kind" value={String(entity.entity_kind ?? "—")} />
          <Field label="Lifecycle" value={String(entity.lifecycle_state ?? "—")} />
          <Field label="Created" value={String(entity.created_at ?? "—")} />
          <Field label="Fingerprint" value={String(entity.identity_key_fingerprint ?? "—")} mono />
        </dl>
      </section>

      {data.resolved_identities.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Resolved identities</h3>
          <div className="mt-3 space-y-3">
            {data.resolved_identities.map((row, idx) => (
              <div key={idx} className="rounded-lg border border-stone-100 bg-stone-50 p-3 text-sm">
                <p className="font-mono text-xs text-stone-600">
                  {String(row.projection_kind ?? "unknown")} · {String(row.source_system ?? "—")}
                </p>
                <pre className="mt-2 overflow-x-auto text-xs text-stone-800">
                  {JSON.stringify(row, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Authoritative links" value={String(summary.authoritative_link_count ?? 0)} />
        <Metric label="Candidates" value={String(summary.candidate_count ?? 0)} />
        <Metric label="Promotable" value={String(summary.promotable_count ?? 0)} />
        <Metric label="Skipped" value={String(summary.skipped_count ?? 0)} />
      </section>

      {data.skipped_candidates.length > 0 ? (
        <CandidateTable title="Skipped / rejected candidates" rows={data.skipped_candidates} />
      ) : null}

      {data.promotable_candidates.length > 0 ? (
        <CandidateTable title="Promotable candidates" rows={data.promotable_candidates} />
      ) : null}

      {data.promotion_lineage.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Promotion lineage</h3>
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                  <th className="px-3 py-2">link_type</th>
                  <th className="px-3 py-2">rule_id</th>
                  <th className="px-3 py-2">candidate</th>
                  <th className="px-3 py-2">created</th>
                </tr>
              </thead>
              <tbody>
                {data.promotion_lineage.map((row) => (
                  <tr key={String(row.link_id)} className="border-b border-stone-100">
                    <td className="px-3 py-2 font-mono text-xs">{String(row.link_type ?? "—")}</td>
                    <td className="px-3 py-2 font-mono text-xs">{String(row.rule_id ?? "—")}</td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {String(row.promoted_from_candidate_id ?? "—").slice(0, 8)}…
                    </td>
                    <td className="px-3 py-2 text-xs">{String(row.created_at ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {data.open_ambiguities.length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">Open ambiguities</h3>
          <ul className="mt-2 space-y-2 text-sm text-amber-900">
            {data.open_ambiguities.map((row) => (
              <li key={String(row.id)} className="font-mono text-xs">
                {String(row.ambiguity_class)} · {String(row.status)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-stone-50 p-4">
        <h3 className="text-sm font-semibold text-stone-900">Raw entity metadata</h3>
        <pre className="mt-2 overflow-x-auto text-xs text-stone-700">
          {JSON.stringify(entity.metadata_json ?? {}, null, 2)}
        </pre>
      </section>
    </div>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs uppercase text-stone-500">{label}</dt>
      <dd className={["mt-0.5 text-stone-900", mono ? "font-mono text-xs break-all" : ""].join(" ")}>
        {value}
      </dd>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase text-stone-500">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function CandidateTable({ title, rows }: { title: string; rows: IdentityContinuityCandidate[] }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-stone-900">{title}</h3>
      <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-stone-50 text-xs uppercase text-stone-500">
              <th className="px-3 py-2">rule_id</th>
              <th className="px-3 py-2">link_type</th>
              <th className="px-3 py-2">skip reason</th>
              <th className="px-3 py-2">evidence refs</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.candidate_id} className="border-b border-stone-100">
                <td className="px-3 py-2 font-mono text-xs">{row.rule_id ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-xs">{row.link_type}</td>
                <td className="px-3 py-2 text-xs">{row.skip_reason_code}</td>
                <td className="px-3 py-2 tabular-nums">{row.evidence_raw_record_ids.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

