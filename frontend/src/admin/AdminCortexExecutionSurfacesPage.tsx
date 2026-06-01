import { useParams, useSearchParams } from "react-router-dom";

import { DomainDetailView } from "./executionSurfaces/DomainDetailView";
import { DomainsTab } from "./executionSurfaces/DomainsTab";
import { OverviewTab } from "./executionSurfaces/OverviewTab";
import { PeopleTab } from "./executionSurfaces/PeopleTab";
import { ActivityTab } from "./executionSurfaces/ActivityTab";
import { WorkTab } from "./executionSurfaces/WorkTab";

type Tab = "overview" | "domains" | "people" | "work" | "activity";

function resolveTab(tabParam: string | null): Tab {
  if (tabParam === "overview") return "overview";
  if (tabParam === "people") return "people";
  if (tabParam === "work") return "work";
  if (tabParam === "activity") return "activity";
  return "domains";
}

export default function AdminCortexExecutionSurfacesPage() {
  const { domainId, artifactId } = useParams<{
    tenantId: string;
    domainId?: string;
    artifactId?: string;
  }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = resolveTab(searchParams.get("tab"));

  if (domainId) {
    return <DomainDetailView domainId={domainId} />;
  }

  if (artifactId) {
    return <WorkTab />;
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-stone-900">Execution Surfaces</h1>
        <p className="mt-1 text-sm text-stone-600">
          Human view of execution reality — declared domains, people, work, and cross-tool connections. Substrate
          health lives in the tabs to the right.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["domains", "Domains"],
            ["overview", "Overview"],
            ["people", "People"],
            ["work", "Work"],
            ["activity", "Activity"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              tab === key ? "bg-indigo-100 text-indigo-900" : "text-stone-700 hover:bg-stone-100"
            }`}
            onClick={() =>
              setSearchParams((prev) => {
                const p = new URLSearchParams(prev);
                p.set("tab", key);
                p.delete("domain_id");
                p.delete("person_id");
                return p;
              })
            }
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "overview" ? <OverviewTab /> : null}
      {tab === "domains" ? <DomainsTab /> : null}
      {tab === "people" ? <PeopleTab /> : null}
      {tab === "work" ? <WorkTab /> : null}
      {tab === "activity" ? <ActivityTab /> : null}
    </div>
  );
}
