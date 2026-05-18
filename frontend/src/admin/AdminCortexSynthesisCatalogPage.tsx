import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { SYNTHESIS_CATALOG_SURFACES, type SynthesisCatalogSurface } from "./synthesisAdminSurfaces";

type Props = {
  surfaceKey: keyof typeof SYNTHESIS_CATALOG_SURFACES;
};

export default function AdminCortexSynthesisCatalogPage({ surfaceKey }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const surface: SynthesisCatalogSurface = SYNTHESIS_CATALOG_SURFACES[surfaceKey];

  const { data, isLoading, error } = useQuery({
    queryKey: ["synthesis-catalog", tenantId, surfaceKey],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/synthesis${surface.endpoint}`,
      ),
  });

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">{surface.title}</h2>
      <p className="mt-1 text-sm text-stone-600">{surface.description}</p>
      {isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      {error && <p className="mt-2 text-sm text-red-700">Failed to load catalog.</p>}
      {data && (
        <pre className="mt-3 max-h-[32rem] overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </section>
  );
}
