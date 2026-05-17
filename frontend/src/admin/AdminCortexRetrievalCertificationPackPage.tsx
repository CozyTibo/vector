import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type CertPack = {
  closure_passed: boolean;
  retrieval_cert_pack_format: string;
  whole_file_sha256?: string | null;
  pack_byte_length?: number | null;
};

export default function AdminCortexRetrievalCertificationPackPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const q = useQuery({
    queryKey: ["retrieval-cert-pack", tenantId],
    queryFn: () =>
      adminJson<CertPack>(`/admin/tenants/${tenantId}/cortex/retrieval/certification-pack`),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">RETRIEVAL-CERT-PACK-1</h2>
      <p className="mt-1 text-sm text-stone-600">
        Program certification pack snapshot (G-P07-CLOSE-01). Read-only gzip artifact + digest.
      </p>
      {q.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      {q.error && <p className="mt-2 text-sm text-red-600">{(q.error as Error).message}</p>}
      {q.data && (
        <dl className="mt-4 grid gap-2 text-sm">
          <div>
            <dt className="text-stone-500">Closure passed</dt>
            <dd>
              <StatusBadge tone={q.data.closure_passed ? "ok" : "warn"}>
                {String(q.data.closure_passed)}
              </StatusBadge>
            </dd>
          </div>
          <div>
            <dt className="text-stone-500">Format</dt>
            <dd className="font-mono text-xs">{q.data.retrieval_cert_pack_format}</dd>
          </div>
          {typeof q.data.whole_file_sha256 === "string" && (
            <div>
              <dt className="text-stone-500">Pack digest</dt>
              <dd className="font-mono text-xs break-all">{q.data.whole_file_sha256}</dd>
            </div>
          )}
          {typeof q.data.pack_byte_length === "number" && (
            <div>
              <dt className="text-stone-500">Pack bytes</dt>
              <dd>{q.data.pack_byte_length}</dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}
