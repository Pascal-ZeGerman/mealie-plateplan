<template>
  <v-container class="px-2 py-4">
    <!-- Page header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-2">
          <div class="d-flex align-center gap-2">
            <h1 class="text-h4 font-weight-bold">
              Your Week
            </h1>
            <v-chip
              v-if="planState === 'preview'"
              color="info"
              variant="tonal"
              size="small"
            >
              Preview — not saved yet
            </v-chip>
            <v-chip
              v-else-if="planState === 'committed'"
              color="success"
              variant="tonal"
              size="small"
            >
              Active
            </v-chip>
          </div>
          <!-- Action buttons -->
          <div class="d-flex gap-2 flex-wrap align-center">
            <template v-if="planState === 'empty' || planState === 'committed'">
              <NuxtLink
                v-if="planState === 'committed'"
                to="/meal-plans"
                class="text-caption text-decoration-none text-primary mr-2"
              >
                View in Mealie Calendar
              </NuxtLink>
              <v-btn
                variant="flat"
                color="primary"
                @click="openConfig"
              >
                {{ planState === 'committed' ? 'Regenerate Plan' : 'Generate Meal Plan' }}
              </v-btn>
            </template>
            <template v-else-if="planState === 'preview'">
              <v-btn
                variant="outlined"
                @click="openConfig"
              >
                Regenerate Plan
              </v-btn>
              <v-btn
                variant="flat"
                color="primary"
                size="large"
                :loading="committing"
                @click="commitPlan"
              >
                Commit Plan
              </v-btn>
            </template>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Small library warning -->
    <v-row v-if="recipeCount > 0 && recipeCount < 15 && (planState === 'preview' || planState === 'generating')">
      <v-col cols="12">
        <v-alert
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-2"
        >
          You have {{ recipeCount }} recipes — we recommend at least 15 for varied plans. Generation will proceed.
        </v-alert>
      </v-col>
    </v-row>

    <!-- Generation error -->
    <v-row v-if="generationError">
      <v-col cols="12">
        <v-alert
          type="error"
          variant="tonal"
          density="compact"
          class="mb-2"
          closable
          @click:close="generationError = ''"
        >
          {{ generationError }}
        </v-alert>
      </v-col>
    </v-row>

    <!-- Config panel (state = config) -->
    <v-row v-if="planState === 'config'">
      <v-col cols="12" md="5">
        <GenerateConfigPanel
          v-model="configVisible"
          :has-existing-plan="hasExistingPlan"
          :loading="false"
          @generate="onGenerate"
          @update:model-value="onConfigCancel"
        />
      </v-col>
      <v-col cols="12" md="7" style="opacity: 0.6;">
        <MealPlanGrid
          :slots="slots"
          :week-start="currentWeekStart"
          :plan-state="planState === 'config' ? 'empty' : planState"
          :loading="false"
        />
      </v-col>
    </v-row>

    <!-- Generating state -->
    <v-row v-else-if="planState === 'generating'">
      <v-col cols="12">
        <v-card variant="flat" class="mb-4 pa-4 text-center">
          <v-progress-linear
            indeterminate
            color="primary"
            class="mb-4"
          />
          <p class="text-body-1 text-medium-emphasis">
            {{ generatingMessage }}
          </p>
        </v-card>
        <MealPlanGrid
          :slots="slots"
          :week-start="currentWeekStart"
          plan-state="generating"
          :loading="true"
        />
      </v-col>
    </v-row>

    <!-- Empty state -->
    <v-row v-else-if="planState === 'empty'">
      <v-col cols="12" style="position: relative;">
        <!-- Background grid at reduced opacity -->
        <div style="opacity: 0.3; pointer-events: none;">
          <MealPlanGrid
            :slots="[]"
            :week-start="currentWeekStart"
            plan-state="empty"
            :loading="false"
          />
        </div>
        <!-- Overlay CTA card -->
        <div
          style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1; width: 100%; max-width: 400px;"
          class="px-4"
        >
          <v-card variant="flat" class="pa-6 text-center elevation-2">
            <h2 class="text-h6 font-weight-bold mb-2">
              Your week is empty
            </h2>
            <p class="text-body-1 text-medium-emphasis mb-4">
              Generate an AI-powered meal plan tailored to your family's preferences.
            </p>
            <v-btn
              variant="flat"
              color="primary"
              size="large"
              @click="openConfig"
            >
              Generate Meal Plan
            </v-btn>
          </v-card>
        </div>
      </v-col>
    </v-row>

    <!-- Preview / committed state -->
    <v-row v-else-if="planState === 'preview' || planState === 'committed'">
      <v-col cols="12">
        <MealPlanGrid
          :slots="slots"
          :week-start="currentWeekStart"
          :plan-state="planState"
          :loading="false"
          @swap="handleSwap"
          @lock="handleLockToggle"
          @unlock="handleLockToggle"
          @remove="handleRemove"
          @mark-dining-out="handleDiningOutToggle"
          @unmark-dining-out="handleDiningOutToggle"
        />
      </v-col>
    </v-row>

    <!-- SwapDialog: AI Suggestions tab (calls swapMeal API) + Browse Library tab (filtered allRecipes) -->
    <SwapDialog
      v-model="swapDialogOpen"
      :slot="swapSlot"
      :day-name="swapDayName"
      :all-recipes="allRecipes"
      @select="handleSwapSelect"
    />

    <!-- Success snackbar -->
    <v-snackbar
      v-model="showSuccessSnackbar"
      color="success"
      :timeout="4000"
    >
      Your meal plan has been saved to Mealie.
    </v-snackbar>
  </v-container>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";
import type { MealSlotPreview, GenerateMealPlanRequest } from "~/lib/api/user/ai-addon";
import type { RecipeSearchQuery } from "~/lib/api/user/recipes/recipe";

interface AllRecipeEntry {
  id: string;
  name: string;
  slug: string;
  categories: string[];
}

const GENERATING_MESSAGES = [
  "Analyzing your preferences...",
  "Selecting recipes from your library...",
  "Building your meal plan...",
  "Almost there...",
];

const MESSAGE_TIMINGS = [0, 2000, 5000, 10000];

/** Returns the Monday of the week containing the given date as YYYY-MM-DD */
function getMondayOf(date: Date): string {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun,1=Mon,...,6=Sat
  const diff = (day === 0 ? -6 : 1 - day);
  d.setDate(d.getDate() + diff);
  return d.toISOString().split("T")[0];
}

export default defineNuxtComponent({
  setup() {
    definePageMeta({
      middleware: ["ai-addon-auth"],
    });

    const { $globals } = useNuxtApp();
    const api = useUserApi();

    const planState = ref<"empty" | "config" | "generating" | "preview" | "committed">("empty");
    const slots = ref<MealSlotPreview[]>([]);
    const currentWeekStart = ref("");
    const recipeCount = ref(0);
    const configVisible = ref(false);
    const committing = ref(false);
    const generationError = ref("");
    const showSuccessSnackbar = ref(false);
    const generatingMessage = ref(GENERATING_MESSAGES[0]);
    let generatingInterval: ReturnType<typeof setInterval> | null = null;

    // Map keying "${date}-${mealType}" -> group_meal_plan_id (populated after commit)
    const committedPlanIds = ref(new Map<string, number>());

    // Swap dialog state
    const swapDialogOpen = ref(false);
    const swapSlot = ref<MealSlotPreview | null>(null);
    const swapDayName = ref("");
    const allRecipes = ref<AllRecipeEntry[]>([]);

    const hasExistingPlan = computed(() => slots.value.length > 0);

    // Calculate smart week default: Mon-Wed (1-3) => this week, Thu-Sun (4,5,6,0) => next week
    function getDefaultWeekStart(): string {
      const today = new Date();
      const dayOfWeek = today.getDay();
      if (dayOfWeek >= 1 && dayOfWeek <= 3) {
        return getMondayOf(today);
      }
      else {
        const next = new Date(today);
        next.setDate(today.getDate() + 7);
        return getMondayOf(next);
      }
    }

    function startGeneratingMessages() {
      generatingMessage.value = GENERATING_MESSAGES[0];
      let msgIdx = 0;
      generatingInterval = setInterval(() => {
        const elapsed = Date.now() - startTime;
        let nextIdx = 0;
        for (let i = 0; i < MESSAGE_TIMINGS.length; i++) {
          if (elapsed >= MESSAGE_TIMINGS[i]) nextIdx = i;
        }
        if (nextIdx !== msgIdx) {
          msgIdx = nextIdx;
          generatingMessage.value = GENERATING_MESSAGES[msgIdx];
        }
      }, 500);
    }

    let startTime = 0;

    function stopGeneratingMessages() {
      if (generatingInterval) {
        clearInterval(generatingInterval);
        generatingInterval = null;
      }
    }

    function openConfig() {
      configVisible.value = true;
      planState.value = "config";
    }

    function onConfigCancel() {
      configVisible.value = false;
      planState.value = slots.value.length > 0 ? "committed" : "empty";
    }

    async function onGenerate(config: GenerateMealPlanRequest) {
      configVisible.value = false;
      currentWeekStart.value = config.weekStart;
      planState.value = "generating";
      generationError.value = "";
      startTime = Date.now();
      startGeneratingMessages();

      try {
        const { data, error } = await api.aiAddon.generateMealPlan(config);
        stopGeneratingMessages();

        if (error?.value) {
          const status = (error.value as { status?: number }).status;
          if (status === 402) {
            generationError.value = "Weekly AI budget reached. Plan generation is paused until Sunday. View settings to adjust your budget.";
          }
          else if (status === 422 || status === 404) {
            generationError.value = "No recipes found in your library. Add some recipes to Mealie before generating a plan.";
          }
          else {
            generationError.value = "The AI took too long to respond. Try again or reduce your special requests.";
          }
          planState.value = slots.value.length > 0 ? "committed" : "empty";
        }
        else if (data?.value) {
          slots.value = data.value.slots;
          recipeCount.value = data.value.recipeCount;
          planState.value = "preview";
        }
        else {
          generationError.value = "The AI took too long to respond. Try again or reduce your special requests.";
          planState.value = slots.value.length > 0 ? "committed" : "empty";
        }
      }
      catch (_e) {
        stopGeneratingMessages();
        generationError.value = "The AI took too long to respond. Try again or reduce your special requests.";
        planState.value = slots.value.length > 0 ? "committed" : "empty";
      }
    }

    async function commitPlan() {
      committing.value = true;
      try {
        const { data } = await api.aiAddon.commitMealPlan({
          weekStart: currentWeekStart.value,
          slots: slots.value,
        });

        if (data?.value) {
          // Map each slot index to the returned group_meal_plan_id
          const ids = data.value;
          const newMap = new Map<string, number>();
          slots.value.forEach((slot, idx) => {
            if (ids[idx] !== undefined) {
              newMap.set(`${slot.date}-${slot.mealType}`, ids[idx]);
            }
          });
          committedPlanIds.value = newMap;
        }

        planState.value = "committed";
        showSuccessSnackbar.value = true;
      }
      catch (_e) {
        generationError.value = "Failed to save the plan. Please try again.";
      }
      finally {
        committing.value = false;
      }
    }

    function handleLockToggle(slot: MealSlotPreview) {
      if (planState.value === "preview") {
        // Local state only — no API call (metadata rows don't exist yet)
        const idx = slots.value.findIndex(s => s.date === slot.date && s.mealType === slot.mealType);
        if (idx !== -1) {
          slots.value[idx] = { ...slots.value[idx], isLocked: !slots.value[idx].isLocked };
        }
      }
      else if (planState.value === "committed") {
        // API call — metadata rows exist post-commit
        const planId = committedPlanIds.value.get(`${slot.date}-${slot.mealType}`);
        if (planId) {
          api.aiAddon.updateMetadata(planId, { isLocked: !slot.isLocked }).then(({ data }) => {
            if (data?.value) {
              const idx = slots.value.findIndex(s => s.date === slot.date && s.mealType === slot.mealType);
              if (idx !== -1) {
                slots.value[idx] = { ...slots.value[idx], isLocked: data.value!.isLocked };
              }
            }
          }).catch(() => {
            // Ignore metadata update failures silently
          });
        }
      }
    }

    function handleDiningOutToggle(slot: MealSlotPreview) {
      if (planState.value === "preview") {
        // Local state only
        const idx = slots.value.findIndex(s => s.date === slot.date && s.mealType === slot.mealType);
        if (idx !== -1) {
          slots.value[idx] = { ...slots.value[idx], isDiningOut: !slots.value[idx].isDiningOut };
        }
      }
      else if (planState.value === "committed") {
        // API call
        const planId = committedPlanIds.value.get(`${slot.date}-${slot.mealType}`);
        if (planId) {
          api.aiAddon.updateMetadata(planId, { isDiningOut: !slot.isDiningOut }).then(({ data }) => {
            if (data?.value) {
              const idx = slots.value.findIndex(s => s.date === slot.date && s.mealType === slot.mealType);
              if (idx !== -1) {
                slots.value[idx] = { ...slots.value[idx], isDiningOut: data.value!.isDiningOut };
              }
            }
          }).catch(() => {
            // Ignore silently
          });
        }
      }
    }

    function handleRemove(slot: MealSlotPreview) {
      if (planState.value === "preview") {
        const idx = slots.value.findIndex(s => s.date === slot.date && s.mealType === slot.mealType);
        if (idx !== -1) {
          slots.value.splice(idx, 1);
        }
      }
    }

    function handleSwap(slot: MealSlotPreview) {
      swapSlot.value = slot;
      // Compute day name from slot.date (YYYY-MM-DD)
      const dateObj = new Date(slot.date + "T12:00:00Z");
      swapDayName.value = dateObj.toLocaleDateString("en-US", { weekday: "long", timeZone: "UTC" });
      swapDialogOpen.value = true;
    }

    function handleSwapSelect(recipe: { recipeId: string; recipeName: string; recipeSlug: string; servings: number | null }) {
      if (!swapSlot.value) return;
      const idx = slots.value.findIndex(
        s => s.date === swapSlot.value!.date && s.mealType === swapSlot.value!.mealType,
      );
      if (idx !== -1) {
        slots.value[idx] = {
          ...slots.value[idx],
          recipeId: recipe.recipeId,
          recipeName: recipe.recipeName,
          recipeSlug: recipe.recipeSlug,
          recipeServings: recipe.servings,
          slotType: "recipe",
          isDiningOut: false,
        };
      }
      swapDialogOpen.value = false;
      swapSlot.value = null;
    }

    onMounted(async () => {
      // 1. Onboarding gate (same pattern as index.vue)
      try {
        const { data: prefs } = await api.aiAddon.getPreferences();
        if (!prefs?.value?.onboardingComplete) {
          await navigateTo("/ai-meal-planner/onboarding");
          return;
        }
      }
      catch (_e) {
        await navigateTo("/ai-meal-planner/onboarding");
        return;
      }

      // 2. Smart week default
      currentWeekStart.value = getDefaultWeekStart();

      // 3. Fetch existing plan
      try {
        const { data } = await api.aiAddon.getMealPlan(currentWeekStart.value);
        if (data?.value && data.value.slots && data.value.slots.length > 0) {
          slots.value = data.value.slots;
          recipeCount.value = data.value.recipeCount;
          planState.value = "committed";
        }
        else {
          planState.value = "empty";
        }
      }
      catch (_e) {
        planState.value = "empty";
      }

        // 4. Fetch all recipes for Browse Library (non-blocking)
      // SwapDialog uses these for its Browse Library tab and AI Suggestions tab calls swapMeal
      api.recipes.getAll(1, -1, {} as RecipeSearchQuery).then(({ data: recipePage }) => {
        if (recipePage?.value?.items) {
          allRecipes.value = recipePage.value.items.map(r => ({
            id: r.id ?? "",
            name: r.name ?? "",
            slug: r.slug ?? "",
            categories: (r.recipeCategory ?? []).map((c: { name?: string }) => c.name ?? "").filter(Boolean),
          }));
        }
      }).catch(() => {
        // Browse library will be empty — not blocking
      });
    });

    onUnmounted(() => {
      stopGeneratingMessages();
    });

    return {
      $globals,
      planState,
      slots,
      currentWeekStart,
      recipeCount,
      configVisible,
      committing,
      generationError,
      showSuccessSnackbar,
      generatingMessage,
      committedPlanIds,
      hasExistingPlan,
      swapDialogOpen,
      swapSlot,
      swapDayName,
      allRecipes,
      openConfig,
      onConfigCancel,
      onGenerate,
      commitPlan,
      handleLockToggle,
      handleDiningOutToggle,
      handleRemove,
      handleSwap,
      handleSwapSelect,
    };
  },
});
</script>
