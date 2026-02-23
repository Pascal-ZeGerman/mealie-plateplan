// Onboarding gate middleware for AI Meal Planner.
// Apply via definePageMeta({ middleware: ["ai-onboarding-complete"] }) on meal plan generation pages (Phase 4).
// This middleware is created in Phase 2 but not applied to any page yet.
export default defineNuxtRouteMiddleware(async () => {
  const api = useUserApi();
  try {
    const { data } = await api.aiAddon.getPreferences();
    if (!data?.onboardingComplete) {
      return navigateTo("/ai-meal-planner/onboarding");
    }
  }
  catch (_e) {
    // If preferences can't be fetched, redirect to onboarding
    return navigateTo("/ai-meal-planner/onboarding");
  }
});
