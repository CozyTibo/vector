import AdminCortexOverviewPage from "../AdminCortexOverviewPage";
import { isCortexAdminV2Enabled } from "./featureFlags";
import OperatorOverviewPage from "./OperatorOverviewPage";

/** Routes legacy bootstrap overview vs operator v2 overview based on frontend flag. */
export default function AdminCortexOverviewGateway() {
  if (isCortexAdminV2Enabled()) {
    return <OperatorOverviewPage />;
  }
  return <AdminCortexOverviewPage />;
}
