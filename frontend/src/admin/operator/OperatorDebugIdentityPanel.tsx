import { useSearchParams } from "react-router-dom";

/** Debug-only cortex identity APIs (Wave 2 — not linked from primary nav). */
export function OperatorDebugIdentityPanel() {
  const [searchParams] = useSearchParams();
  if (searchParams.get("debug") !== "1") {
    return null;
  }

  return (
    <section className="rounded-xl border border-dashed border-amber-300 bg-amber-50/80 p-5 text-sm text-amber-950">
      <p className="font-semibold">Debug identity APIs</p>
      <p className="mt-1 text-xs opacity-90">
        Forensics only. Routine repair: use <strong>Rebuild identities</strong> on People (reset cursor +
        convergence slices). These routes are not on the primary operator nav.
      </p>
      <ul className="mt-3 list-inside list-disc space-y-1 font-mono text-xs">
        <li>POST …/cortex/debug/identity/backfill/from-canonical-anchors</li>
        <li>GET/POST …/cortex/debug/identity/replay-jobs</li>
        <li>POST …/cortex/debug/identity/full-substrate-refresh?debug_acknowledged=true</li>
      </ul>
      <p className="mt-2 text-xs">Add <code className="rounded bg-amber-100 px-1">?debug=1</code> to this URL to show this panel.</p>
    </section>
  );
}
