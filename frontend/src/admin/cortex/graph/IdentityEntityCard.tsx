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
  const status = data.continuity_status;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Identity card</h3>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <Field label="Entity id" value={String(entity.id ?? "—")} mono />
          <Field label="Entity kind" value={String(entity.entity_kind ?? "—")} />
          <Field label="Lifecycle" value={String(entity.lifecycle_state ?? "—")} />
          <Field label="Created" value={String(entity.created_at ?? "—")} />
          <Field
            label="Canonical entity id"
            value={String(status.canonical_entity_id ?? "—")}
            mono
          />
          <Field label="Fingerprint" value={String(entity.identity_key_fingerprint ?? "—")} mono />
        </dl>
      </section>

      {data.linked_handles.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Linked handles (multi-persona)</h3>
          <p className="mt-1 text-xs text-stone-500">
            Slack, GitHub, Notion, and email personas connected via authoritative links or ambiguity
            clusters.
          </p>
          <div className="mt-3 space-y-3">
            {data.linked_handles.map((row, idx) => (
              <div key={idx} className="rounded-lg border border-stone-100 bg-stone-50 p-3 text-sm">
                <p className="font-mono text-xs text-stone-600">
                  {String(row.projection_kind ?? "unknown")} · {String(row.source_system ?? "—")}
                  {row.is_primary ? " · primary" : ""}
                </p>
                <pre className="mt-2 overflow-x-auto text-xs text-stone-800">
                  {JSON.stringify(row, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </section>
      ) : null}

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
        <Metric label="Linked handles" value={String(summary.linked_handle_count ?? 0)} />
        <Metric label="Authoritative links" value={String(summary.authoritative_link_count ?? 0)} />
        <Metric label="Candidates" value={String(summary.candidate_count ?? 0)} />
        <Metric label="Promotable" value={String(summary.promotable_count ?? 0)} />
        <Metric label="Skipped" value={String(summary.skipped_count ?? 0)} />
        <Metric label="Generation rejections" value={String(summary.unresolved_generation_count ?? 0)} />
        <Metric label="Evidence receipts" value={String(summary.evidence_receipt_count ?? 0)} />
        <Metric label="Open ambiguities" value={String(summary.open_ambiguity_count ?? 0)} />
      </section>

      {data.duplicate_identities.length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">Duplicate identities</h3>
          <ul className="mt-2 space-y-1 text-xs font-mono text-amber-900">
            {data.duplicate_identities.map((row, idx) => (
              <li key={idx}>
                {String(row.match_field)}={String(row.match_value)} →{" "}
                {(row.handle_ids as string[]).join(", ")}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {data.conflicting_identities.length > 0 ? (
        <section className="rounded-xl border border-red-200 bg-red-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-red-950">Conflicting identities</h3>
          <ul className="mt-2 space-y-1 text-xs font-mono text-red-900">
            {data.conflicting_identities.map((row, idx) => (
              <li key={idx}>
                {String(row.ambiguity_class)} · {(row.involved_org_entity_ids as string[]).join(", ")}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {data.generation_rejections.length > 0 ? (
        <section className="rounded-xl border border-orange-200 bg-orange-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-orange-950">Generation rejections</h3>
          <p className="mt-1 text-xs text-orange-800">
            Anchors related to this entity that did not produce continuity-eligible candidates.
          </p>
          {Object.keys(data.generation_rejection_counts).length > 0 ? (
            <ul className="mt-2 flex flex-wrap gap-2 text-xs">
              {Object.entries(data.generation_rejection_counts).map(([code, count]) => (
                <li key={code} className="rounded bg-orange-100 px-2 py-1 font-mono text-orange-900">
                  {code}: {count}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mt-3 space-y-2">
            {data.generation_rejections.slice(0, 12).map((row, idx) => (
              <details key={idx} className="rounded-lg border border-orange-200 bg-white p-3 text-xs">
                <summary className="cursor-pointer font-mono text-orange-900">
                  {String(row.anchor_canonical_entity_id ?? "anchor").slice(0, 8)}… ·{" "}
                  {String(row.primary_skip_reason_code ?? "—")}
                </summary>
                <pre className="mt-2 overflow-x-auto text-stone-700">{JSON.stringify(row, null, 2)}</pre>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      {data.evidence_receipts.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Anchor evidence chain</h3>
          <p className="mt-1 text-xs text-stone-500">
            Raw → canonical → anchor → eligible rules and primitive projections per related anchor.
          </p>
          <div className="mt-3 space-y-2">
            {data.evidence_receipts.slice(0, 12).map((row, idx) => (
              <details key={idx} className="rounded-lg border border-stone-100 bg-stone-50 p-3 text-xs">
                <summary className="cursor-pointer font-mono text-stone-800">
                  {String(row.anchor_connector ?? "—")} / {String(row.anchor_canonical_object_kind ?? "—")} ·{" "}
                  {String(row.anchor_canonical_entity_id ?? "—").slice(0, 8)}…
                </summary>
                <pre className="mt-2 overflow-x-auto text-stone-700">{JSON.stringify(row, null, 2)}</pre>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      {(data.candidate_lineage?.pair_families_touching_entity as Array<Record<string, unknown>>)?.length >
      0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Candidate pair evidence</h3>
          <pre className="mt-2 overflow-x-auto text-xs text-stone-700">
            {JSON.stringify(data.candidate_lineage.pair_families_touching_entity, null, 2)}
          </pre>
        </section>
      ) : null}

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
                {String(row.ambiguity_class)} · {String(row.status)} ·{" "}
                {(row.involved_org_entity_ids as string[] | undefined)?.join(", ")}
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

