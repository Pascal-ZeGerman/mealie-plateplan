<template>
  <div>
    <div class="mb-4">
      <h2 class="text-h6 font-weight-medium mb-1">
        Cuisine Preferences
      </h2>
      <p class="text-body-2 text-medium-emphasis">
        Tell us how much you enjoy each cuisine. This helps us suggest meals you'll love.
      </p>
    </div>

    <v-row>
      <v-col
        v-for="cuisine in CUISINES"
        :key="cuisine.id"
        cols="12"
        sm="6"
        md="4"
      >
        <v-card
          variant="outlined"
          class="pa-3"
        >
          <div class="text-body-1 font-weight-medium mb-2">
            {{ cuisine.label }}
          </div>
          <v-btn-toggle
            :model-value="modelValue[cuisine.id]"
            mandatory
            density="compact"
            color="primary"
            class="w-100"
            @update:model-value="onCuisineChange(cuisine.id, $event)"
          >
            <v-btn
              value="love"
              size="small"
              class="flex-grow-1"
            >
              Love
            </v-btn>
            <v-btn
              value="neutral"
              size="small"
              class="flex-grow-1"
            >
              Neutral
            </v-btn>
            <v-btn
              value="dislike"
              size="small"
              class="flex-grow-1"
            >
              Dislike
            </v-btn>
          </v-btn-toggle>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
const CUISINES = [
  { id: "italian", label: "Italian" },
  { id: "mexican", label: "Mexican" },
  { id: "chinese", label: "Chinese" },
  { id: "japanese", label: "Japanese" },
  { id: "indian", label: "Indian" },
  { id: "thai", label: "Thai" },
  { id: "mediterranean", label: "Mediterranean" },
  { id: "american", label: "American" },
  { id: "french", label: "French" },
  { id: "middle_eastern", label: "Middle Eastern" },
];

export default defineNuxtComponent({
  props: {
    modelValue: {
      type: Object as () => Record<string, "love" | "neutral" | "dislike">,
      required: true,
    },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    function onCuisineChange(cuisineId: string, value: "love" | "neutral" | "dislike") {
      emit("update:modelValue", {
        ...props.modelValue,
        [cuisineId]: value,
      });
    }

    return {
      CUISINES,
      onCuisineChange,
    };
  },
});
</script>
