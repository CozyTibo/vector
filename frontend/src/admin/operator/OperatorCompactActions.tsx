import { OperatorActionPanel } from "./OperatorActionPanel";

type Props = {
  runnableConnectors: string[];
};

export function OperatorCompactActions({ runnableConnectors }: Props) {
  return <OperatorActionPanel variant="compact" runnableConnectors={runnableConnectors} />;
}
