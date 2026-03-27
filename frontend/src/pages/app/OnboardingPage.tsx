import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  completeOnboarding,
  fetchOnboarding,
  patchOnboarding,
  triggerGithubSync,
  type OnboardingStep,
} from "../../lib/onboardingApi";
import { fetchMe, productApiBase } from "../../lib/meApi";

const PRE_CONNECT_STEPS = 4;

const STACK_GROUPS: {
  key: string;
  label: string;
  items: { id: string; label: string }[];
}[] = [
  {
    key: "engineering",
    label: "Engineering",
    items: [
      { id: "github", label: "GitHub" },
      { id: "gitlab", label: "GitLab" },
      { id: "bitbucket", label: "Bitbucket" },
      { id: "azure_devops", label: "Azure DevOps" },
    ],
  },
  {
    key: "project_management",
    label: "Project management",
    items: [
      { id: "linear", label: "Linear" },
      { id: "jira", label: "Jira" },
      { id: "clickup", label: "ClickUp" },
      { id: "asana", label: "Asana" },
      { id: "monday", label: "Monday" },
    ],
  },
  {
    key: "communication",
    label: "Communication",
    items: [
      { id: "slack", label: "Slack" },
      { id: "ms_teams", label: "Microsoft Teams" },
      { id: "discord", label: "Discord" },
    ],
  },
  {
    key: "documentation",
    label: "Documentation",
    items: [
      { id: "notion", label: "Notion" },
      { id: "confluence", label: "Confluence" },
      { id: "coda", label: "Coda" },
      { id: "google_docs", label: "Google Docs" },
    ],
  },
  {
    key: "sales_crm",
    label: "Sales / CRM",
    items: [
      { id: "salesforce", label: "Salesforce" },
      { id: "hubspot", label: "HubSpot" },
      { id: "pipedrive", label: "Pipedrive" },
    ],
  },
  {
    key: "support",
    label: "Support",
    items: [
      { id: "zendesk", label: "Zendesk" },
      { id: "intercom", label: "Intercom" },
      { id: "freshdesk", label: "Freshdesk" },
    ],
  },
];

function emptyStackByCategory(): Record<string, string[]> {
  return Object.fromEntries(STACK_GROUPS.map((g) => [g.key, [] as string[]])) as Record<string, string[]>;
}

function toolsStackFromAnswers(answers: Record<string, unknown>): { byCategory: Record<string, string[]>; other: string } {
  const byCategory = emptyStackByCategory();
  let other = "";
  const raw = answers.tools_stack;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return { byCategory, other };
  }
  const o = raw as Record<string, unknown>;
  if (typeof o.other === "string") {
    other = o.other;
  }
  for (const g of STACK_GROUPS) {
    const arr = o[g.key];
    if (Array.isArray(arr)) {
      byCategory[g.key] = arr.filter((x): x is string => typeof x === "string");
    }
  }
  return { byCategory, other };
}

function serializeToolsStack(byCategory: Record<string, string[]>, other: string): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const g of STACK_GROUPS) {
    const ids = [...(byCategory[g.key] ?? [])].sort();
    if (ids.length > 0) {
      out[g.key] = ids;
    }
  }
  const t = other.trim();
  if (t) {
    out.other = t;
  }
  return out;
}

const TOOL_GROUPS: { category: string; items: { id: string; label: string; hint?: string }[] }[] = [
  {
    category: "Engineering",
    items: [
      { id: "github", label: "GitHub" },
      { id: "gitlab", label: "GitLab", hint: "Soon" },
    ],
  },
  {
    category: "Project management",
    items: [
      { id: "linear", label: "Linear" },
      { id: "jira", label: "Jira", hint: "Soon" },
    ],
  },
  {
    category: "Communication",
    items: [{ id: "slack", label: "Slack", hint: "Soon" }],
  },
  {
    category: "Documentation",
    items: [{ id: "notion", label: "Notion", hint: "Soon" }],
  },
];

function connectableConnectorIds(): Set<string> {
  return new Set(
    TOOL_GROUPS.flatMap((g) => g.items.filter((item) => !item.hint).map((item) => item.id)),
  );
}

/** Stack-discovery selections that match a live connector on the “connect first” step (order = stack survey order). */
function connectableIdsFromToolsStack(answers: Record<string, unknown>): string[] {
  const connectable = connectableConnectorIds();
  const { byCategory } = toolsStackFromAnswers(answers);
  const ordered: string[] = [];
  const seen = new Set<string>();
  for (const g of STACK_GROUPS) {
    for (const id of byCategory[g.key] ?? []) {
      if (!connectable.has(id) || seen.has(id)) {
        continue;
      }
      seen.add(id);
      ordered.push(id);
    }
  }
  return ordered;
}

function toolsInterestOrdered(answers: Record<string, unknown>): string[] {
  const raw = answers.tools_interest;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((x): x is string => typeof x === "string");
}

/** Merges saved `tools_interest` with stack-discovery hints for connector preselection. */
function mergeToolsSelectionFromAnswers(answers: Record<string, unknown>): Set<string> {
  const connectable = connectableConnectorIds();
  const fromInterest = toolsInterestOrdered(answers).filter((id) => connectable.has(id));
  const fromStack = connectableIdsFromToolsStack(answers);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of fromInterest) {
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);
    out.push(id);
  }
  for (const id of fromStack) {
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);
    out.push(id);
  }
  return new Set(out);
}

type LiveConnectorId = "github" | "linear";

function isLiveConnector(id: string): id is LiveConnectorId {
  return id === "github" || id === "linear";
}

/** Preserves UI selection order; only GitHub and Linear are connectable today. */
function connectQueueFromToolsInterest(toolsInterestOrdered: string[]): LiveConnectorId[] {
  return toolsInterestOrdered.filter(isLiveConnector);
}

function connectPlanFromAnswers(answers: Record<string, unknown>, currentStep: string): string[] {
  const p = answers.connect_plan;
  if (Array.isArray(p) && p.length > 0) {
    return p as string[];
  }
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    return [...(q as string[])];
  }
  if (currentStep === "CONNECT_GITHUB") {
    return ["github"];
  }
  if (currentStep === "CONNECT_LINEAR") {
    return ["linear"];
  }
  return [];
}

function effectiveConnectQueue(answers: Record<string, unknown>, currentStep: string): string[] {
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    return [...(q as string[])];
  }
  if (currentStep === "CONNECT_GITHUB") {
    return ["github"];
  }
  if (currentStep === "CONNECT_LINEAR") {
    return ["linear"];
  }
  return [];
}

function normalizeQueueAfterOAuth(
  answers: Record<string, unknown>,
  currentStep: string,
  provider: LiveConnectorId,
): string[] {
  let queue: string[] = [];
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    queue = [...(q as string[])];
  }
  if (queue.length === 0) {
    if (currentStep === "CONNECT_GITHUB" && provider === "github") {
      queue = ["github"];
    } else if (currentStep === "CONNECT_LINEAR" && provider === "linear") {
      queue = ["linear"];
    }
  }
  if (queue[0] === provider) {
    return queue.slice(1);
  }
  return queue.filter((p) => p !== provider);
}

export default function OnboardingPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const me = useQuery({ queryKey: ["me", apiBase], queryFn: () => fetchMe(apiBase) });

  const ob = useQuery({
    queryKey: ["onboarding", apiBase],
    queryFn: () => fetchOnboarding(apiBase),
  });

  const [companyName, setCompanyName] = useState("");
  const [companyDomain, setCompanyDomain] = useState("");
  const [stackByCategory, setStackByCategory] = useState<Record<string, string[]>>(() => emptyStackByCategory());
  const [stackOther, setStackOther] = useState("");
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());
  const [scanBlurb, setScanBlurb] = useState(0);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanRetry, setScanRetry] = useState(0);
  const scanStarted = useRef(false);

  const server = ob.data;
  const displayStep: OnboardingStep | null = useMemo(() => {
    if (!server) {
      return null;
    }
    if (server.status === "completed") {
      return "THANK_YOU";
    }
    return server.current_step as OnboardingStep;
  }, [server]);

  const thankYou = Boolean(server && (server.status === "completed" || displayStep === "THANK_YOU"));

  const progress = useMemo(() => {
    if (!server || thankYou) {
      return { current: 0, total: 0 };
    }
    const plan = connectPlanFromAnswers(server.answers, server.current_step);
    const connectCount = plan.length;
    const total = PRE_CONNECT_STEPS + Math.max(connectCount, 1) + 1;
    const st = displayStep!;
    let current = 1;
    if (st === "WELCOME") {
      current = 1;
    } else if (st === "COMPANY_INFO") {
      current = 2;
    } else if (st === "TOOL_STACK_DISCOVERY") {
      current = 3;
    } else if (st === "TOOLS_SELECTION") {
      current = 4;
    } else if (st === "CONNECT_GITHUB" || st === "CONNECT_LINEAR") {
      const queue = effectiveConnectQueue(server.answers, server.current_step);
      const done = connectCount - queue.length;
      current = PRE_CONNECT_STEPS + Math.max(done, 0) + 1;
    } else if (st === "SCANNING") {
      current = PRE_CONNECT_STEPS + connectCount + 1;
    }
    return { current, total };
  }, [server, displayStep, thankYou]);

  const wantsGithubSync = useMemo(() => {
    if (!server) {
      return false;
    }
    const ti = server.answers.tools_interest;
    return Array.isArray(ti) && ti.includes("github");
  }, [server]);

  const selectedLiveConnectors = useMemo(
    () => connectQueueFromToolsInterest(Array.from(selectedTools)),
    [selectedTools],
  );

  useEffect(() => {
    if (!me.data) {
      return;
    }
    setCompanyName((prev) => (prev ? prev : me.data!.company_name));
  }, [me.data]);

  useEffect(() => {
    if (!server) {
      return;
    }
    setSelectedTools(mergeToolsSelectionFromAnswers(server.answers));
    const cn = server.answers.company_name;
    if (typeof cn === "string" && cn.trim()) {
      setCompanyName(cn.trim());
    }
    const cd = server.answers.company_domain;
    if (typeof cd === "string") {
      setCompanyDomain(cd);
    }
    const { byCategory, other } = toolsStackFromAnswers(server.answers);
    setStackByCategory(byCategory);
    setStackOther(other);
  }, [server?.id, server?.version]);

  const patchMut = useMutation({
    mutationFn: (body: Parameters<typeof patchOnboarding>[1]) => patchOnboarding(apiBase, body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["onboarding", apiBase] }),
  });

  const goToStep = useCallback(
    (step: OnboardingStep, answers?: Record<string, unknown>) => {
      patchMut.mutate({ current_step: step, answers });
    },
    [patchMut],
  );

  const continueAfterManualConnect = useCallback(
    (provider: LiveConnectorId) => {
      if (!server) {
        return;
      }
      const queue = effectiveConnectQueue(server.answers, server.current_step);
      if (queue[0] !== provider) {
        return;
      }
      const rest = queue.slice(1);
      if (rest.length === 0) {
        goToStep("SCANNING", { connect_queue: [] });
      } else {
        const next = rest[0];
        goToStep(next === "github" ? "CONNECT_GITHUB" : "CONNECT_LINEAR", { connect_queue: rest });
      }
    },
    [server, goToStep],
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gh = params.get("github_connected");
    const lin = params.get("linear_connected");
    if (gh !== "1" && lin !== "1") {
      return;
    }
    const provider: LiveConnectorId = gh === "1" ? "github" : "linear";
    window.history.replaceState({}, "", "/app/onboarding");
    void (async () => {
      try {
        const fresh = await fetchOnboarding(apiBase);
        const nextQueue = normalizeQueueAfterOAuth(fresh.answers, fresh.current_step, provider);
        if (nextQueue.length === 0) {
          await patchOnboarding(apiBase, { current_step: "SCANNING", answers: { connect_queue: [] } });
        } else {
          const next = nextQueue[0];
          await patchOnboarding(apiBase, {
            current_step: NextConnectStep(next),
            answers: { connect_queue: nextQueue },
          });
        }
        await qc.invalidateQueries({ queryKey: ["onboarding", apiBase] });
      } catch {
        /* surfaced by query */
      }
    })();
  }, [apiBase, qc]);

  const scanMessages = [
    "Syncing data from your connected tools…",
    "Processing work activity…",
    "Building your activity graph…",
  ];
  useEffect(() => {
    if (displayStep !== "SCANNING" || server?.status === "completed") {
      return;
    }
    const t = window.setInterval(() => {
      setScanBlurb((i) => (i + 1) % scanMessages.length);
    }, 2200);
    return () => window.clearInterval(t);
  }, [displayStep, server?.status, scanMessages.length]);

  useEffect(() => {
    if (displayStep !== "SCANNING" || server?.status === "completed" || !server) {
      return;
    }
    if (scanStarted.current) {
      return;
    }
    scanStarted.current = true;
    setScanError(null);
    void (async () => {
      try {
        if (wantsGithubSync) {
          if (!server.github_connected) {
            scanStarted.current = false;
            setScanError("GitHub is not connected.");
            return;
          }
          const run = await triggerGithubSync(apiBase);
          if (run.status !== "succeeded" && run.status !== "partial") {
            scanStarted.current = false;
            setScanError(run.error_summary || "Ingestion did not finish successfully.");
            return;
          }
        }
        await completeOnboarding(apiBase);
        await qc.invalidateQueries({ queryKey: ["onboarding", apiBase] });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      } catch (e) {
        scanStarted.current = false;
        setScanError(e instanceof Error ? e.message : "Something went wrong.");
      }
    })();
  }, [apiBase, displayStep, qc, server, wantsGithubSync, scanRetry]);

  useEffect(() => {
    if (displayStep !== "SCANNING") {
      scanStarted.current = false;
    }
  }, [displayStep]);

  if (ob.isPending || !server) {
    return (
      <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4">
        <p className="text-stone-500">Loading…</p>
      </main>
    );
  }

  if (ob.isError) {
    return (
      <main className="mx-auto max-w-lg px-4 py-16">
        <p className="text-red-700">{(ob.error as Error).message}</p>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] px-4 py-12">
      <div
        className="mx-auto max-w-xl transition-[opacity,transform] duration-500 ease-out"
        style={{ opacity: 1, transform: "translateY(0)" }}
      >
        {!thankYou && progress.total > 0 ? (
          <p className="mb-10 text-center text-xs font-medium uppercase tracking-widest text-stone-400">
            Step {progress.current} of {progress.total}
          </p>
        ) : null}

        {thankYou ? (
          <div className="space-y-6 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-stone-900">You&apos;re early. We&apos;re learning with you.</h1>
            <p className="text-lg leading-relaxed text-stone-600">
              You&apos;re in. Vector is processing activity from your connected tools. We&apos;re working with a small group of
              design partners. We&apos;ll be back soon with the first execution insights.
            </p>
            <button
              type="button"
              className="mt-4 rounded-full bg-stone-900 px-8 py-3 text-sm font-medium text-white hover:bg-stone-800"
              onClick={() => navigate("/app/connectors", { replace: true })}
            >
              Go to connectors
            </button>
            <p className="pt-4 text-sm text-stone-500">
              <Link to="/app" className="text-blue-600 underline">
                App home
              </Link>
            </p>
          </div>
        ) : displayStep === "WELCOME" ? (
          <div className="space-y-8 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-stone-900">Let Vector learn how your team works.</h1>
            <div className="space-y-4 text-lg leading-relaxed text-stone-600">
              <p>Your tools already tell the story of how you ship.</p>
              <p>
                We connect to the ones you use and learn from real activity in your engineering, project, and communication
                tools.
              </p>
            </div>
            <button
              type="button"
              className="rounded-full bg-stone-900 px-8 py-3 text-sm font-medium text-white hover:bg-stone-800"
              onClick={() => goToStep("COMPANY_INFO")}
            >
              Continue
            </button>
          </div>
        ) : displayStep === "COMPANY_INFO" ? (
          <div className="space-y-8">
            <div className="text-center">
              <h1 className="text-3xl font-semibold tracking-tight text-stone-900">Who&apos;s this workspace for?</h1>
              <p className="mt-3 text-stone-600">A name and optional domain help us recognize your company later.</p>
            </div>
            <label className="block text-left text-sm text-stone-700">
              Company name
              <input
                className="mt-1.5 w-full rounded-xl border border-stone-200 bg-white px-4 py-3 text-stone-900 outline-none ring-stone-900 focus:ring-2"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                autoComplete="organization"
              />
            </label>
            <label className="block text-left text-sm text-stone-700">
              Website or email domain{" "}
              <span className="font-normal text-stone-400">(optional)</span>
              <input
                className="mt-1.5 w-full rounded-xl border border-stone-200 bg-white px-4 py-3 text-stone-900 outline-none ring-stone-900 focus:ring-2"
                value={companyDomain}
                onChange={(e) => setCompanyDomain(e.target.value)}
                placeholder="acme.com"
                autoComplete="url"
              />
            </label>
            <div className="flex justify-center gap-3 pt-4">
              <button
                type="button"
                className="rounded-full border border-stone-300 px-6 py-2.5 text-sm text-stone-800 hover:bg-stone-50"
                onClick={() => goToStep("WELCOME")}
              >
                Back
              </button>
              <button
                type="button"
                disabled={!companyName.trim() || patchMut.isPending}
                className="rounded-full bg-stone-900 px-8 py-2.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-40"
                onClick={() =>
                  goToStep("TOOL_STACK_DISCOVERY", {
                    company_name: companyName.trim(),
                    company_domain: companyDomain.trim() || undefined,
                  })
                }
              >
                Continue
              </button>
            </div>
          </div>
        ) : displayStep === "TOOL_STACK_DISCOVERY" ? (
          <div className="space-y-8">
            <div className="text-center">
              <h1 className="text-3xl font-semibold tracking-tight text-stone-900">
                Before we start, help us understand your stack.
              </h1>
              <p className="mt-3 text-stone-600 leading-relaxed">
                Which tools does your company use today?
                <br />
                <span className="text-stone-500">
                  This helps us prioritize integrations and adapt Vector to your workflow.
                </span>
              </p>
            </div>
            <div className="space-y-7">
              {STACK_GROUPS.map((g) => {
                const selected = stackByCategory[g.key] ?? [];
                return (
                  <div key={g.key}>
                    <h2 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-stone-400">{g.label}</h2>
                    <div className="flex flex-wrap gap-2">
                      {g.items.map((item) => {
                        const on = selected.includes(item.id);
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() =>
                              setStackByCategory((prev) => {
                                const cur = [...(prev[g.key] ?? [])];
                                const idx = cur.indexOf(item.id);
                                if (idx >= 0) {
                                  cur.splice(idx, 1);
                                } else {
                                  cur.push(item.id);
                                }
                                return { ...prev, [g.key]: cur };
                              })
                            }
                            className={[
                              "rounded-full border px-3.5 py-1.5 text-sm font-medium transition",
                              on
                                ? "border-stone-900 bg-stone-900 text-white"
                                : "border-stone-200 bg-white text-stone-800 hover:border-stone-300",
                            ].join(" ")}
                          >
                            {item.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
            <label className="block text-left text-sm text-stone-700">
              Other tools <span className="font-normal text-stone-400">(optional)</span>
              <input
                className="mt-1.5 w-full rounded-xl border border-stone-200 bg-white px-4 py-3 text-stone-900 outline-none ring-stone-900 focus:ring-2"
                value={stackOther}
                onChange={(e) => setStackOther(e.target.value)}
                placeholder="Anything we should know?"
                autoComplete="off"
              />
            </label>
            <div className="flex justify-center gap-3 pt-2">
              <button
                type="button"
                className="rounded-full border border-stone-300 px-6 py-2.5 text-sm text-stone-800 hover:bg-stone-50"
                onClick={() => goToStep("COMPANY_INFO")}
              >
                Back
              </button>
              <button
                type="button"
                disabled={patchMut.isPending}
                className="rounded-full bg-stone-900 px-8 py-2.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-40"
                onClick={() =>
                  goToStep("TOOLS_SELECTION", {
                    tools_stack: serializeToolsStack(stackByCategory, stackOther),
                    // Drop stale connector prefs so preselection comes only from `tools_stack` (and user toggles).
                    tools_interest: [],
                    connect_plan: [],
                    connect_queue: [],
                  })
                }
              >
                Continue
              </button>
            </div>
          </div>
        ) : displayStep === "TOOLS_SELECTION" ? (
          <div className="space-y-8">
            <div className="text-center">
              <h1 className="text-3xl font-semibold tracking-tight text-stone-900">Which tools should Vector start with?</h1>
              <p className="mt-3 text-stone-600 leading-relaxed">
                Connect the tools you want Vector to learn from first.
                <br />
                You can always add more later.
              </p>
            </div>
            <div className="space-y-8">
              {TOOL_GROUPS.map((g) => (
                <div key={g.category}>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-400">{g.category}</h2>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {g.items.map((item) => {
                      const on = selectedTools.has(item.id);
                      const coming = Boolean(item.hint);
                      return (
                        <button
                          key={item.id}
                          type="button"
                          disabled={coming}
                          onClick={() => {
                            if (coming) {
                              return;
                            }
                            setSelectedTools((prev) => {
                              const n = new Set(prev);
                              if (n.has(item.id)) {
                                n.delete(item.id);
                              } else {
                                n.add(item.id);
                              }
                              return n;
                            });
                          }}
                          className={[
                            "rounded-xl border px-4 py-4 text-left text-sm transition",
                            coming
                              ? "cursor-not-allowed border-stone-100 bg-stone-50 text-stone-400"
                              : on
                                ? "border-stone-900 bg-stone-900 text-white shadow-md"
                                : "border-stone-200 bg-white text-stone-800 hover:border-stone-300",
                          ].join(" ")}
                        >
                          <span className="font-medium">{item.label}</span>
                          {item.hint ? (
                            <span className="mt-1 block text-xs opacity-80">{item.hint}</span>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
            <p className="mx-auto max-w-lg text-center text-sm leading-relaxed text-stone-600">
              For sensitive tools like GitHub or Slack, Vector does not store your code or messages. We only collect execution
              signals that describe how work moves through your connected integrations.
            </p>
            {selectedLiveConnectors.length === 0 ? (
              <p className="text-center text-sm text-amber-800">
                Choose at least one of GitHub or Linear to continue onboarding.
              </p>
            ) : null}
            <div className="flex justify-center gap-3 pt-4">
              <button
                type="button"
                className="rounded-full border border-stone-300 px-6 py-2.5 text-sm text-stone-800 hover:bg-stone-50"
                onClick={() => goToStep("TOOL_STACK_DISCOVERY")}
              >
                Back
              </button>
              <button
                type="button"
                disabled={patchMut.isPending || selectedLiveConnectors.length === 0}
                className="rounded-full bg-stone-900 px-8 py-2.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-40"
                onClick={() => {
                  const order = Array.from(selectedTools);
                  const queue = connectQueueFromToolsInterest(order);
                  const toolsInterest = order;
                  if (queue.length === 0) {
                    return;
                  }
                  const plan = [...queue];
                  const first = queue[0];
                  goToStep(first === "github" ? "CONNECT_GITHUB" : "CONNECT_LINEAR", {
                    tools_interest: toolsInterest,
                    connect_plan: plan,
                    connect_queue: [...queue],
                  });
                }}
              >
                Continue
              </button>
            </div>
          </div>
        ) : displayStep === "CONNECT_GITHUB" ? (
          <div className="space-y-8 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-stone-900">Connect GitHub</h1>
            <p className="text-lg leading-relaxed text-stone-600">
              Install the GitHub app for this workspace so we can sync engineering activity. It only takes a moment.
            </p>
            {server.github_connected ? (
              <p className="text-sm font-medium text-green-700">GitHub is connected.</p>
            ) : null}
            <div className="flex flex-col items-center gap-3 pt-2">
              {!server.github_connected ? (
                <a
                  className="inline-flex rounded-full bg-stone-900 px-8 py-3 text-sm font-medium text-white no-underline hover:bg-stone-800"
                  href={`${apiBase}/connectors/github/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                >
                  Connect GitHub
                </a>
              ) : (
                <button
                  type="button"
                  className="rounded-full bg-stone-900 px-8 py-3 text-sm font-medium text-white hover:bg-stone-800"
                  onClick={() => continueAfterManualConnect("github")}
                >
                  Continue
                </button>
              )}
              <button
                type="button"
                className="text-sm text-stone-500 underline"
                onClick={() => goToStep("TOOLS_SELECTION")}
              >
                Back
              </button>
            </div>
          </div>
        ) : displayStep === "CONNECT_LINEAR" ? (
          <div className="space-y-8 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-stone-900">Connect Linear</h1>
            <p className="text-lg leading-relaxed text-stone-600">
              Authorize Linear for this workspace so we can sync project and issue activity.
            </p>
            {server.linear_connected ? (
              <p className="text-sm font-medium text-green-700">Linear is connected.</p>
            ) : null}
            <div className="flex flex-col items-center gap-3 pt-2">
              {!server.linear_connected ? (
                <a
                  className="inline-flex rounded-full bg-stone-900 px-8 py-3 text-sm font-medium text-white no-underline hover:bg-stone-800"
                  href={`${apiBase}/connectors/linear/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                >
                  Connect Linear
                </a>
              ) : (
                <button
                  type="button"
                  className="rounded-full bg-stone-900 px-8 py-3 text-sm font-medium text-white hover:bg-stone-800"
                  onClick={() => continueAfterManualConnect("linear")}
                >
                  Continue
                </button>
              )}
              <button
                type="button"
                className="text-sm text-stone-500 underline"
                onClick={() => goToStep("TOOLS_SELECTION")}
              >
                Back
              </button>
            </div>
          </div>
        ) : displayStep === "SCANNING" ? (
          <div className="space-y-8 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-stone-900">We&apos;re syncing your workspace</h1>
            <p className="min-h-[1.75rem] text-lg text-stone-600 transition-opacity duration-300">
              {scanMessages[scanBlurb]}
            </p>
            {scanError ? (
              <div className="space-y-4">
                <p className="text-sm text-red-700">{scanError}</p>
                <button
                  type="button"
                  className="rounded-full bg-stone-900 px-6 py-2 text-sm text-white"
                  onClick={() => {
                    scanStarted.current = false;
                    setScanError(null);
                    setScanRetry((n) => n + 1);
                  }}
                >
                  Retry
                </button>
              </div>
            ) : (
              <p className="text-sm text-stone-400">This usually takes under a minute.</p>
            )}
          </div>
        ) : null}
      </div>
    </main>
  );
}

function NextConnectStep(next: string): OnboardingStep {
  return next === "github" ? "CONNECT_GITHUB" : "CONNECT_LINEAR";
}
