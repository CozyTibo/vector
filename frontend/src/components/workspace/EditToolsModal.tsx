import { useCallback, useEffect, useState } from "react";

import { ONBOARDING_TOOL_GROUPS, type ToolPickState } from "../onboarding/onboardingToolGroups";
import { ToolLogo } from "./toolLogos";
import { workspacePrimaryButtonCompact } from "./workspaceUiTokens";
import {
  cloneToolPick,
  isLiveConnectorToolId,
  isToolLockedByConnection,
} from "./workspaceStackPick";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Snapshot when the modal opens (onboarding + optional saved edits, merged with connected tools). */
  initialPick: ToolPickState;
  connected: Set<string>;
  onSave: (pick: ToolPickState) => void;
};

export default function EditToolsModal({ open, onClose, initialPick, connected, onSave }: Props) {
  const [draft, setDraft] = useState<ToolPickState>(() => cloneToolPick(initialPick));

  useEffect(() => {
    if (!open) {
      return;
    }
    setDraft(cloneToolPick(initialPick));
  }, [open, initialPick]);

  const toggle = useCallback(
    (groupKey: string, toolId: string) => {
      if (isToolLockedByConnection(toolId, connected)) {
        return;
      }
      setDraft((prev) => {
        const next = cloneToolPick(prev);
        const arr = [...(next[groupKey] ?? [])];
        const i = arr.indexOf(toolId);
        if (i >= 0) {
          arr.splice(i, 1);
        } else {
          arr.push(toolId);
        }
        next[groupKey] = arr;
        return next;
      });
    },
    [connected],
  );

  const handleSave = useCallback(() => {
    onSave(cloneToolPick(draft));
    onClose();
  }, [draft, onSave, onClose]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-tools-title"
    >
      <button type="button" className="absolute inset-0 bg-zinc-900/40" aria-label="Close" onClick={onClose} />
      <div className="relative max-h-[min(90vh,36rem)] w-full max-w-lg overflow-y-auto rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl">
        <h2 id="edit-tools-title" className="text-lg font-semibold text-zinc-900">
          Tools in your stack
        </h2>
        <p className="mt-2 text-sm text-zinc-600">
          Same list as onboarding. Checked tools appear under Connector status; connect or disconnect on each card.
          While a tool is connected, it stays selected here.
        </p>
        <div className="mt-6 space-y-6">
          {ONBOARDING_TOOL_GROUPS.map((group) => (
            <div key={group.key}>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">{group.label}</p>
              <ul className="mt-3 space-y-2">
                {group.items.map((item) => {
                  const checked = (draft[group.key] ?? []).includes(item.id);
                  const locked = isToolLockedByConnection(item.id, connected) && checked;
                  const liveConnector = isLiveConnectorToolId(item.id);
                  return (
                    <li key={`${group.key}:${item.id}`}>
                      <label
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border border-zinc-100 px-3 py-2.5 hover:bg-zinc-50 ${
                          locked ? "cursor-default opacity-100" : ""
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="h-4 w-4 shrink-0 rounded border-zinc-300 accent-zinc-700 focus:ring-2 focus:ring-zinc-400/35 focus:ring-offset-0 disabled:cursor-not-allowed"
                          checked={checked}
                          disabled={locked}
                          onChange={() => toggle(group.key, item.id)}
                        />
                        <ToolLogo toolId={item.id} name={item.label} />
                        <span className="text-sm font-medium text-zinc-900">{item.label}</span>
                        {!liveConnector ? (
                          <span className="text-xs text-zinc-400">Coming soon</span>
                        ) : null}
                      </label>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-6 flex justify-end gap-3 border-t border-zinc-100 pt-4">
          <button
            type="button"
            className="rounded-lg border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className={workspacePrimaryButtonCompact}
            onClick={handleSave}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
