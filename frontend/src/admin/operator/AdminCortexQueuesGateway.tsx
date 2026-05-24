import { Navigate } from "react-router-dom";

import { isCortexAdminV2Enabled } from "./featureFlags";
import OperatorQueuesPage from "./OperatorQueuesPage";

export default function AdminCortexQueuesGateway() {
  if (!isCortexAdminV2Enabled()) {
    return <Navigate to=".." replace />;
  }
  return <OperatorQueuesPage />;
}
