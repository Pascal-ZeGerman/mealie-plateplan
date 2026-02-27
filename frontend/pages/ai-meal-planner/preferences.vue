<template>
  <v-container class="px-2 py-4">
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold">
              Meal Planner Preferences
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              Update your preferences. Changes are saved automatically.
            </p>
          </div>
          <div class="d-flex gap-2">
            <v-btn
              variant="outlined"
              :to="'/ai-meal-planner'"
              :prepend-icon="$globals.icons.arrowLeftBold"
            >
              Back
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <div
      v-if="loading"
      class="text-center py-12"
    >
      <v-progress-circular
        indeterminate
        color="primary"
        size="48"
      />
      <p class="text-body-2 text-medium-emphasis mt-4">
        Loading your preferences...
      </p>
    </div>

    <template v-else>
      <!-- Save status indicator -->
      <v-row v-if="saveStatus !== 'idle'">
        <v-col cols="12">
          <v-alert
            v-if="saveStatus === 'saving'"
            type="info"
            variant="tonal"
            density="compact"
          >
            Saving changes...
          </v-alert>
          <v-alert
            v-else-if="saveStatus === 'saved'"
            type="success"
            variant="tonal"
            density="compact"
          >
            Preferences saved.
          </v-alert>
        </v-col>
      </v-row>

      <!-- Cuisine Preferences -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-medium">
              Cuisine Preferences
            </v-card-title>
            <v-card-text>
              <OnboardingStepCuisines
                :model-value="preferences.cuisinePreferences"
                @update:model-value="preferences.cuisinePreferences = $event"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Allergies -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-medium">
              Food Allergies
            </v-card-title>
            <v-card-text>
              <OnboardingStepAllergies
                :model-value="preferences.allergies"
                @update:model-value="preferences.allergies = $event"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Dietary Restrictions -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-medium">
              Dietary Preferences
            </v-card-title>
            <v-card-text>
              <OnboardingStepDietary
                :model-value="preferences.dietaryRestrictions"
                @update:model-value="preferences.dietaryRestrictions = $event"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Family Profile -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-medium">
              Family Profile
            </v-card-title>
            <v-card-text>
              <OnboardingStepFamily
                :model-value="familyModelValue"
                @update:model-value="onFamilyUpdate($event)"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Re-run wizard button -->
      <v-row>
        <v-col cols="12">
          <v-card variant="outlined">
            <v-card-text class="d-flex align-center justify-space-between">
              <div>
                <p class="text-body-1 font-weight-medium mb-1">
                  Re-run Onboarding Wizard
                </p>
                <p class="text-body-2 text-medium-emphasis">
                  Go through the full setup wizard again to update all preferences in one flow.
                </p>
              </div>
              <v-btn
                variant="tonal"
                color="primary"
                :to="'/ai-meal-planner/onboarding'"
              >
                Re-run Full Wizard
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";

const DEBOUNCE_MS = 800;

export default defineNuxtComponent({
  setup() {
    definePageMeta({
      middleware: ["ai-addon-auth"],
    });
    const { $globals } = useNuxtApp();
    const api = useUserApi();

    const loading = ref(true);
    const saveStatus = ref<"idle" | "saving" | "saved">("idle");

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

    // Auto-save: single global watch on the entire preferences object
    let saveTimer: ReturnType<typeof setTimeout> | null = null;
    let dataLoaded = false;

    watch(
      preferences,
      () => {
        if (!dataLoaded) return;
        if (saveTimer) clearTimeout(saveTimer);
        saveStatus.value = "idle";
        saveTimer = setTimeout(() => {
          void savePreferences();
        }, DEBOUNCE_MS);
      },
      { deep: true },
    );

    onUnmounted(() => {
      if (saveTimer) clearTimeout(saveTimer);
    });

    onMounted(async () => {
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
        // Could not load preferences -- defaults remain
      }
      finally {
        loading.value = false;
        dataLoaded = true;
      }
    });

    async function savePreferences() {
      saveStatus.value = "saving";
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
        saveStatus.value = "saved";
        // Clear "saved" indicator after 2 seconds
        setTimeout(() => {
          saveStatus.value = "idle";
        }, 2000);
      }
      catch (_e) {
        saveStatus.value = "idle";
      }
    }

    return {
      $globals,
      loading,
      saveStatus,
      preferences,
      familyModelValue,
      onFamilyUpdate,
    };
  },
});
</script>
