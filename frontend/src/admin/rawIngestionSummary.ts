/**
 * Human-readable summary for Step 1 raw ingestion rows (admin UX).
 */

function trunc(s: string, max: number): string {
  const t = s.trim();
  if (t.length <= max) {
    return t;
  }
  return `${t.slice(0, max - 1)}…`;
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

function strField(o: Record<string, unknown>, key: string): string | undefined {
  const v = o[key];
  return typeof v === "string" && v.length > 0 ? v : undefined;
}

function metaLines(
  apiEndpoint: string,
  queryParams: Record<string, unknown>,
): string[] {
  const out: string[] = [];
  const op = typeof queryParams.operation === "string" ? queryParams.operation : undefined;
  if (op) {
    out.push(`Operation: ${op}`);
  }
  if (apiEndpoint) {
    out.push(`Endpoint: ${apiEndpoint}`);
  }
  return out;
}

function linearViewerSummary(payload: Record<string, unknown>): { headline: string; bullets: string[] } {
  const data = asRecord(payload.data);
  const viewer = data ? asRecord(data.viewer) : null;
  const name = viewer ? strField(viewer, "name") : undefined;
  const org = viewer ? asRecord(viewer.organization) : null;
  const orgName = org ? strField(org, "name") : undefined;
  const bullets: string[] = [];
  if (orgName) {
    bullets.push(`Organization: ${orgName}`);
  }
  const em = viewer?.email;
  if (typeof em === "string" && em) {
    bullets.push(`Email: ${em}`);
  }
  return {
    headline: name ?? "Linear viewer",
    bullets,
  };
}

export function summarizeRawIngestionDetail(input: {
  resourceType: string;
  externalId: string;
  apiEndpoint: string;
  queryParams: Record<string, unknown>;
  payloadBody: Record<string, unknown>;
}): { headline: string; bullets: string[] } {
  const { resourceType, externalId, apiEndpoint, queryParams, payloadBody } = input;
  const meta = metaLines(apiEndpoint, queryParams);

  if (resourceType === "linear.viewer") {
    const v = linearViewerSummary(payloadBody);
    return { headline: v.headline, bullets: [...v.bullets, ...meta] };
  }

  if (resourceType.startsWith("linear.")) {
    const lines: string[] = [];
    const identifier = strField(payloadBody, "identifier");
    const title = strField(payloadBody, "title");
    const name = strField(payloadBody, "name");
    const key = strField(payloadBody, "key");
    const body = strField(payloadBody, "body");

    if (identifier) {
      lines.push(`Key: ${identifier}`);
    }
    if (title) {
      lines.push(trunc(title, 160));
    } else if (name && resourceType !== "linear.issue") {
      lines.push(name);
    } else if (key) {
      lines.push(`Team key: ${key}`);
    }

    const state = asRecord(payloadBody.state);
    const stateName = state ? strField(state, "name") : undefined;
    if (stateName) {
      lines.push(`Status: ${stateName}`);
    }

    const team = asRecord(payloadBody.team);
    const teamLabel = team ? strField(team, "name") ?? strField(team, "key") : undefined;
    if (teamLabel) {
      lines.push(`Team: ${teamLabel}`);
    }

    const assignee = asRecord(payloadBody.assignee);
    if (assignee && strField(assignee, "name")) {
      lines.push(`Assignee: ${assignee.name as string}`);
    }

    const reporter = asRecord(payloadBody.creator);
    if (resourceType === "linear.issue" && reporter && strField(reporter, "name")) {
      lines.push(`Reporter: ${reporter.name as string}`);
    }

    const project = asRecord(payloadBody.project);
    if (project && strField(project, "name")) {
      lines.push(`Project: ${project.name as string}`);
    }

    const cycle = asRecord(payloadBody.cycle);
    if (cycle) {
      const cn = strField(cycle, "name");
      const cnum = cycle.number;
      if (cn || typeof cnum === "number") {
        lines.push(`Cycle: ${cn ?? `#${String(cnum)}`}`);
      }
    }

    if (resourceType !== "linear.issue") {
      const user =
        asRecord(payloadBody.user) ??
        asRecord(payloadBody.creator) ??
        asRecord(payloadBody.lead);
      if (user && strField(user, "name")) {
        lines.push(`Person: ${user.name as string}`);
      }
      const email = user && strField(user, "email");
      if (email) {
        lines.push(`Email: ${email}`);
      }
    }

    const issue = asRecord(payloadBody.issue);
    if (issue) {
      const ik = strField(issue, "identifier") ?? strField(issue, "id");
      if (ik) {
        lines.push(`Issue: ${ik}`);
      }
    }

    const relType = strField(payloadBody, "type");
    if (resourceType === "linear.issue_relation" && relType) {
      lines.push(`Relation type: ${relType}`);
    }
    const related = asRecord(payloadBody.relatedIssue);
    if (related && strField(related, "identifier")) {
      lines.push(`Other issue: ${related.identifier as string}`);
    }

    if (resourceType === "linear.comment" && body) {
      lines.push(`Comment: ${trunc(body, 220)}`);
    }

    const color = strField(payloadBody, "color");
    if (resourceType === "linear.issue_label" && color) {
      lines.push(`Color: ${color}`);
    }

    if (resourceType === "linear.workflow_state") {
      const st = strField(payloadBody, "type");
      if (st) {
        lines.push(`Workflow type: ${st}`);
      }
    }

    if (resourceType === "linear.cycle") {
      const num = payloadBody.number;
      if (typeof num === "number") {
        lines.push(`Cycle number: ${num}`);
      }
      const starts = strField(payloadBody, "startsAt");
      const ends = strField(payloadBody, "endsAt");
      if (starts && ends) {
        lines.push(`${starts} → ${ends}`);
      }
    }

    if (resourceType === "linear.project") {
      const pteam = asRecord(payloadBody.team);
      if (pteam && (strField(pteam, "name") || strField(pteam, "key"))) {
        lines.push(`Owning team: ${strField(pteam, "name") ?? strField(pteam, "key")}`);
      }
      const pLead = asRecord(payloadBody.lead);
      if (pLead && strField(pLead, "name")) {
        lines.push(`Project lead: ${pLead.name as string}`);
      }
    }

    if (resourceType === "linear.initiative") {
      const desc = strField(payloadBody, "description");
      if (desc) {
        lines.push(trunc(desc, 200));
      }
      const owner = asRecord(payloadBody.owner) ?? asRecord(payloadBody.lead);
      if (owner && strField(owner, "name")) {
        lines.push(`Owner: ${owner.name as string}`);
      }
    }

    const parent = asRecord(payloadBody.parent);
    if (parent && resourceType === "linear.issue") {
      const pe = strField(parent, "identifier") ?? strField(parent, "title");
      const pLead = asRecord(parent.lead);
      if (pe) {
        lines.push(`Parent epic: ${pe}`);
      }
      if (pLead && strField(pLead, "name")) {
        lines.push(`Epic lead: ${pLead.name as string}`);
      }
    }

    const headline =
      title ??
      name ??
      identifier ??
      key ??
      (externalId.length > 12 ? `${externalId.slice(0, 8)}…` : externalId);

    return { headline, bullets: [...lines, ...meta] };
  }

  if (resourceType.startsWith("github.")) {
    const lines: string[] = [];
    const fullName = strField(payloadBody, "full_name");
    const ghTitle = strField(payloadBody, "title");
    const num = payloadBody.number;
    const sha = strField(payloadBody, "sha");
    const htmlUrl = strField(payloadBody, "html_url");

    if (resourceType === "github.repository" && fullName) {
      const desc = strField(payloadBody, "description");
      if (desc) {
        lines.push(trunc(desc, 200));
      }
      return { headline: fullName, bullets: [...lines, ...meta] };
    }

    if (resourceType === "github.pull_request") {
      const n = typeof num === "number" ? `#${num}` : "";
      const h = ghTitle ? `${n} ${ghTitle}`.trim() : `Pull request ${n || externalId}`;
      if (htmlUrl) {
        lines.push(htmlUrl);
      }
      const state = strField(payloadBody, "state");
      if (state) {
        lines.push(`State: ${state}`);
      }
      return { headline: trunc(h, 100), bullets: [...lines, ...meta] };
    }

    if (resourceType === "github.issue") {
      const h = ghTitle ?? `Issue ${typeof num === "number" ? `#${num}` : externalId}`;
      if (htmlUrl) {
        lines.push(htmlUrl);
      }
      return { headline: trunc(h, 100), bullets: [...lines, ...meta] };
    }

    if (resourceType === "github.commit" && sha) {
      const commit = asRecord(payloadBody.commit);
      const msg = commit ? strField(commit, "message") : undefined;
      const firstLine = msg ? (msg.split("\n")[0] ?? msg) : "";
      lines.push(sha.slice(0, 7));
      if (htmlUrl) {
        lines.push(htmlUrl);
      }
      return {
        headline: trunc(firstLine || sha.slice(0, 12), 100),
        bullets: [...lines, ...meta],
      };
    }

    if (resourceType === "github.pull_request_commit" && sha) {
      return {
        headline: `Commit ${sha.slice(0, 7)}`,
        bullets: [trunc(externalId, 140), ...meta],
      };
    }

    return { headline: resourceType, bullets: [`external_id: ${externalId}`, ...meta] };
  }

  return {
    headline: resourceType,
    bullets: [`external_id: ${externalId}`, ...meta],
  };
}
