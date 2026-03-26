<template>
  <v-dialog v-model="isOpen" max-width="480">
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <span>Swap {{ slot?.mealType }} — {{ dayName }}</span>
        <v-btn icon variant="text" @click="isOpen = false">
          <v-icon>{{ $globals.icons.close }}</v-icon>
        </v-btn>
      </v-card-title>
      <v-tabs v-model="activeTab">
        <v-tab value="ai">AI Suggestions</v-tab>
        <v-tab value="browse">Browse Library</v-tab>
      </v-tabs>
      <v-window v-model="activeTab">
        <!-- Tab 1: AI Suggestions -->
        <v-window-item value="ai">
          <v-card-text>
            <!-- Loading state -->
            <div v-if="aiLoading" class="d-flex flex-column align-center py-6">
              <v-progress-circular size="32" color="primary" indeterminate />
              <p class="text-caption mt-2">Finding alternatives...</p>
            </div>
            <!-- Error state -->
            <v-alert v-else-if="aiError" type="error" variant="tonal">
              Couldn't fetch AI suggestions. Switch to Browse Library to pick manually.
            </v-alert>
            <!-- Results -->
            <v-list v-else>
              <v-list-item
                v-for="s in suggestions"
                :key="s.recipeId"
                :active="selectedRecipe?.recipeId === s.recipeId"
                active-color="primary"
                @click="selectedRecipe = s"
              >
                <v-list-item-title>{{ s.recipeName }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ s.categories.join(', ') }}
                  <span v-if="s.servings"> · {{ s.servings }} servings</span>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-window-item>
        <!-- Tab 2: Browse Library -->
        <v-window-item value="browse">
          <v-card-text>
            <v-text-field
              v-model="searchQuery"
              label="Search recipes..."
              :prepend-inner-icon="$globals.icons.search"
              density="compact"
              hide-details
              class="mb-3"
            />
            <v-list style="max-height: 300px; overflow-y: auto">
              <v-list-item
                v-for="r in filteredRecipes"
                :key="r.id"
                :active="selectedRecipe?.recipeId === r.id"
                active-color="primary"
                @click="selectedRecipe = { recipeId: r.id, recipeName: r.name, recipeSlug: r.slug, categories: r.categories, servings: null }"
              >
                <v-list-item-title>{{ r.name }}</v-list-item-title>
                <v-list-item-subtitle>{{ r.categories.join(', ') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-window-item>
      </v-window>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="isOpen = false">Cancel</v-btn>
        <v-btn variant="flat" color="primary" :disabled="!selectedRecipe" @click="confirmSwap">
          Use this recipe
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";
import type { MealSlotPreview, SwapSuggestion } from "~/lib/api/user/ai-addon";

interface RecipeEntry {
  id: string;
  name: string;
  slug: string;
  categories: string[];
}

interface SelectedRecipe {
  recipeId: string;
  recipeName: string;
  recipeSlug: string;
  categories: string[];
  servings: number | null;
}

export default defineNuxtComponent({
  props: {
    modelValue: {
      type: Boolean,
      required: true,
    },
    slot: {
      type: Object as () => MealSlotPreview | null,
      default: null,
    },
    dayName: {
      type: String,
      default: "",
    },
    allRecipes: {
      type: Array as () => RecipeEntry[],
      default: () => [],
    },
  },

  emits: ["update:modelValue", "select"],

  setup(props, { emit }) {
    const { $globals } = useNuxtApp();
    const api = useUserApi();

    const activeTab = ref<"ai" | "browse">("ai");
    const aiLoading = ref(false);
    const aiError = ref(false);
    const suggestions = ref<SwapSuggestion[]>([]);
    const searchQuery = ref("");
    const selectedRecipe = ref<SelectedRecipe | null>(null);

    const isOpen = computed({
      get: () => props.modelValue,
      set: (val: boolean) => emit("update:modelValue", val),
    });

    const filteredRecipes = computed(() => {
      if (!searchQuery.value.trim()) {
        return props.allRecipes;
      }
      const q = searchQuery.value.toLowerCase();
      return props.allRecipes.filter(r => r.name.toLowerCase().includes(q));
    });

    // When dialog opens, fetch AI suggestions
    watch(
      () => props.modelValue,
      async (opened) => {
        if (!opened) {
          return;
        }
        // Reset state on open
        activeTab.value = "ai";
        aiLoading.value = true;
        aiError.value = false;
        suggestions.value = [];
        selectedRecipe.value = null;
        searchQuery.value = "";

        if (!props.slot) {
          aiLoading.value = false;
          aiError.value = true;
          return;
        }

        try {
          const { data, error } = await api.aiAddon.swapMeal({
            date: props.slot.date,
            mealType: props.slot.mealType,
            currentRecipeId: props.slot.recipeId,
            currentRecipeName: props.slot.recipeName,
          });

          if (error || !data) {
            aiError.value = true;
          }
          else {
            suggestions.value = data.suggestions;
          }
        }
        catch (_e) {
          aiError.value = true;
        }
        finally {
          aiLoading.value = false;
        }
      },
    );

    function confirmSwap() {
      if (!selectedRecipe.value) return;
      emit("select", selectedRecipe.value);
      isOpen.value = false;
    }

    return {
      $globals,
      isOpen,
      activeTab,
      aiLoading,
      aiError,
      suggestions,
      searchQuery,
      selectedRecipe,
      filteredRecipes,
      confirmSwap,
    };
  },
});
</script>
