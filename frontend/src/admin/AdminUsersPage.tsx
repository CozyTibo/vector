import { useQuery } from "@tanstack/react-query";

import { adminJson } from "../lib/adminFetch";
import { OperatorIntro, OperatorSection } from "./ui/OperatorSections";

type UserRow = {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
  has_password: boolean;
};

export default function AdminUsersPage() {
  const q = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminJson<{ items: UserRow[] }>("/admin/users"),
  });

  if (q.isPending) {
    return <p className="mx-auto max-w-6xl px-4 py-8 text-sm text-stone-600">Loading users…</p>;
  }
  if (q.isError) {
    return (
      <p className="mx-auto max-w-6xl px-4 py-8 text-sm text-red-700">{(q.error as Error).message}</p>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <OperatorIntro title="Users">
        All rows in the <code className="rounded bg-stone-100 px-1 py-0.5 text-xs">users</code> table
        (product accounts). Password column is not exposed; “Password” indicates a stored hash exists.
      </OperatorIntro>

      <OperatorSection
        title="Directory"
        description="Newest first. Use workspace cards from Workspaces to see tenant context for a member."
      >
        <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white shadow-sm">
          <table className="min-w-full text-left text-sm text-stone-800">
            <thead className="border-b border-stone-200 bg-stone-50 text-xs font-semibold uppercase tracking-wide text-stone-600">
              <tr>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Full name</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Password</th>
                <th className="px-4 py-3 font-mono text-[11px] font-normal normal-case text-stone-500">
                  user_id
                </th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-stone-500">
                    No users yet.
                  </td>
                </tr>
              ) : (
                q.data.items.map((u) => (
                  <tr key={u.id} className="border-b border-stone-100 last:border-0 hover:bg-stone-50/80">
                    <td className="max-w-[14rem] truncate px-4 py-2.5 font-medium" title={u.email}>
                      {u.email}
                    </td>
                    <td className="max-w-[12rem] truncate px-4 py-2.5 text-stone-600" title={u.full_name ?? ""}>
                      {u.full_name ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-stone-600">
                      {new Date(u.created_at).toLocaleString()}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-stone-600">
                      {u.has_password ? "Yes" : "—"}
                    </td>
                    <td className="max-w-[8rem] truncate px-4 py-2.5 font-mono text-[11px] text-stone-500">
                      {u.id}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </OperatorSection>
    </main>
  );
}
