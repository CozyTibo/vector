const STORAGE_KEY = "admin-pending-tenant-deletes";

export type PendingTenantDelete = {
  id: string;
  company_name: string;
  task_id: string;
};

export function readPendingTenantDeletes(): PendingTenantDelete[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (row): row is PendingTenantDelete =>
        typeof row === "object" &&
        row !== null &&
        typeof (row as PendingTenantDelete).id === "string" &&
        typeof (row as PendingTenantDelete).company_name === "string" &&
        typeof (row as PendingTenantDelete).task_id === "string",
    );
  } catch {
    return [];
  }
}

export function writePendingTenantDeletes(rows: PendingTenantDelete[]): void {
  if (rows.length === 0) {
    sessionStorage.removeItem(STORAGE_KEY);
    return;
  }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
}

export function addPendingTenantDeletes(rows: PendingTenantDelete[]): void {
  const existing = readPendingTenantDeletes();
  const byId = new Map(existing.map((r) => [r.id, r]));
  for (const row of rows) {
    byId.set(row.id, row);
  }
  writePendingTenantDeletes([...byId.values()]);
}

export function removePendingTenantDelete(id: string): void {
  writePendingTenantDeletes(readPendingTenantDeletes().filter((r) => r.id !== id));
}
