<template>
  <div>
    <div class="mb-4">
      <h2 class="text-h6 font-weight-medium mb-1">
        Dietary Preferences
      </h2>
      <p class="text-body-2 text-medium-emphasis">
        Select any dietary preferences or restrictions. These guide meal style recommendations.
      </p>
    </div>

    <v-chip-group
      :model-value="modelValue"
      multiple
      selected-class="text-primary"
      filter
      @update:model-value="$emit('update:modelValue', $event)"
    >
      <v-chip
        v-for="restriction in DIETARY_RESTRICTIONS"
        :key="restriction.id"
        :value="restriction.id"
        variant="outlined"
      >
        {{ restriction.label }}
      </v-chip>
    </v-chip-group>

    <p
      v-if="modelValue.length === 0"
      class="text-body-2 text-medium-emphasis mt-3"
    >
      No dietary preferences selected. Click any chip above to add one.
    </p>
    <p
      v-else
      class="text-body-2 text-medium-emphasis mt-3"
    >
      Selected: {{ modelValue.join(", ") }}
    </p>
  </div>
</template>

<script lang="ts">
const DIETARY_RESTRICTIONS = [
  { id: "vegetarian", label: "Vegetarian" },
  { id: "vegan", label: "Vegan" },
  { id: "halal", label: "Halal" },
  { id: "kosher", label: "Kosher" },
  { id: "keto", label: "Keto" },
  { id: "paleo", label: "Paleo" },
  { id: "pescatarian", label: "Pescatarian" },
  { id: "low_carb", label: "Low-Carb" },
  { id: "low_sodium", label: "Low-Sodium" },
  { id: "gluten_free", label: "Gluten-Free" },
];

export default defineNuxtComponent({
  props: {
    modelValue: {
      type: Array as () => string[],
      required: true,
    },
  },
  emits: ["update:modelValue"],
  setup() {
    return {
      DIETARY_RESTRICTIONS,
    };
  },
});
</script>
