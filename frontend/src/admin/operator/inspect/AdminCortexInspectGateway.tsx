import { Navigate } from "react-router-dom";

import { isCortexAdminV2Enabled } from "../featureFlags";
import AdminCortexInspectLayout from "./AdminCortexInspectLayout";

/** Wraps inspect routes — redirects to overview when v2 disabled. */
export default function AdminCortexInspectGateway() {
  if (!isCortexAdminV2Enabled()) {
    return <Navigate to="../overview" replace />;
  }
  return <AdminCortexInspectLayout />;
}
