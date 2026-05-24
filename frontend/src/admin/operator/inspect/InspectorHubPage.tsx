import { Link, useParams } from "react-router-dom";

const LENSES = [
  {
    key: "identity",
    title: "Identity",
    description: "Who is this person across Slack, GitHub, Notion, and email?",
    question: "Search by external id → entity card with promotion lineage.",
  },
  {
    key: "graph",
    title: "Graph",
    description: "Why does this edge exist? What rules promoted it?",
    question: "Materialized snapshot summary + on-demand edge lookup.",
  },
  {
    key: "islands",
    title: "Islands",
    description: "What execution scopes are alive in the registry?",
    question: "Registry list only — no connected-component scan on load.",
  },
  {
    key: "retrieval",
    title: "Retrieval",
    description: "Was this PR or scope indexed? What epoch and lineage?",
    question: "Epoch list + entry search + terminal→root chain.",
  },
  {
    key: "synthesis",
    title: "Synthesis",
    description: "What claim came from which retrieval pins?",
    question: "Job search → existing debugger with artifact evidence.",
  },
  {
    key: "execution",
    title: "Execution thread",
    description: "What walk/TCRE/index chain exists for this scope?",
    question: "Walk replay lineage + TCRE jobs + related index entries.",
  },
] as const;

export default function InspectorHubPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Inspect</h1>
        <p className="mt-1 text-sm text-stone-600">
          Evidence-first lenses. This hub makes no API calls — pick a lens to investigate.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {LENSES.map((lens) => (
          <Link
            key={lens.key}
            to={`/admin/tenants/${tenantId}/cortex/inspect/${lens.key}`}
            className="block rounded-xl border border-stone-200 bg-white p-5 no-underline shadow-sm transition hover:border-indigo-200 hover:shadow-md"
          >
            <p className="text-sm font-semibold text-stone-900">{lens.title}</p>
            <p className="mt-2 text-sm text-stone-700">{lens.description}</p>
            <p className="mt-2 text-xs text-stone-500">{lens.question}</p>
            <span className="mt-4 inline-block text-xs font-medium text-indigo-700">Open lens →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
