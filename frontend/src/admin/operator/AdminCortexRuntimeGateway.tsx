import { Navigate } from "react-router-dom";

import { isCortexAdminV2Enabled } from "./featureFlags";
import OperatorRuntimePage from "./OperatorRuntimePage";

/** Routes operator runtime vs legacy redirect when v2 disabled. */
export default function AdminCortexRuntimeGateway() {
  if (!isCortexAdminV2Enabled()) {
    return <Navigate to=".." replace />;
  }
  return <OperatorRuntimePage />;
}
