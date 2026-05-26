import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchSubstrateTruth } from "./fetchOperator";
import { operatorKeys } from "./operatorKeys";
import type { SubstrateTruth } from "./operatorTypes";

export function useSubstrateTruth() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.substrateTruth(tenantId),
    queryFn: () => fetchSubstrateTruth(tenantId),
    enabled: Boolean(tenantId),
  });
}

export type { SubstrateTruth };
