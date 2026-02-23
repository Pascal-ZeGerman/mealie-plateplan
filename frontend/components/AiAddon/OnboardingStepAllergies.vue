<template>
  <div>
    <div class="mb-4">
      <h2 class="text-h6 font-weight-medium mb-1">
        Food Allergies
      </h2>
      <p class="text-body-2 text-medium-emphasis">
        Select any food allergies. We'll ensure your meal plans avoid these ingredients.
      </p>
    </div>

    <v-chip-group
      :model-value="modelValue"
      multiple
      selected-class="text-error"
      filter
      @update:model-value="$emit('update:modelValue', $event)"
    >
      <v-chip
        v-for="allergy in ALLERGIES"
        :key="allergy.id"
        :value="allergy.id"
        variant="outlined"
      >
        {{ allergy.label }}
      </v-chip>
    </v-chip-group>

    <p
      v-if="modelValue.length === 0"
      class="text-body-2 text-medium-emphasis mt-3"
    >
      No allergies selected. Click any chip above to add an allergy.
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
const ALLERGIES = [
  { id: "nut", label: "Nut" },
  { id: "shellfish", label: "Shellfish" },
  { id: "dairy", label: "Dairy" },
  { id: "gluten", label: "Gluten" },
  { id: "egg", label: "Egg" },
  { id: "soy", label: "Soy" },
  { id: "wheat", label: "Wheat" },
  { id: "fish", label: "Fish" },
  { id: "sesame", label: "Sesame" },
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
      ALLERGIES,
    };
  },
});
</script>
