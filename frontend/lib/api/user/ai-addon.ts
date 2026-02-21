import { BaseAPI } from "../base/base-clients";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";

export interface AddonHealthResponse {
  status: string;
  addonVersion: string;
  databaseOk: boolean;
  mealieApiOk: boolean;
  configSummary: Record<string, unknown>;
}

export interface AddonStatusResponse {
  enabled: boolean;
}

const routes = {
  health: "/api/ai/health",
  status: "/api/ai/status",
  adminConfig: "/api/ai/admin/config",
  adminConfigToggle: (configId: number | string) => `/api/ai/admin/config/${configId}/toggle`,
};

export class AiAddonApi extends BaseAPI {
  constructor(requests: ApiRequestInstance) {
    super(requests);
  }

  async getHealth() {
    return this.requests.get<AddonHealthResponse>(routes.health);
  }

  async getStatus(householdId?: string) {
    const url = householdId
      ? `${routes.status}?household_id=${encodeURIComponent(householdId)}`
      : routes.status;
    return this.requests.get<AddonStatusResponse>(url);
  }

  async getAdminConfig() {
    return this.requests.get<unknown[]>(routes.adminConfig);
  }

  async toggleConfig(configId: number | string) {
    return this.requests.put<AddonStatusResponse, Record<string, never>>(
      routes.adminConfigToggle(configId),
      {},
    );
  }
}
