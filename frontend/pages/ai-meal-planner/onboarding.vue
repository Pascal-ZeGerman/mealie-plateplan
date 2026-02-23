<template>
  <v-container class="px-2 py-4">
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold">
              Set Up Your AI Meal Planner
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              Tell us about your preferences so we can generate meals your family will love.
            </p>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-stepper
      v-model="currentStep"
      non-linear
      flat
      alt-labels
    >
      <v-stepper-header>
        <template
          v-for="(step, i) in STEPS"
          :key="step.value"
        >
          <v-stepper-item
            :value="step.value"
            :title="step.title"
            :complete="completedSteps.has(step.value)"
            editable
          />
          <v-divider v-if="i < STEPS.length - 1" />
        </template>
      </v-stepper-header>

      <v-stepper-window>
        <v-stepper-window-item :value="1">
          <div class="pa-4">
            <OnboardingStepCuisines
              :model-value="preferences.cuisinePreferences"
              @update:model-value="preferences.cuisinePreferences = $event"
            />
          </div>
        </v-stepper-window-item>

        <v-stepper-window-item :value="2">
          <div class="pa-4">
            <OnboardingStepAllergies
              :model-value="preferences.allergies"
              @update:model-value="preferences.allergies = $event"
            />
          </div>
        </v-stepper-window-item>

        <v-stepper-window-item :value="3">
          <div class="pa-4">
            <OnboardingStepDietary
              :model-value="preferences.dietaryRestrictions"
              @update:model-value="preferences.dietaryRestrictions = $event"
            />
          </div>
        </v-stepper-window-item>

        <v-stepper-window-item :value="4">
          <div class="pa-4">
            <OnboardingStepFamily
              :model-value="familyModelValue"
              @update:model-value="onFamilyUpdate($event)"
            />
          </div>
        </v-stepper-window-item>

        <v-stepper-window-item :value="5">
          <div class="pa-4">
            <OnboardingStepSeedRating ref="seedRatingRef" />
          </div>
        </v-stepper-window-item>

        <v-stepper-window-item :value="6">
          <div class="pa-4">
            <OnboardingStepReview
              :cuisine-preferences="preferences.cuisinePreferences"
              :allergies="preferences.allergies"
              :dietary-restrictions="preferences.dietaryRestrictions"
              :family-adults="preferences.familyAdults"
              :family-teens="preferences.familyTeens"
              :family-children="preferences.familyChildren"
              :family-toddlers="preferences.familyToddlers"
              :portion-override="preferences.portionOverride"
              :seed-rating-count="seedRatingCount"
              @go-to-step="currentStep = $event"
            />
          </div>
        </v-stepper-window-item>
      </v-stepper-window>

      <!-- Navigation bar -->
      <div class="d-flex justify-space-between align-center pa-4 border-t">
        <v-btn
          variant="text"
          @click="skipOnboarding"
        >
          Skip for now
        </v-btn>
        <div class="d-flex gap-2">
          <v-btn
            variant="outlined"
            :disabled="currentStep <= 1"
            @click="prevStep"
          >
            Back
          </v-btn>
          <v-btn
            v-if="currentStep < STEPS.length"
            color="primary"
            @click="nextStep"
          >
            Next
          </v-btn>
          <v-btn
            v-else
            color="success"
            :loading="completing"
            @click="completeOnboarding"
          >
            Complete Setup
          </v-btn>
        </div>
      </div>
    </v-stepper>
  </v-container>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";

const STEPS = [
  { value: 1, title: "Cuisines" },
  { value: 2, title: "Allergies" },
  { value: 3, title: "Dietary" },
  { value: 4, title: "Family" },
  { value: 5, title: "Seed Recipes" },
  { value: 6, title: "Review" },
];

const DEBOUNCE_MS = 800;

export default defineNuxtComponent({
  setup() {
    const api = useUserApi();
    const router = useRouter();

    const currentStep = ref(1);
    const completedSteps = ref(new Set<number>());
    const completing = ref(false);
    const seedRatingRef = ref<{ getRatings: () => Array<{ recipeSlug: string; recipeName: string; rating: number }> } | null>(null);
    const seedRatingCount = ref(0);

    const preferences = reactive({
      cuisinePreferences: {} as Record<string, "love" | "neutral" | "dislike">,
      allergies: [] as string[],
      dietaryRestrictions: [] as string[],
      familyAdults: 2,
      familyTeens: 0,
      familyChildren: 0,
      familyToddlers: 0,
      portionOverride: null as number | null,
    });

    const familyModelValue = computed(() => ({
      familyAdults: preferences.familyAdults,
      familyTeens: preferences.familyTeens,
      familyChildren: preferences.familyChildren,
      familyToddlers: preferences.familyToddlers,
      portionOverride: preferences.portionOverride,
    }));

    function onFamilyUpdate(val: {
      familyAdults: number;
      familyTeens: number;
      familyChildren: number;
      familyToddlers: number;
      portionOverride: number | null;
    }) {
      preferences.familyAdults = val.familyAdults;
      preferences.familyTeens = val.familyTeens;
      preferences.familyChildren = val.familyChildren;
      preferences.familyToddlers = val.familyToddlers;
      preferences.portionOverride = val.portionOverride;
    }

    // Auto-save: single global watch on the entire preferences object (prevents race conditions)
    let saveTimer: ReturnType<typeof setTimeout> | null = null;
    let dataLoaded = false;

    watch(
      preferences,
      () => {
        if (!dataLoaded) return; // Don't auto-save during initial load
        if (saveTimer) clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
          void savePreferences();
        }, DEBOUNCE_MS);
      },
      { deep: true },
    );

    // Track step transitions to mark completed steps
    watch(currentStep, (newStep, oldStep) => {
      if (oldStep && oldStep !== newStep) {
        completedSteps.value = new Set(completedSteps.value).add(oldStep);
      }
      // If navigating to the review step, capture seed rating count
      if (newStep === 6 && seedRatingRef.value) {
        seedRatingCount.value = seedRatingRef.value.getRatings().length;
      }
    });

    onUnmounted(() => {
      if (saveTimer) clearTimeout(saveTimer);
    });

    onMounted(async () => {
      // Fetch existing preferences to pre-populate on re-run (Pitfall 5)
      try {
        const { data } = await api.aiAddon.getPreferences();
        if (data) {
          preferences.cuisinePreferences = data.cuisinePreferences ?? {};
          preferences.allergies = data.allergies ?? [];
          preferences.dietaryRestrictions = data.dietaryRestrictions ?? [];
          preferences.familyAdults = data.familyAdults ?? 2;
          preferences.familyTeens = data.familyTeens ?? 0;
          preferences.familyChildren = data.familyChildren ?? 0;
          preferences.familyToddlers = data.familyToddlers ?? 0;
          preferences.portionOverride = data.portionOverride ?? null;
        }
      }
      catch (_e) {
        // First visit with no preference record -- start with defaults
      }
      finally {
        dataLoaded = true;
      }
    });

    async function savePreferences() {
      try {
        await api.aiAddon.updatePreferences({
          cuisinePreferences: preferences.cuisinePreferences,
          allergies: preferences.allergies,
          dietaryRestrictions: preferences.dietaryRestrictions,
          familyAdults: preferences.familyAdults,
          familyTeens: preferences.familyTeens,
          familyChildren: preferences.familyChildren,
          familyToddlers: preferences.familyToddlers,
          portionOverride: preferences.portionOverride,
        });
      }
      catch (_e) {
        // Auto-save failures are silent -- user will not see an error
      }
    }

    async function skipOnboarding() {
      try {
        await api.aiAddon.updatePreferences({ onboardingComplete: true });
      }
      catch (_e) {
        // Best-effort skip
      }
      await router.push("/ai-meal-planner");
    }

    async function completeOnboarding() {
      completing.value = true;
      try {
        // Flush any pending auto-save first
        if (saveTimer) {
          clearTimeout(saveTimer);
          saveTimer = null;
        }
        await savePreferences();

        // Submit seed ratings if any were provided
        if (seedRatingRef.value) {
          const ratings = seedRatingRef.value.getRatings();
          if (ratings.length > 0) {
            await api.aiAddon.submitSeedRatings(ratings);
          }
        }

        // Mark onboarding complete
        await api.aiAddon.updatePreferences({ onboardingComplete: true });
        await router.push("/ai-meal-planner");
      }
      catch (_e) {
        // Even if something fails, navigate home
        await router.push("/ai-meal-planner");
      }
      finally {
        completing.value = false;
      }
    }

    function nextStep() {
      if (currentStep.value < STEPS.length) {
        completedSteps.value = new Set(completedSteps.value).add(currentStep.value);
        currentStep.value++;
      }
    }

    function prevStep() {
      if (currentStep.value > 1) {
        currentStep.value--;
      }
    }

    return {
      STEPS,
      currentStep,
      completedSteps,
      completing,
      preferences,
      familyModelValue,
      seedRatingRef,
      seedRatingCount,
      onFamilyUpdate,
      skipOnboarding,
      completeOnboarding,
      nextStep,
      prevStep,
    };
  },
});
</script>
