<template>
  <div>
    <div class="mb-4">
      <h2 class="text-h6 font-weight-medium mb-1">
        Rate Your Recipes
      </h2>
      <p class="text-body-2 text-medium-emphasis">
        Rate recipes from your Mealie library. This helps us understand your taste preferences from the start. Completely optional.
      </p>
    </div>

    <div
      v-if="loading"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
      <p class="text-body-2 text-medium-emphasis mt-3">
        Loading your recipes...
      </p>
    </div>

    <v-alert
      v-else-if="recipes.length === 0"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      <p class="text-body-2 mb-0">
        No recipes in your library yet. You can rate recipes later from the preferences page.
        Feel free to continue to the next step.
      </p>
    </v-alert>

    <div v-else>
      <v-card
        v-for="recipe in recipes"
        :key="recipe.slug"
        variant="outlined"
        class="mb-3"
      >
        <v-card-text>
          <div class="d-flex align-center justify-space-between flex-wrap gap-2">
            <span class="text-body-1 font-weight-medium">{{ recipe.name }}</span>
            <v-rating
              v-model="ratings[recipe.slug]"
              :length="5"
              color="amber"
              density="compact"
              half-increments
            />
          </div>
        </v-card-text>
      </v-card>

      <p class="text-caption text-medium-emphasis mt-2">
        Rating {{ ratedCount }} of {{ recipes.length }} recipes. You can skip any you haven't tried.
      </p>
    </div>
  </div>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";
import type { SeedRatingIn } from "~/lib/api/user/ai-addon";

interface RecipeSummary {
  slug: string;
  name: string;
}

export default defineNuxtComponent({
  setup() {
    const api = useUserApi();
    const recipes = ref<RecipeSummary[]>([]);
    const ratings = ref<Record<string, number>>({});
    const loading = ref(true);

    const ratedCount = computed(() => {
      return Object.values(ratings.value).filter((r) => r > 0).length;
    });

    onMounted(async () => {
      try {
        const { data } = await api.recipes.getAll(1, 10);
        if (data && data.items) {
          recipes.value = data.items.map((r: RecipeSummary) => ({
            slug: r.slug,
            name: r.name,
          }));
        }
      }
      catch (_e) {
        // If recipes can't be fetched, just show empty state
        recipes.value = [];
      }
      finally {
        loading.value = false;
      }
    });

    function getRatings(): SeedRatingIn[] {
      return Object.entries(ratings.value)
        .filter(([, r]) => r > 0)
        .map(([slug, rating]) => ({
          recipeSlug: slug,
          recipeName: recipes.value.find((r) => r.slug === slug)?.name ?? slug,
          rating: Math.round(rating),
        }));
    }

    return {
      recipes,
      ratings,
      loading,
      ratedCount,
      getRatings,
    };
  },
});
</script>
