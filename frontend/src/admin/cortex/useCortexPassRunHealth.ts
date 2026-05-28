import { useCanonReadiness } from "./useCanonReadiness";
import { useCortexIngestionOverview } from "./useCortexIngestionOverview";
import { useIdentityReadiness } from "./useIdentityReadiness";
import {
  isCanonPassRunStale,
  isIdentityPassRunStale,
  isIngestionPassRunStale,
} from "./passRunHealth";

/** Stale-run indicators for Cortex top-level nav (Ingestion / Canonical / Identities). */
export function useCortexPassRunHealth() {
  const identityQ = useIdentityReadiness();
  const canonQ = useCanonReadiness();
  const ingestionQ = useCortexIngestionOverview();

  return {
    identityStale: isIdentityPassRunStale(identityQ.data),
    canonStale: isCanonPassRunStale(canonQ.data),
    ingestionStale: isIngestionPassRunStale(ingestionQ.data),
    isLoading: identityQ.isLoading || canonQ.isLoading || ingestionQ.isLoading,
  };
}
