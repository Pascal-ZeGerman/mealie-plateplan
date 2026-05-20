<template>
  <v-card class="pa-4" :loading="loading">
    <v-card-title class="text-h6 font-weight-bold pa-0 mb-4">
      Configure Meal Plan
    </v-card-title>

    <!-- Week picker -->
    <div class="mb-4">
      <p class="text-caption text-medium-emphasis mb-2">
        Which week?
      </p>
      <v-select
        v-model="selectedWeek"
        :items="weekOptions"
        item-title="title"
        item-value="value"
        variant="outlined"
        density="compact"
        hide-details
        mandatory
      />
    </div>

    <!-- Meal type toggles -->
    <div class="mb-4">
      <p class="text-caption text-medium-emphasis mb-1">
        Meal types
      </p>
      <v-checkbox
        v-model="mealTypes"
        label="Breakfast"
        value="breakfast"
        density="compact"
        hide-details
        class="mb-1"
      />
      <v-checkbox
        v-model="mealTypes"
        label="Lunch"
        value="lunch"
        density="compact"
        hide-details
        class="mb-1"
      />
      <v-checkbox
        v-model="mealTypes"
        label="Dinner"
        value="dinner"
        density="compact"
        hide-details
      />
    </div>

    <!-- Exclude days -->
    <div class="mb-4">
      <p class="text-caption text-medium-emphasis mb-2">
        Exclude days (optional)
      </p>
      <v-chip-group
        v-model="excludedDays"
        multiple
        column
      >
        <v-chip
          v-for="day in DAYS"
          :key="day.value"
          :value="day.value"
          variant="tonal"
          filter
          size="small"
        >
          {{ day.label }}
        </v-chip>
      </v-chip-group>
    </div>

    <!-- Special requests -->
    <div class="mb-4">
      <v-textarea
        v-model="specialRequests"
        label="Any special requests? (optional)"
        rows="2"
        auto-grow
        variant="outlined"
        density="compact"
        hide-details
      />
    </div>

    <!-- Merge mode notice (when existing plan) -->
    <v-alert
      v-if="hasExistingPlan && !replaceAll"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      Existing entries will be kept. Only empty slots will be filled.
    </v-alert>

    <!-- Replace all toggle (when existing plan) -->
    <div v-if="hasExistingPlan" class="mb-4">
      <v-switch
        v-model="replaceAll"
        label="Replace all unlocked slots"
        color="warning"
        density="compact"
        hide-details
        class="mb-2"
      />
      <v-alert
        v-if="replaceAll"
        type="warning"
        density="compact"
        variant="tonal"
      >
        This will remove all unlocked meals and start fresh. Locked meals will be kept.
      </v-alert>
    </div>

    <!-- Action buttons -->
    <div class="d-flex gap-3 flex-wrap">
      <v-btn
        variant="flat"
        color="primary"
        size="large"
        :loading="loading"
        :disabled="mealTypes.length === 0"
        @click="onGenerate"
      >
        Generate Meal Plan
      </v-btn>
      <v-btn
        variant="text"
        @click="$emit('update:modelValue', false)"
      >
        Cancel Generation
      </v-btn>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { startOfWeek, addDays, format } from "date-fns";
import type { GenerateMealPlanRequest } from "~/lib/api/user/ai-addon";

const DAYS = [
  { value: "monday", label: "Mon" },
  { value: "tuesday", label: "Tue" },
  { value: "wednesday", label: "Wed" },
  { value: "thursday", label: "Thu" },
  { value: "friday", label: "Fri" },
  { value: "saturday", label: "Sat" },
  { value: "sunday", label: "Sun" },
];

interface Props {
  modelValue: boolean;
  hasExistingPlan: boolean;
  loading: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  hasExistingPlan: false,
  loading: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "generate": [config: GenerateMealPlanRequest];
}>();

interface WeekOption {
  title: string;
  value: string;
}

const _today = new Date();
const _monday0 = startOfWeek(_today, { weekStartsOn: 1 });

const weekOptions: WeekOption[] = [0, 1, 2, 3].map((n) => {
  const mon = addDays(_monday0, n * 7);
  const sun = addDays(mon, 6);
  return {
    title: `${format(mon, "EEE MMM d")} – ${format(sun, "EEE MMM d")}`,
    value: format(mon, "yyyy-MM-dd"),
  };
});

// Smart week default: Mon-Wed (days 1-3) => this week, Thu-Sun (days 4-0) => next week
const dayOfWeek = _today.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat
const defaultIso = (dayOfWeek >= 1 && dayOfWeek <= 3)
  ? weekOptions[0].value
  : weekOptions[1].value;

const selectedWeek = ref<string>(defaultIso);
const mealTypes = ref<string[]>(["breakfast", "lunch", "dinner"]);
const excludedDays = ref<string[]>([]);
const specialRequests = ref("");
const replaceAll = ref(false);

function onGenerate() {
  const config: GenerateMealPlanRequest = {
    weekStart: selectedWeek.value,
    mealTypes: mealTypes.value,
    excludedDays: excludedDays.value,
    specialRequests: specialRequests.value.trim() || undefined,
    replaceUnlocked: replaceAll.value,
  };
  emit("generate", config);
}
</script>
