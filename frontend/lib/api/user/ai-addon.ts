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

const routes = {
  health: "/api/ai/health",
  status: "/api/ai/status",
  adminConfig: "/api/ai/admin/config",
  adminConfigToggle: (configId: number | string) => `/api/ai/admin/config/${configId}/toggle`,
  preferences: "/api/ai/preferences",
  seedRatings: "/api/ai/preferences/seed-ratings",
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
}
