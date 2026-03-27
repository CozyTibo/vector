import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { readErrorDetail } from "../lib/canonicalApi";
import { fetchMe, productApiBase } from "../lib/meApi";

export default function SignupPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const already = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });

  const register = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/auth/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName.trim() || null,
          company_name: company.trim() || null,
        }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: async () => {
      setNotice(null);
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate("/app/onboarding", { replace: true });
    },
    onError: (e: Error) => {
      setNotice(e.message);
    },
  });

  if (already.data) {
    return <Navigate to="/app" replace />;
  }

  return (
    <div className="min-h-screen bg-stone-50 px-4 py-16">
      <div className="mx-auto max-w-sm">
        <h1 className="mb-2 text-xl font-semibold text-stone-900">Sign up</h1>
        <p className="mb-6 text-sm text-stone-600">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-600 underline">
            Sign in
          </Link>
        </p>
        {notice ? (
          <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {notice}
          </p>
        ) : null}
        <label className="mb-3 block text-sm text-stone-700">
          Email
          <input
            type="email"
            autoComplete="email"
            className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="mb-3 block text-sm text-stone-700">
          Password
          <input
            type="password"
            autoComplete="new-password"
            className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="mb-3 block text-sm text-stone-700">
          Full name <span className="font-normal text-stone-500">(optional)</span>
          <input
            type="text"
            className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
        <label className="mb-6 block text-sm text-stone-700">
          Company <span className="font-normal text-stone-500">(optional)</span>
          <input
            type="text"
            className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={register.isPending}
          className="w-full rounded-lg bg-stone-900 py-2.5 text-sm font-medium text-white disabled:opacity-60"
          onClick={() => register.mutate()}
        >
          {register.isPending ? "Creating…" : "Create account"}
        </button>
        <p className="mt-6 text-center text-xs text-stone-500">
          <a className="text-blue-600 underline" href={`${apiBase}/auth/google/start`}>
            Sign up with Google
          </a>
        </p>
        <p className="mt-4 text-center text-sm">
          <Link to="/" className="text-stone-600 underline">
            ← Home
          </Link>
        </p>
      </div>
    </div>
  );
}
