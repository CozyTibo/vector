/** Phase 08 Step 23 — SPA route registry for synthesis admin surfaces. */

export type SynthesisCatalogSurface = {
  title: string;
  description: string;
  endpoint: string;
};

export const SYNTHESIS_CATALOG_SURFACES: Record<string, SynthesisCatalogSurface> = {
  coverage: {
    title: "Coverage panel",
    description: "Eligible vs synthesized scopes and publication epoch lag.",
    endpoint: "/coverage",
  },
  policy: {
    title: "Policy pack inspector",
    description: "Job contract, caps, and LLM model routes (doctrine catalog).",
    endpoint: "/legality-matrix",
  },
  degradation: {
    title: "Degradation topology",
    description: "SD-* codes, RD→SD matrix, and omission histogram.",
    endpoint: "/degradation-topology",
  },
  omissions: {
    title: "SD omission explorer",
    description: "Process-wide SD histogram and remediation links.",
    endpoint: "/omissions",
  },
  replay: {
    title: "Replay explorer",
    description: "Twin diff law, recent jobs, replay prove (W2).",
    endpoint: "/replay-explorer",
  },
  legality: {
    title: "Legality explorer",
    description: "S-LEG predicates and jobs-by-legality histogram.",
    endpoint: "/legality-matrix",
  },
  runtimeLegality: {
    title: "Runtime legality matrix",
    description: "Production gates, SYN-FORB detector, and PROD-SYN-01 certification.",
    endpoint: "/runtime-legality-matrix",
  },
  evaluation: {
    title: "Evaluation explorer",
    description: "G-P08-EVAL-01 citation coverage and G-P08-EVAL-02 wording drift (non-blocking).",
    endpoint: "/evaluation",
  },
  certification: {
    title: "Certification pack",
    description: "SYNTHESIS-CERT-PACK-1 closure snapshot and archive digest.",
    endpoint: "/certification-pack",
  },
  programClosure: {
    title: "Program closure",
    description: "FF-P08-5 completion criteria and operator checklist.",
    endpoint: "/program-closure",
  },
  observability: {
    title: "Throughput / latency",
    description: "Job duration, tokens, queue depth proxies.",
    endpoint: "/observability",
  },
  artifacts: {
    title: "Artifact explorer",
    description: "Tenant artifacts with claims and publication state.",
    endpoint: "/artifact-explorer",
  },
};

export const SYNTHESIS_NAV_SECTIONS = [
  { key: "", label: "Overview", end: true as const },
  { key: "workflows", label: "Workflows", end: true as const },
  { key: "jobs", label: "Jobs", end: true as const },
  { key: "artifacts", label: "Artifacts", end: true as const },
  { key: "replay", label: "Replay", end: true as const },
  { key: "omissions", label: "Omissions", end: true as const },
  { key: "degradation", label: "Degradation", end: true as const },
  { key: "legality", label: "Legality", end: true as const },
  { key: "runtime-legality", label: "Runtime legality", end: true as const },
  { key: "evaluation", label: "Evaluation", end: true as const },
  { key: "coverage", label: "Coverage", end: true as const },
  { key: "observability", label: "Observability", end: true as const },
  { key: "control-plane", label: "Control plane", end: true as const },
  { key: "certification", label: "Certification", end: true as const },
  { key: "program-closure", label: "Program closure", end: true as const },
  { key: "resynthesize", label: "Re-synth", end: true as const },
] as const;
