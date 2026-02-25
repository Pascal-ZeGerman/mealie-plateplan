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

export interface PreferencesResponse {
  cuisinePreferences: Record<string, "love" | "neutral" | "dislike">;
  allergies: string[];
  dietaryRestrictions: string[];
  familyAdults: number;
  familyTeens: number;
  familyChildren: number;
  familyToddlers: number;
  calculatedPortions: number;
  portionOverride: number | null;
  effectivePortions: number;
  onboardingComplete: boolean;
}

export interface PreferencesUpdate {
  cuisinePreferences?: Record<string, "love" | "neutral" | "dislike">;
  allergies?: string[];
  dietaryRestrictions?: string[];
  familyAdults?: number;
  familyTeens?: number;
  familyChildren?: number;
  familyToddlers?: number;
  portionOverride?: number | null;
  onboardingComplete?: boolean;
}

export interface SeedRatingIn {
  recipeSlug: string;
  recipeName: string;
  rating: number;
}

export interface ProviderKeyStatus {
  provider: string;
  maskedKey: string;
  isValid: boolean;
  validationError?: string | null;
}

export interface ProviderKeyIn {
  provider: string;
  apiKey: string;
}

export interface BudgetStatusResponse {
  spent: number;
  cap: number;
  pct: number;
  alert: boolean;
  resetsOn: string;
}

export interface BudgetConfigIn {
  weeklyCap: number;
}

export interface TaskConfigEntry {
  taskType: string;
  providerTier: string;
}

export interface AvailableTier {
  tier: string;
  provider: string;
  modelId: string;
  displayName: string;
  approxCostPerCall: string;
}

export interface TaskConfigListResponse {
  configs: TaskConfigEntry[];
  availableTiers: AvailableTier[];
}

const routes = {
  health: "/api/ai/health",
  status: "/api/ai/status",
  adminConfig: "/api/ai/admin/config",
  adminConfigToggle: (configId: number | string) => `/api/ai/admin/config/${configId}/toggle`,
  preferences: "/api/ai/preferences",
  seedRatings: "/api/ai/preferences/seed-ratings",
  providerSettings: "/api/ai/provider-settings",
  providerSettingsDelete: (provider: string) => `/api/ai/provider-settings/${provider}`,
  budgetStatus: "/api/ai/budget/status",
  budgetConfig: "/api/ai/budget/config",
  taskConfig: "/api/ai/task-config",
  adminTaskConfig: "/api/ai/admin/task-config",
  adminTaskConfigDelete: (taskType: string) => `/api/ai/admin/task-config/${encodeURIComponent(taskType)}`,
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

  async getPreferences() {
    return this.requests.get<PreferencesResponse>(routes.preferences);
  }

  async updatePreferences(payload: PreferencesUpdate) {
    return this.requests.put<PreferencesResponse, PreferencesUpdate>(routes.preferences, payload);
  }

  async submitSeedRatings(ratings: SeedRatingIn[]) {
    return this.requests.post<void, { ratings: SeedRatingIn[] }>(routes.seedRatings, { ratings });
  }

  async listProviderSettings() {
    return this.requests.get<ProviderKeyStatus[]>(routes.providerSettings);
  }

  async saveProviderKey(payload: ProviderKeyIn) {
    return this.requests.post<ProviderKeyStatus, ProviderKeyIn>(routes.providerSettings, payload);
  }

  async deleteProviderKey(provider: string) {
    return this.requests.delete<void>(routes.providerSettingsDelete(provider));
  }

  async getBudgetStatus() {
    return this.requests.get<BudgetStatusResponse>(routes.budgetStatus);
  }

  async updateBudgetConfig(payload: BudgetConfigIn) {
    return this.requests.put<BudgetStatusResponse, BudgetConfigIn>(routes.budgetConfig, payload);
  }

  async getTaskConfig() {
    return this.requests.get<TaskConfigListResponse>(routes.taskConfig);
  }

  async upsertTaskConfig(payload: TaskConfigEntry) {
    return this.requests.put<TaskConfigEntry, TaskConfigEntry>(routes.adminTaskConfig, payload);
  }

  async deleteTaskConfig(taskType: string) {
    return this.requests.delete<void>(routes.adminTaskConfigDelete(taskType));
  }
}
