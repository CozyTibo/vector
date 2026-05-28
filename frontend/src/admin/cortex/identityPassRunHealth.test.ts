import { describe, expect, it } from "vitest";

import type { IdentityReadiness } from "../cortexAdminTypes";
import { IDENTITY_PASS_STALE_MS, isIdentityPassRunStale } from "./identityPassRunHealth";

function readiness(overrides: Partial<IdentityReadiness> = {}): IdentityReadiness {
  return {
    tenant_id: "t",
    actor_count: 1,
    identity_count: 1,
    linked_account_count: 1,
    unresolved_actor_count: 0,
    dirty_queue_depth: 0,
    latest_pass_run: null,
    scheduler: { enabled: true, interval_seconds: 300 },
    ...overrides,
  };
}

describe("isIdentityPassRunStale", () => {
  it("is false when scheduler is disabled", () => {
    expect(
      isIdentityPassRunStale(
        readiness({ scheduler: { enabled: false, interval_seconds: 300 }, latest_pass_run: null }),
      ),
    ).toBe(false);
  });

  it("is true when scheduler is on and there is no run", () => {
    expect(isIdentityPassRunStale(readiness({ latest_pass_run: null }))).toBe(true);
  });

  it("is false when the latest run started within 10 minutes", () => {
    const started = new Date(Date.now() - IDENTITY_PASS_STALE_MS + 60_000).toISOString();
    expect(
      isIdentityPassRunStale(
        readiness({
          latest_pass_run: {
            id: "1",
            status: "COMPLETED",
            source_trigger: "scheduled",
            started_at: started,
            finished_at: started,
            error_summary: null,
            stats: {},
          },
        }),
      ),
    ).toBe(false);
  });

  it("is true when the latest run started more than 10 minutes ago", () => {
    const started = new Date(Date.now() - IDENTITY_PASS_STALE_MS - 1).toISOString();
    expect(
      isIdentityPassRunStale(
        readiness({
          latest_pass_run: {
            id: "1",
            status: "COMPLETED",
            source_trigger: "scheduled",
            started_at: started,
            finished_at: started,
            error_summary: null,
            stats: {},
          },
        }),
      ),
    ).toBe(true);
  });
});
