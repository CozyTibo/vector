import { useAdminBuildInfo } from "./useAdminBuildInfo";
import { frontendGitShaShort } from "./buildVersion";

export function DeployInfoFooter() {
  const buildQ = useAdminBuildInfo();
  const apiSha = buildQ.data?.git_sha_short ?? buildQ.data?.git_sha ?? null;
  const uiSha = frontendGitShaShort();

  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-xs text-stone-600">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span>
          API deploy{" "}
          <code className="rounded bg-white px-1 py-0.5 text-stone-800">{apiSha ?? "unknown"}</code>
        </span>
        <span>
          UI build{" "}
          <code className="rounded bg-white px-1 py-0.5 text-stone-800">{uiSha ?? "local"}</code>
        </span>
        {buildQ.data?.env ? <span>env={buildQ.data.env}</span> : null}
      </div>
      {buildQ.isError ? (
        <p className="mt-1 text-red-700">Could not load API build info: {(buildQ.error as Error).message}</p>
      ) : null}
    </div>
  );
}
