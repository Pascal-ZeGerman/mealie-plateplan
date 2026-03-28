<template>
  <v-container class="px-2 py-4">
    <!-- Page header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold">
              AI Provider Settings
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              Configure API keys, budget limits, and model selection.
            </p>
          </div>
          <v-btn
            variant="outlined"
            :to="'/ai-meal-planner'"
            :prepend-icon="$globals.icons.arrowLeftBold"
          >
            Back
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Loading state -->
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
        Loading settings...
      </p>
    </div>

    <template v-else>
      <!-- Section 1: API Keys -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title>API Keys</v-card-title>
            <v-card-subtitle>
              Your API keys are shared across your household. Keys are validated before saving.
            </v-card-subtitle>
            <v-card-text>
              <div
                v-for="provider in ['claude', 'openai']"
                :key="provider"
                class="mb-6"
              >
                <p class="text-body-1 font-weight-medium mb-2 text-capitalize">
                  {{ provider === 'claude' ? 'Anthropic (Claude)' : 'OpenAI' }}
                  <v-chip
                    v-if="providerStatusMap[provider]"
                    size="x-small"
                    class="ml-2"
                    :color="providerStatusMap[provider]?.isValid ? 'success' : 'error'"
                    variant="tonal"
                  >
                    {{ providerStatusMap[provider]?.isValid ? 'Configured' : 'Invalid' }}
                  </v-chip>
                </p>

                <p
                  v-if="providerStatusMap[provider]"
                  class="text-caption text-medium-emphasis mb-2"
                >
                  Current key: ...{{ providerStatusMap[provider]?.maskedKey }}
                </p>

                <v-row align="center">
                  <v-col cols="12" sm="8">
                    <v-text-field
                      v-model="keyInputs[provider]"
                      :label="`Enter new ${provider === 'claude' ? 'Anthropic' : 'OpenAI'} API key`"
                      type="password"
                      density="compact"
                      variant="outlined"
                      :placeholder="providerStatusMap[provider] ? 'Leave blank to keep existing key' : 'sk-ant-...'"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="12" sm="4">
                    <v-btn
                      color="primary"
                      variant="tonal"
                      :loading="savingKey[provider]"
                      :disabled="!keyInputs[provider]"
                      @click="saveProviderKey(provider)"
                    >
                      Test &amp; Save
                    </v-btn>
                    <v-btn
                      v-if="providerStatusMap[provider]"
                      color="error"
                      variant="text"
                      size="small"
                      class="ml-1"
                      :loading="deletingKey[provider]"
                      @click="deleteProviderKey(provider)"
                    >
                      Remove
                    </v-btn>
                  </v-col>
                </v-row>

                <v-alert
                  v-if="keyFeedback[provider]"
                  :type="keyFeedback[provider]?.success ? 'success' : 'error'"
                  variant="tonal"
                  density="compact"
                  class="mt-2"
                >
                  {{ keyFeedback[provider]?.message }}
                </v-alert>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Section 2: Weekly Budget -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title>Weekly Budget</v-card-title>
            <v-card-subtitle>
              Controls how much can be spent on AI API calls per week (resets Sunday).
            </v-card-subtitle>
            <v-card-text>
              <div v-if="budgetStatus" class="mb-4">
                <div class="d-flex justify-space-between mb-1">
                  <span class="text-body-2">
                    ${{ budgetStatus.spent.toFixed(2) }} spent of ${{ budgetStatus.cap.toFixed(2) }}
                    ({{ budgetStatus.pct.toFixed(1) }}%)
                  </span>
                  <span class="text-caption text-medium-emphasis">
                    Resets {{ budgetStatus.resetsOn }}
                  </span>
                </div>
                <v-progress-linear
                  :model-value="budgetStatus.pct"
                  :color="budgetStatus.pct >= 95 ? 'error' : budgetStatus.pct >= 80 ? 'warning' : 'success'"
                  height="8"
                  rounded
                />
              </div>

              <v-row align="center" class="mt-2">
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="budgetCapInput"
                    label="Weekly cap ($)"
                    type="number"
                    density="compact"
                    variant="outlined"
                    :min="0.01"
                    :step="1"
                    prefix="$"
                    hide-details
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-btn
                    color="primary"
                    variant="tonal"
                    :loading="savingBudget"
                    :disabled="!budgetCapInput || budgetCapInput <= 0"
                    @click="saveBudget"
                  >
                    Update Cap
                  </v-btn>
                </v-col>
              </v-row>

              <v-alert
                v-if="budgetFeedback"
                :type="budgetFeedback.success ? 'success' : 'error'"
                variant="tonal"
                density="compact"
                class="mt-2"
              >
                {{ budgetFeedback.message }}
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Section 3: Model Configuration -->
      <v-row>
        <v-col cols="12">
          <v-card class="mb-4">
            <v-card-title>AI Models</v-card-title>
            <v-card-subtitle v-if="!isAdmin">
              Read-only &mdash; only admins can change model routing.
            </v-card-subtitle>
            <v-card-subtitle v-else>
              Configure which AI model tier is used for each task type.
            </v-card-subtitle>
            <v-card-text>
              <p
                v-if="!taskConfigData || taskConfigData.configs.length === 0"
                class="text-body-2 text-medium-emphasis"
              >
                No task types configured yet. Model routing is configured automatically when AI features are first used.
              </p>
              <div
                v-for="entry in taskConfigData?.configs ?? []"
                :key="entry.taskType"
                class="mb-4"
              >
                <div class="d-flex align-center justify-space-between">
                  <span class="text-body-2 font-weight-medium text-capitalize">
                    {{ entry.taskType.replace(/_/g, ' ') }}
                  </span>
                  <div v-if="isAdmin" class="d-flex align-center gap-2" style="min-width: 260px;">
                    <v-select
                      :model-value="entry.providerTier"
                      :items="tierSelectItems"
                      item-title="title"
                      item-value="value"
                      density="compact"
                      variant="outlined"
                      hide-details
                      style="min-width: 220px;"
                      @update:model-value="updateTaskConfig(entry.taskType, $event)"
                    >
                      <template #item="{ item, props: itemProps }">
                        <v-list-item
                          v-bind="itemProps"
                          :subtitle="tierCostMap[item.value]"
                        />
                      </template>
                    </v-select>
                    <v-btn
                      icon
                      variant="text"
                      size="small"
                      color="error"
                      :loading="deletingTask[entry.taskType]"
                      @click="deleteTaskConfig(entry.taskType)"
                    >
                      <v-icon>{{ $globals.icons.delete }}</v-icon>
                    </v-btn>
                  </div>
                  <span v-else class="text-body-2 text-medium-emphasis">
                    {{ tierDisplayMap[entry.providerTier] ?? entry.providerTier }}
                  </span>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Section 4: Rating History -->
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h6 font-weight-bold">Rating History</v-card-title>
            <v-card-subtitle class="text-body-2 text-medium-emphasis">
              Meals you have rated — most recent first.
            </v-card-subtitle>
            <v-card-text>
              <!-- Loading state -->
              <div v-if="ratingHistoryLoading && ratingHistory.length === 0" class="d-flex justify-center py-12">
                <v-progress-circular indeterminate />
              </div>

              <!-- Error state -->
              <div v-else-if="ratingHistoryError && ratingHistory.length === 0" class="text-center py-12">
                <p class="text-body-2 text-medium-emphasis">
                  Could not load rating history. Refresh to try again.
                </p>
              </div>

              <!-- Empty state -->
              <div v-else-if="ratingHistory.length === 0" class="text-center py-12">
                <p class="text-subtitle-1 font-weight-bold">No ratings yet</p>
                <p class="text-body-2 text-medium-emphasis mt-2">
                  After your first meal plan is committed, tap the stars on any recipe slot to rate it. Ratings help the AI learn your preferences.
                </p>
              </div>

              <!-- Rating list -->
              <v-list v-else density="compact">
                <v-list-item v-for="item in ratingHistory" :key="item.id">
                  <template #prepend>
                    <v-rating
                      :model-value="item.rating"
                      readonly
                      size="x-small"
                      color="warning"
                      density="compact"
                    />
                  </template>
                  <v-list-item-title class="text-body-2 font-weight-bold">
                    {{ item.recipeName }}
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption text-medium-emphasis">
                    {{ formatRatingDate(item.updatedAt) }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>

              <!-- Load more button -->
              <div v-if="ratingHistory.length < ratingHistoryTotal" class="d-flex justify-center mt-4">
                <v-btn
                  variant="text"
                  size="small"
                  :loading="ratingHistoryLoading"
                  @click="loadMoreRatings"
                >
                  Load more ratings
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Section 5: Learned Cuisine Preferences -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-subtitle-1 font-weight-bold">
              Learned Cuisine Preferences
            </v-card-title>
            <v-card-text>
              <p class="text-body-2 text-medium-emphasis mb-4">
                Updated automatically as you rate meals. Read-only — edit your base preferences above.
              </p>

              <div v-if="cuisineWeightsLoading" class="d-flex justify-center py-6">
                <v-progress-circular indeterminate size="24" />
              </div>

              <div v-else-if="cuisineWeights.length === 0" class="text-center py-6">
                <p class="text-body-2 text-medium-emphasis">No cuisine data available yet.</p>
              </div>

              <div v-else>
                <div v-for="cw in cuisineWeights" :key="cw.cuisine" class="d-flex align-center mb-2">
                  <span class="text-body-2 mr-2" style="min-width: 120px;">{{ cw.cuisine }}</span>
                  <v-chip
                    v-if="cw.hasEnoughData"
                    size="x-small"
                    variant="tonal"
                    :color="cw.weight >= 0.75 ? 'success' : cw.weight >= 0.40 ? 'secondary' : 'error'"
                  >
                    {{ cw.weight.toFixed(2) }}
                  </v-chip>
                  <span v-else class="text-caption text-medium-emphasis">(not enough data yet)</span>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";
import type { ProviderKeyStatus, BudgetStatusResponse, TaskConfigListResponse, RatingOut, CuisineWeightEntry } from "~/lib/api/user/ai-addon";

export default defineNuxtComponent({
  setup() {
    definePageMeta({
      middleware: ["ai-addon-auth"],
    });
    const { $globals } = useNuxtApp();
    const api = useUserApi();
    const auth = useMealieAuth();

    const isAdmin = computed(() => auth.user.value?.admin ?? false);
    const loading = ref(true);

    // Provider key state
    const providerSettings = ref<ProviderKeyStatus[]>([]);
    const providerStatusMap = computed<Record<string, ProviderKeyStatus | undefined>>(() => {
      const map: Record<string, ProviderKeyStatus | undefined> = {};
      for (const p of providerSettings.value) {
        map[p.provider] = p;
      }
      return map;
    });
    const keyInputs = reactive<Record<string, string>>({ claude: "", openai: "" });
    const savingKey = reactive<Record<string, boolean>>({ claude: false, openai: false });
    const deletingKey = reactive<Record<string, boolean>>({ claude: false, openai: false });
    const keyFeedback = reactive<Record<string, { success: boolean; message: string } | null>>({ claude: null, openai: null });

    // Budget state
    const budgetStatus = ref<BudgetStatusResponse | null>(null);
    const budgetCapInput = ref<number>(10);
    const savingBudget = ref(false);
    const budgetFeedback = ref<{ success: boolean; message: string } | null>(null);

    // Task config state
    const taskConfigData = ref<TaskConfigListResponse | null>(null);
    const deletingTask = reactive<Record<string, boolean>>({});

    // Rating history state
    const ratingHistory = ref<RatingOut[]>([]);
    const ratingHistoryTotal = ref(0);
    const ratingHistoryLoading = ref(false);
    const ratingHistoryError = ref(false);
    const ratingHistoryOffset = ref(0);
    const RATINGS_PAGE_SIZE = 20;

    // Cuisine weights state
    const cuisineWeights = ref<CuisineWeightEntry[]>([]);
    const cuisineWeightsLoading = ref(false);

    const tierSelectItems = computed(() => {
      return (taskConfigData.value?.availableTiers ?? []).map((t) => ({
        title: t.displayName,
        value: t.tier,
      }));
    });

    const tierDisplayMap = computed<Record<string, string>>(() => {
      const map: Record<string, string> = {};
      for (const t of taskConfigData.value?.availableTiers ?? []) {
        map[t.tier] = t.displayName;
      }
      return map;
    });

    const tierCostMap = computed<Record<string, string>>(() => {
      const map: Record<string, string> = {};
      for (const t of taskConfigData.value?.availableTiers ?? []) {
        map[t.tier] = t.approxCostPerCall;
      }
      return map;
    });

    async function loadAll() {
      try {
        const [provRes, budgetRes, taskRes] = await Promise.all([
          api.aiAddon.listProviderSettings(),
          api.aiAddon.getBudgetStatus(),
          api.aiAddon.getTaskConfig(),
        ]);
        if (provRes.data) {
          providerSettings.value = provRes.data;
        }
        if (budgetRes.data) {
          budgetStatus.value = budgetRes.data;
          budgetCapInput.value = budgetRes.data.cap;
        }
        if (taskRes.data) {
          taskConfigData.value = taskRes.data;
        }
      }
      catch (_e) {
        // Silently handle load errors — page still renders with empty state
      }
      finally {
        loading.value = false;
      }
    }

    async function loadRatingHistory(append = false) {
      ratingHistoryLoading.value = true;
      ratingHistoryError.value = false;
      try {
        const { data } = await api.aiAddon.getRatingHistory(RATINGS_PAGE_SIZE, ratingHistoryOffset.value);
        if (data) {
          if (append) {
            ratingHistory.value.push(...data.items);
          }
          else {
            ratingHistory.value = data.items;
          }
          ratingHistoryTotal.value = data.total;
        }
      }
      catch (_e) {
        ratingHistoryError.value = true;
      }
      finally {
        ratingHistoryLoading.value = false;
      }
    }

    async function loadMoreRatings() {
      ratingHistoryOffset.value += RATINGS_PAGE_SIZE;
      await loadRatingHistory(true);
    }

    async function loadCuisineWeights() {
      cuisineWeightsLoading.value = true;
      try {
        const { data } = await api.aiAddon.getCuisineWeights();
        if (data) {
          cuisineWeights.value = data.weights;
        }
      }
      catch (_e) {
        // Silent failure — section just stays empty
      }
      finally {
        cuisineWeightsLoading.value = false;
      }
    }

    function formatRatingDate(dateStr: string | null): string {
      if (!dateStr) return "";
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
    }

    onMounted(() => {
      void loadAll();
      void loadRatingHistory();
      void loadCuisineWeights();
    });

    async function saveProviderKey(provider: string) {
      if (!keyInputs[provider]) return;
      savingKey[provider] = true;
      keyFeedback[provider] = null;
      try {
        const { data } = await api.aiAddon.saveProviderKey({ provider, apiKey: keyInputs[provider] });
        if (data) {
          if (data.isValid) {
            keyFeedback[provider] = { success: true, message: `${provider === 'claude' ? 'Anthropic' : 'OpenAI'} API key validated and saved successfully.` };
            keyInputs[provider] = "";
            // Reload provider list to show updated masked key
            const { data: updated } = await api.aiAddon.listProviderSettings();
            if (updated) {
              providerSettings.value = updated;
            }
          }
          else {
            keyFeedback[provider] = {
              success: false,
              message: data.validationError ?? "API key validation failed. Please check your key and try again.",
            };
          }
        }
      }
      catch (_e) {
        keyFeedback[provider] = { success: false, message: "Failed to save key. Please try again." };
      }
      finally {
        savingKey[provider] = false;
      }
    }

    async function deleteProviderKey(provider: string) {
      deletingKey[provider] = true;
      keyFeedback[provider] = null;
      try {
        await api.aiAddon.deleteProviderKey(provider);
        const { data: updated } = await api.aiAddon.listProviderSettings();
        if (updated) {
          providerSettings.value = updated;
        }
        keyFeedback[provider] = { success: true, message: "API key removed." };
      }
      catch (_e) {
        keyFeedback[provider] = { success: false, message: "Failed to remove key." };
      }
      finally {
        deletingKey[provider] = false;
      }
    }

    async function saveBudget() {
      if (!budgetCapInput.value || budgetCapInput.value <= 0) return;
      savingBudget.value = true;
      budgetFeedback.value = null;
      try {
        const { data } = await api.aiAddon.updateBudgetConfig({ weeklyCap: budgetCapInput.value });
        if (data) {
          budgetStatus.value = data;
          budgetCapInput.value = data.cap;
          budgetFeedback.value = { success: true, message: `Weekly cap updated to $${data.cap.toFixed(2)}.` };
          setTimeout(() => {
            budgetFeedback.value = null;
          }, 3000);
        }
      }
      catch (_e) {
        budgetFeedback.value = { success: false, message: "Failed to update budget cap." };
      }
      finally {
        savingBudget.value = false;
      }
    }

    async function updateTaskConfig(taskType: string, providerTier: string) {
      try {
        await api.aiAddon.upsertTaskConfig({ taskType, providerTier });
        const { data } = await api.aiAddon.getTaskConfig();
        if (data) {
          taskConfigData.value = data;
        }
      }
      catch (_e) {
        // Silently handle
      }
    }

    async function deleteTaskConfig(taskType: string) {
      deletingTask[taskType] = true;
      try {
        await api.aiAddon.deleteTaskConfig(taskType);
        const { data } = await api.aiAddon.getTaskConfig();
        if (data) {
          taskConfigData.value = data;
        }
      }
      catch (_e) {
        // Silently handle
      }
      finally {
        deletingTask[taskType] = false;
      }
    }

    return {
      $globals,
      isAdmin,
      loading,
      providerStatusMap,
      keyInputs,
      savingKey,
      deletingKey,
      keyFeedback,
      budgetStatus,
      budgetCapInput,
      savingBudget,
      budgetFeedback,
      taskConfigData,
      tierSelectItems,
      tierDisplayMap,
      tierCostMap,
      deletingTask,
      ratingHistory,
      ratingHistoryTotal,
      ratingHistoryLoading,
      ratingHistoryError,
      cuisineWeights,
      cuisineWeightsLoading,
      saveProviderKey,
      deleteProviderKey,
      saveBudget,
      updateTaskConfig,
      deleteTaskConfig,
      loadMoreRatings,
      formatRatingDate,
    };
  },
});
</script>
