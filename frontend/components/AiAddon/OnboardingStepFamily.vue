<template>
  <div>
    <div class="mb-4">
      <h2 class="text-h6 font-weight-medium mb-1">
        Family Profile
      </h2>
      <p class="text-body-2 text-medium-emphasis">
        Tell us about your household. We'll calculate how many portions each meal should make.
      </p>
    </div>

    <v-card
      variant="outlined"
      class="mb-4"
    >
      <v-card-text>
        <v-row
          v-for="group in AGE_GROUPS"
          :key="group.key"
          class="align-center mb-2"
        >
          <v-col
            cols="12"
            sm="5"
          >
            <div>
              <span class="text-body-1 font-weight-medium">{{ group.label }}</span>
              <div class="text-caption text-medium-emphasis">
                {{ group.range }}
              </div>
            </div>
          </v-col>
          <v-col
            cols="12"
            sm="7"
          >
            <div class="d-flex align-center gap-2">
              <v-btn
                icon
                size="small"
                variant="outlined"
                :disabled="getCount(group.key) <= 0"
                @click="decrement(group.key)"
              >
                <v-icon size="small">
                  mdi-minus
                </v-icon>
              </v-btn>
              <span class="text-h6 mx-3 min-width-24 text-center">{{ getCount(group.key) }}</span>
              <v-btn
                icon
                size="small"
                variant="outlined"
                :disabled="getCount(group.key) >= 20"
                @click="increment(group.key)"
              >
                <v-icon size="small">
                  mdi-plus
                </v-icon>
              </v-btn>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card variant="outlined">
      <v-card-text>
        <div class="d-flex align-center justify-space-between mb-2">
          <div>
            <span class="text-body-1 font-weight-medium">Portions per meal</span>
            <div class="text-caption text-medium-emphasis">
              Based on your household composition
            </div>
          </div>
          <v-chip
            color="primary"
            variant="tonal"
          >
            {{ portionOverride !== null ? portionOverride : calculatedPortions.toFixed(1) }}
            <span
              v-if="portionOverride === null"
              class="ml-1 text-caption"
            >(auto)</span>
          </v-chip>
        </div>

        <div class="text-caption text-medium-emphasis mb-3">
          Formula: Adults (x1.0) + Teens (x1.0) + Children (x0.5) + Toddlers (x0.25)
        </div>

        <v-checkbox
          v-model="showOverride"
          label="Customize portions manually"
          density="compact"
          hide-details
          class="mb-2"
          @update:model-value="onOverrideToggle"
        />

        <v-text-field
          v-if="showOverride"
          :model-value="portionOverride"
          label="Custom portions"
          type="number"
          min="0.5"
          max="50"
          step="0.5"
          variant="outlined"
          density="compact"
          suffix="portions"
          @update:model-value="onPortionOverrideChange"
        />
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
const AGE_GROUPS = [
  { key: "familyAdults", label: "Adults", range: "18+" },
  { key: "familyTeens", label: "Teens", range: "13-17" },
  { key: "familyChildren", label: "Children", range: "4-12" },
  { key: "familyToddlers", label: "Toddlers", range: "1-3" },
];

export interface FamilyModelValue {
  familyAdults: number;
  familyTeens: number;
  familyChildren: number;
  familyToddlers: number;
  portionOverride: number | null;
}

export default defineNuxtComponent({
  props: {
    modelValue: {
      type: Object as () => FamilyModelValue,
      required: true,
    },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const showOverride = ref(props.modelValue.portionOverride !== null);

    const calculatedPortions = computed(() => {
      return (
        props.modelValue.familyAdults * 1.0
        + props.modelValue.familyTeens * 1.0
        + props.modelValue.familyChildren * 0.5
        + props.modelValue.familyToddlers * 0.25
      );
    });

    const portionOverride = computed(() => props.modelValue.portionOverride);

    function getCount(key: string): number {
      return (props.modelValue as Record<string, number | null>)[key] as number ?? 0;
    }

    function increment(key: string) {
      const current = getCount(key);
      if (current < 20) {
        emit("update:modelValue", { ...props.modelValue, [key]: current + 1 });
      }
    }

    function decrement(key: string) {
      const current = getCount(key);
      if (current > 0) {
        emit("update:modelValue", { ...props.modelValue, [key]: current - 1 });
      }
    }

    function onOverrideToggle(enabled: boolean) {
      if (!enabled) {
        emit("update:modelValue", { ...props.modelValue, portionOverride: null });
      }
      else {
        // Default to the calculated value when enabling override
        emit("update:modelValue", {
          ...props.modelValue,
          portionOverride: Math.max(0.5, calculatedPortions.value),
        });
      }
    }

    function onPortionOverrideChange(value: string | number) {
      const parsed = typeof value === "string" ? parseFloat(value) : value;
      if (!isNaN(parsed) && parsed >= 0.5 && parsed <= 50) {
        emit("update:modelValue", { ...props.modelValue, portionOverride: parsed });
      }
    }

    return {
      AGE_GROUPS,
      showOverride,
      calculatedPortions,
      portionOverride,
      getCount,
      increment,
      decrement,
      onOverrideToggle,
      onPortionOverrideChange,
    };
  },
});
</script>
