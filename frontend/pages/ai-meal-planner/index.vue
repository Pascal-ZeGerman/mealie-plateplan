<template>
  <v-container class="px-2 py-4">
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold">
              AI Meal Planner
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              AI-powered meal planning
            </p>
          </div>
          <div class="d-flex align-center gap-2">
            <v-btn
              variant="outlined"
              size="small"
              :to="'/ai-meal-planner/settings'"
              :prepend-icon="$globals.icons.cog"
            >
              Settings
            </v-btn>
            <v-icon
              color="success"
              size="small"
            >
              {{ $globals.icons.checkboxMarkedCircle }}
            </v-icon>
            <span class="text-caption text-medium-emphasis">Active</span>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Budget alert banner — show when >= 80% of weekly budget used -->
    <v-alert
      v-if="budgetStatus && budgetStatus.alert && !budgetAlertDismissed"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-4"
      closable
      @click:close="budgetAlertDismissed = true"
    >
      You've used {{ budgetStatus.pct.toFixed(1) }}% of your weekly AI budget
      (${{ budgetStatus.spent.toFixed(2) }} / ${{ budgetStatus.cap.toFixed(2) }}).
      Resets Sunday.
      <template #append>
        <v-btn
          variant="text"
          size="small"
          :to="'/ai-meal-planner/settings'"
        >
          View settings
        </v-btn>
      </template>
    </v-alert>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-text>
            <p class="text-body-1 mb-4">
              Your AI meal planner is set up and ready. Generate a meal plan to get started.
            </p>
            <div class="d-flex gap-3 flex-wrap">
              <v-chip
                :prepend-icon="$globals.icons.calendarMultiselect"
                variant="tonal"
                color="primary"
                :to="'/ai-meal-planner/plan'"
              >
                Meal Plans
              </v-chip>

              <v-chip
                v-if="onboardingComplete"
                :prepend-icon="$globals.icons.cog"
                variant="tonal"
                color="primary"
                :to="'/ai-meal-planner/preferences'"
              >
                Preferences
              </v-chip>
              <v-tooltip
                v-else
                location="bottom"
                text="Complete onboarding to access preferences"
              >
                <template #activator="{ props }">
                  <v-chip
                    v-bind="props"
                    :prepend-icon="$globals.icons.cog"
                    disabled
                    variant="tonal"
                    class="cursor-not-allowed"
                  >
                    Preferences
                  </v-chip>
                </template>
              </v-tooltip>

              <v-chip
                :prepend-icon="$globals.icons.cog"
                variant="tonal"
                color="secondary"
                :to="'/ai-meal-planner/settings'"
              >
                Settings
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row
      v-if="isAdmin"
      class="mt-2"
    >
      <v-col cols="12">
        <v-card
          variant="outlined"
        >
          <v-card-text class="py-2">
            <div class="d-flex align-center">
              <v-icon
                size="small"
                color="secondary"
                class="mr-2"
              >
                {{ $globals.icons.wrench }}
              </v-icon>
              <span class="text-caption text-medium-emphasis mr-3">Admin</span>
              <NuxtLink
                to="/ai-meal-planner/debug"
                class="text-caption text-decoration-none text-primary"
              >
                View addon debug info
              </NuxtLink>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";
import type { BudgetStatusResponse } from "~/lib/api/user/ai-addon";

export default defineNuxtComponent({
  setup() {
    definePageMeta({
      middleware: ["ai-addon-auth"],
    });
    const { $globals } = useNuxtApp();
    const auth = useMealieAuth();
    const api = useUserApi();

    const isAdmin = computed(() => auth.user.value?.admin ?? false);
    const onboardingComplete = ref(false);

    // Budget alert state
    const budgetStatus = ref<BudgetStatusResponse | null>(null);
    const budgetAlertDismissed = ref(false);

    onMounted(async () => {
      try {
        const { data } = await api.aiAddon.getPreferences();
        if (data) {
          onboardingComplete.value = data.onboardingComplete;
          if (!data.onboardingComplete) {
            await navigateTo("/ai-meal-planner/onboarding");
          }
        }
        else {
          // No preference record -- first visit, redirect to onboarding
          await navigateTo("/ai-meal-planner/onboarding");
        }
      }
      catch (_e) {
        // API error on first visit -- redirect to onboarding
        await navigateTo("/ai-meal-planner/onboarding");
      }

      // Non-blocking budget fetch — runs independently after main page load
      api.aiAddon.getBudgetStatus().then(({ data }) => {
        if (data) {
          budgetStatus.value = data;
        }
      }).catch(() => {
        // Budget fetch failure is non-fatal — banner simply does not appear
      });
    });

    return {
      $globals,
      isAdmin,
      onboardingComplete,
      budgetStatus,
      budgetAlertDismissed,
    };
  },
});
</script>
