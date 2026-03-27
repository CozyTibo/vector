import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { productApiBase } from "../lib/meApi";

export default function LandingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const apiBase = productApiBase();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_ok") === "1") {
      void qc.invalidateQueries({ queryKey: ["me", apiBase] });
      window.history.replaceState({}, "", window.location.pathname);
      navigate("/app", { replace: true });
    }
  }, [apiBase, navigate, qc]);

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <main className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="mb-10 text-2xl font-bold tracking-tight text-stone-900">Vector</div>
        <h1 className="mb-10 max-w-xl text-center text-2xl font-semibold text-stone-800 sm:text-3xl">
          Execution Intelligence
        </h1>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/signup"
            className="rounded-lg bg-stone-900 px-5 py-2.5 text-sm font-medium text-white no-underline hover:bg-stone-800"
          >
            Sign up
          </Link>
          <Link
            to="/login"
            className="rounded-lg border border-stone-300 bg-white px-5 py-2.5 text-sm font-medium text-stone-800 no-underline hover:bg-stone-50"
          >
            Sign in
          </Link>
        </div>
      </main>
    </div>
  );
}
