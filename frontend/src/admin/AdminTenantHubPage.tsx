import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { OperatorIntro, OperatorSection } from "./ui/OperatorSections";

type TenantRow = {
  id: string;
  company_name: string;
};

export default function AdminTenantHubPage({
  title,
  subtitle,
  pathSuffix,
}: {
  title: string;
  subtitle: string;
  /** Appended after `/admin/tenants/:id/` — e.g. `execution-graph` */
  pathSuffix: string;
}) {
  const q = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => adminJson<{ items: TenantRow[] }>("/admin/tenants"),
  });

  if (q.isPending) {
    return <p className="mx-auto max-w-6xl px-4 py-8 text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return (
      <p className="mx-auto max-w-6xl px-4 py-8 text-sm text-red-700">{(q.error as Error).message}</p>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <OperatorIntro title={title}>
        {subtitle}
      </OperatorIntro>
      <OperatorSection title="Choose a workspace">
        <ul className="divide-y divide-stone-200 rounded-lg border border-stone-200 bg-white">
          {q.data.items.map((t) => (
            <li key={t.id}>
              <Link
                to={`/admin/tenants/${t.id}/${pathSuffix}`}
                className="flex items-center justify-between px-4 py-3 text-sm hover:bg-stone-50"
              >
                <span className="font-medium text-stone-900">{t.company_name}</span>
                <span className="text-blue-700">Open →</span>
              </Link>
            </li>
          ))}
        </ul>
      </OperatorSection>
    </main>
  );
}
