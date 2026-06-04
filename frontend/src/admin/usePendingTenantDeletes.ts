import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import { adminJson } from "../lib/adminFetch";
import {
  addPendingTenantDeletes,
  readPendingTenantDeletes,
  removePendingTenantDelete,
  type PendingTenantDelete,
  writePendingTenantDeletes,
} from "./pendingTenantDeletes";

type TenantListItem = { id: string; company_name: string };

type HardDeleteJobStatus = {
  task_id: string;
  celery_state: string;
  ready: boolean;
  deleted_count: number | null;
  error: string | null;
  errors: { tenant_id: string; error: string }[] | null;
};

const POLL_MS = 3000;

export function usePendingTenantDeletes() {
  const qc = useQueryClient();
  const [pending, setPending] = useState<PendingTenantDelete[]>(() => readPendingTenantDeletes());
  const [jobError, setJobError] = useState<string | null>(null);

  const syncFromStorage = useCallback(() => {
    setPending(readPendingTenantDeletes());
  }, []);

  const enqueue = useCallback((rows: PendingTenantDelete[]) => {
    addPendingTenantDeletes(rows);
    syncFromStorage();
    setJobError(null);
    void qc.invalidateQueries({ queryKey: ["admin-tenants"] });
  }, [qc, syncFromStorage]);

  const tenantsQ = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => adminJson<{ items: TenantListItem[] }>("/admin/tenants"),
    refetchInterval: pending.length > 0 ? POLL_MS : false,
  });

  const taskIds = useMemo(
    () => [...new Set(pending.map((p) => p.task_id))],
    [pending],
  );

  useEffect(() => {
    if (pending.length === 0 || !tenantsQ.data) {
      return;
    }
    const liveIds = new Set(tenantsQ.data.items.map((t) => t.id));
    let removed = false;
    for (const row of pending) {
      if (!liveIds.has(row.id)) {
        removePendingTenantDelete(row.id);
        removed = true;
      }
    }
    if (removed) {
      syncFromStorage();
    }
  }, [pending, tenantsQ.data, syncFromStorage]);

  useEffect(() => {
    if (pending.length === 0 || taskIds.length === 0) {
      return;
    }
    let cancelled = false;

    const pollJobs = async () => {
      for (const taskId of taskIds) {
        try {
          const status = await adminJson<HardDeleteJobStatus>(
            `/admin/tenants/hard-delete-jobs/${encodeURIComponent(taskId)}`,
          );
          if (cancelled) {
            return;
          }
          if (status.ready && status.celery_state === "FAILURE") {
            const detail =
              status.error ??
              status.errors?.map((e) => `${e.tenant_id}: ${e.error}`).join("; ") ??
              "Background delete failed.";
            setJobError(detail);
          }
        } catch {
          /* ignore transient poll errors */
        }
      }
    };

    void pollJobs();
    const timer = window.setInterval(() => void pollJobs(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pending.length, taskIds]);

  const clearAll = useCallback(() => {
    writePendingTenantDeletes([]);
    syncFromStorage();
    setJobError(null);
  }, [syncFromStorage]);

  const dismissJobError = useCallback(() => {
    setJobError(null);
  }, []);

  const visibleTenants = useCallback(
    (items: TenantListItem[]) => items.filter((t) => !pending.some((p) => p.id === t.id)),
    [pending],
  );

  return {
    pending,
    jobError,
    enqueue,
    clearAll,
    dismissJobError,
    visibleTenants,
    isDeleting: pending.length > 0,
  };
}
