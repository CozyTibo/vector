import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { CanonicalSummaryPanels } from "./cortex/CanonicalSummaryPanels";
import { PhasePageShell } from "./cortex/PhasePageShell";

export default function AdminCortexCanonicalHealthPage() {
  return (
    <PhasePageShell
      phase="canonical"
      title="Canonical"
      description="Raw → deterministic canonical rows. Materialization runs on the execution engine only."
      summaryLoadsOwnData
      summaryContent={() => <CanonicalSummaryPanels />}
      explorerContent={<PhaseExplorer phase="canonical" />}
    />
  );
}
