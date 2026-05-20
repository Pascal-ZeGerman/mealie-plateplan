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

export interface MealSlotPreview {
  date: string;
  mealType: string;
  slotType: string;
  recipeId: string | null;
  recipeName: string | null;
  recipeSlug: string | null;
  recipeServings: number | null;
  title: string | null;
  effectivePortions: number;
  isLocked: boolean;
  isDiningOut: boolean;
  currentRating: number | null;
  groupMealPlanId: number | null;
}

export interface RatingIn {
  recipeId: string;
  recipeName: string;
  rating: number;  // 0=clear, 1-5=set
  groupMealPlanId: number | null;
}

export interface RatingOut {
  id: number;
  recipeId: string;
  recipeName: string;
  rating: number;
  updatedAt: string | null;
}

export interface RatingHistoryResponse {
  items: RatingOut[];
  total: number;
}

export interface CuisineWeightEntry {
  cuisine: string;
  weight: number;
  hasEnoughData: boolean;
}

export interface CuisineWeightsResponse {
  weights: CuisineWeightEntry[];
}

export interface MealPlanPreviewResponse {
  slots: MealSlotPreview[];
  weekStart: string;
  recipeCount: number;
}

export interface GenerateMealPlanRequest {
  weekStart: string;
  mealTypes: string[];
  excludedDays?: string[];
  specialRequests?: string;
  replaceUnlocked?: boolean;
}

export interface CommitMealPlanRequest {
  weekStart: string;
  slots: MealSlotPreview[];
}

export interface SwapMealRequest {
  date: string;
  mealType: string;
  currentRecipeId?: string | null;
  currentRecipeName?: string | null;
}

export interface SwapSuggestion {
  recipeId: string;
  recipeName: string;
  recipeSlug: string;
  categories: string[];
  servings: number | null;
}

export interface SwapMealResponse {
  suggestions: SwapSuggestion[];
}

export interface MetadataUpdate {
  isLocked?: boolean | null;
  isDiningOut?: boolean | null;
}

export interface MetadataResponse {
  id: number;
  groupMealPlanId: number;
  isLocked: boolean;
  isDiningOut: boolean;
  aiGenerated: boolean;
  weekStart: string;
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
  mealPlanGenerate: "/api/ai/meal-plan/generate",
  mealPlanCommit: "/api/ai/meal-plan/commit",
  mealPlanGet: (weekStart: string) => `/api/ai/meal-plan?week_start=${weekStart}`,
  mealPlanSwap: "/api/ai/meal-plan/swap",
  mealPlanMetadata: (planId: number) => `/api/ai/meal-plan/metadata/${planId}`,
  ratings: "/api/ai/ratings",
  ratingsHistory: "/api/ai/ratings/history",
  ratingsCuisineWeights: "/api/ai/ratings/cuisine-weights",
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

  async generateMealPlan(payload: GenerateMealPlanRequest) {
    return this.requests.post<MealPlanPreviewResponse, GenerateMealPlanRequest>(
      routes.mealPlanGenerate, payload
    );
  }

  async getMealPlan(weekStart: string) {
    return this.requests.get<MealPlanPreviewResponse>(routes.mealPlanGet(weekStart));
  }

  async commitMealPlan(payload: CommitMealPlanRequest) {
    return this.requests.post<number[], CommitMealPlanRequest>(routes.mealPlanCommit, payload);
  }

  async swapMeal(payload: SwapMealRequest) {
    return this.requests.post<SwapMealResponse, SwapMealRequest>(routes.mealPlanSwap, payload);
  }

  async updateMetadata(planId: number, payload: MetadataUpdate) {
    return this.requests.put<MetadataResponse, MetadataUpdate>(
      routes.mealPlanMetadata(planId), payload
    );
  }

  async submitRating(payload: RatingIn) {
    return this.requests.post<{ status: string }, RatingIn>(routes.ratings, payload);
  }

  async getRatingHistory(limit = 20, offset = 0) {
    return this.requests.get<RatingHistoryResponse>(
      `${routes.ratingsHistory}?limit=${limit}&offset=${offset}`
    );
  }

  async getCuisineWeights() {
    return this.requests.get<CuisineWeightsResponse>(routes.ratingsCuisineWeights);
  }
}
