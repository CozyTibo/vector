import { useAdminBuildInfo } from "./useAdminBuildInfo";
import { frontendGitShaShort, isCortexAdminV2Enabled } from "./featureFlags";

export function DeployInfoFooter() {
  const buildQ = useAdminBuildInfo();
  const apiSha = buildQ.data?.git_sha_short ?? buildQ.data?.git_sha ?? null;
  const uiSha = frontendGitShaShort();
  const v2Flag = isCortexAdminV2Enabled();
  const apiV2 = buildQ.data?.cortex_admin_v2_enabled;

  return (
    <footer className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-xs text-stone-600">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span>
          API deploy{" "}
          <code className="rounded bg-white px-1 py-0.5 text-stone-800">{apiSha ?? "unknown"}</code>
        </span>
        <span>
          UI build{" "}
          <code className="rounded bg-white px-1 py-0.5 text-stone-800">{uiSha ?? "local"}</code>
        </span>
        <span>
          Operator v2 flag UI=<code className="rounded bg-white px-1">{String(v2Flag)}</code> API=
          <code className="rounded bg-white px-1">{apiV2 == null ? "…" : String(apiV2)}</code>
        </span>
        {buildQ.data?.env ? <span>env={buildQ.data.env}</span> : null}
      </div>
      {buildQ.isError ? (
        <p className="mt-1 text-red-700">Could not load API build info: {(buildQ.error as Error).message}</p>
      ) : null}
    </footer>
  );
}
