import type { GraphInspectorId } from "./graphInspectorTypes";
import { GRAPH_INSPECTORS } from "./graphInspectorTypes";

type Props = {
  active: GraphInspectorId;
  onChange: (id: GraphInspectorId) => void;
};

export function GraphInspectorNav({ active, onChange }: Props) {
  return (
    <nav className="flex flex-wrap gap-2" aria-label="Graph inspectors">
      {GRAPH_INSPECTORS.map((inspector) => {
        const selected = inspector.id === active;
        return (
          <button
            key={inspector.id}
            type="button"
            onClick={() => onChange(inspector.id)}
            className={[
              "rounded-lg border px-3 py-2 text-left text-sm transition-colors",
              selected
                ? "border-indigo-300 bg-indigo-50 text-indigo-950 shadow-sm"
                : "border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50",
            ].join(" ")}
          >
            <span className="font-medium">{inspector.label}</span>
            <span className="ml-2 text-[10px] uppercase tracking-wide text-stone-400">
              {inspector.phase}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

export function GraphInspectorDescription({ active }: { active: GraphInspectorId }) {
  const inspector = GRAPH_INSPECTORS.find((item) => item.id === active);
  if (!inspector) return null;
  return (
    <p className="text-sm text-stone-600">
      <span className="font-medium text-stone-800">{inspector.label}.</span> {inspector.description}
    </p>
  );
}
