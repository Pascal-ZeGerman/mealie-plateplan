<template>
  <div>
    <div class="mb-4">
      <h2 class="text-h6 font-weight-medium mb-1">
        Review Your Preferences
      </h2>
      <p class="text-body-2 text-medium-emphasis">
        Here's a summary of everything you've set up. Click any "Edit" link to go back and change a section.
      </p>
    </div>

    <!-- Cuisine Preferences -->
    <v-card
      variant="outlined"
      class="mb-3"
    >
      <v-card-title class="d-flex align-center justify-space-between py-2 px-4">
        <span class="text-body-1 font-weight-medium">Cuisine Preferences</span>
        <v-btn
          variant="text"
          size="small"
          color="primary"
          @click="$emit('go-to-step', 1)"
        >
          Edit
        </v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <div v-if="lovedCuisines.length > 0">
          <div class="mb-1">
            <span class="text-caption text-medium-emphasis">Love: </span>
            <span class="text-body-2">{{ lovedCuisines.join(", ") }}</span>
          </div>
        </div>
        <div v-if="dislikedCuisines.length > 0">
          <div class="mb-1">
            <span class="text-caption text-medium-emphasis">Dislike: </span>
            <span class="text-body-2">{{ dislikedCuisines.join(", ") }}</span>
          </div>
        </div>
        <div v-if="lovedCuisines.length === 0 && dislikedCuisines.length === 0">
          <span class="text-body-2 text-medium-emphasis">All cuisines set to Neutral (default)</span>
        </div>
      </v-card-text>
    </v-card>

    <!-- Allergies -->
    <v-card
      variant="outlined"
      class="mb-3"
    >
      <v-card-title class="d-flex align-center justify-space-between py-2 px-4">
        <span class="text-body-1 font-weight-medium">Food Allergies</span>
        <v-btn
          variant="text"
          size="small"
          color="primary"
          @click="$emit('go-to-step', 2)"
        >
          Edit
        </v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <span
          v-if="allergies.length === 0"
          class="text-body-2 text-medium-emphasis"
        >None</span>
        <div
          v-else
          class="d-flex flex-wrap gap-1"
        >
          <v-chip
            v-for="a in allergies"
            :key="a"
            size="small"
            color="error"
            variant="tonal"
          >
            {{ a }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Dietary Restrictions -->
    <v-card
      variant="outlined"
      class="mb-3"
    >
      <v-card-title class="d-flex align-center justify-space-between py-2 px-4">
        <span class="text-body-1 font-weight-medium">Dietary Preferences</span>
        <v-btn
          variant="text"
          size="small"
          color="primary"
          @click="$emit('go-to-step', 3)"
        >
          Edit
        </v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <span
          v-if="dietaryRestrictions.length === 0"
          class="text-body-2 text-medium-emphasis"
        >None</span>
        <div
          v-else
          class="d-flex flex-wrap gap-1"
        >
          <v-chip
            v-for="d in dietaryRestrictions"
            :key="d"
            size="small"
            color="primary"
            variant="tonal"
          >
            {{ d }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Family -->
    <v-card
      variant="outlined"
      class="mb-3"
    >
      <v-card-title class="d-flex align-center justify-space-between py-2 px-4">
        <span class="text-body-1 font-weight-medium">Family Profile</span>
        <v-btn
          variant="text"
          size="small"
          color="primary"
          @click="$emit('go-to-step', 4)"
        >
          Edit
        </v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <p class="text-body-2 mb-1">
          {{ familySummary }}
        </p>
        <p class="text-caption text-medium-emphasis">
          {{ portionsSummary }}
        </p>
      </v-card-text>
    </v-card>

    <!-- Seed Ratings -->
    <v-card
      variant="outlined"
      class="mb-3"
    >
      <v-card-title class="d-flex align-center justify-space-between py-2 px-4">
        <span class="text-body-1 font-weight-medium">Recipe Ratings</span>
        <v-btn
          variant="text"
          size="small"
          color="primary"
          @click="$emit('go-to-step', 5)"
        >
          Edit
        </v-btn>
      </v-card-title>
      <v-card-text class="pt-0">
        <span class="text-body-2 text-medium-emphasis">
          {{ seedRatingCount > 0 ? `Rated ${seedRatingCount} recipe${seedRatingCount === 1 ? '' : 's'}` : 'No recipes rated yet' }}
        </span>
      </v-card-text>
    </v-card>

    <v-alert
      type="success"
      variant="tonal"
      class="mt-4"
    >
      <p class="text-body-2 mb-0">
        Everything looks good! Click "Complete Setup" below to save and start using the AI Meal Planner.
      </p>
    </v-alert>
  </div>
</template>

<script lang="ts">
interface ReviewProps {
  cuisinePreferences: Record<string, "love" | "neutral" | "dislike">;
  allergies: string[];
  dietaryRestrictions: string[];
  familyAdults: number;
  familyTeens: number;
  familyChildren: number;
  familyToddlers: number;
  portionOverride: number | null;
  seedRatingCount: number;
}

export default defineNuxtComponent({
  props: {
    cuisinePreferences: {
      type: Object as () => Record<string, "love" | "neutral" | "dislike">,
      required: true,
    },
    allergies: {
      type: Array as () => string[],
      required: true,
    },
    dietaryRestrictions: {
      type: Array as () => string[],
      required: true,
    },
    familyAdults: {
      type: Number,
      required: true,
    },
    familyTeens: {
      type: Number,
      required: true,
    },
    familyChildren: {
      type: Number,
      required: true,
    },
    familyToddlers: {
      type: Number,
      required: true,
    },
    portionOverride: {
      type: Number as () => number | null,
      default: null,
    },
    seedRatingCount: {
      type: Number,
      default: 0,
    },
  },
  emits: ["go-to-step"],
  setup(props: ReviewProps) {
    const CUISINE_LABELS: Record<string, string> = {
      italian: "Italian",
      mexican: "Mexican",
      chinese: "Chinese",
      japanese: "Japanese",
      indian: "Indian",
      thai: "Thai",
      mediterranean: "Mediterranean",
      american: "American",
      french: "French",
      middle_eastern: "Middle Eastern",
    };

    const lovedCuisines = computed(() =>
      Object.entries(props.cuisinePreferences)
        .filter(([, v]) => v === "love")
        .map(([k]) => CUISINE_LABELS[k] ?? k),
    );

    const dislikedCuisines = computed(() =>
      Object.entries(props.cuisinePreferences)
        .filter(([, v]) => v === "dislike")
        .map(([k]) => CUISINE_LABELS[k] ?? k),
    );

    const familySummary = computed(() => {
      const parts: string[] = [];
      if (props.familyAdults > 0) parts.push(`${props.familyAdults} Adult${props.familyAdults !== 1 ? "s" : ""}`);
      if (props.familyTeens > 0) parts.push(`${props.familyTeens} Teen${props.familyTeens !== 1 ? "s" : ""}`);
      if (props.familyChildren > 0) parts.push(`${props.familyChildren} Child${props.familyChildren !== 1 ? "ren" : ""}`);
      if (props.familyToddlers > 0) parts.push(`${props.familyToddlers} Toddler${props.familyToddlers !== 1 ? "s" : ""}`);
      return parts.length > 0 ? parts.join(", ") : "No household members set";
    });

    const calculatedPortions = computed(() => {
      return (
        props.familyAdults * 1.0
        + props.familyTeens * 1.0
        + props.familyChildren * 0.5
        + props.familyToddlers * 0.25
      );
    });

    const portionsSummary = computed(() => {
      if (props.portionOverride !== null) {
        return `${props.portionOverride} portions per meal (manual override)`;
      }
      return `${calculatedPortions.value.toFixed(1)} portions per meal (auto-calculated)`;
    });

    return {
      lovedCuisines,
      dislikedCuisines,
      familySummary,
      portionsSummary,
    };
  },
});
</script>
