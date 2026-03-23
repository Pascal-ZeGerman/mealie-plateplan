<template>
  <div class="meal-plan-grid-wrapper" style="overflow-x: auto;">
    <div class="meal-plan-grid d-flex flex-nowrap gap-2" style="min-width: max-content;">
      <div
        v-for="dayInfo in gridDays"
        :key="dayInfo.date"
        class="day-column"
        style="min-width: 140px; width: 140px;"
      >
        <!-- Day header -->
        <div class="text-center mb-2">
          <p class="text-h6 font-weight-bold mb-0">
            {{ dayInfo.dayName }}
          </p>
          <p class="text-caption text-medium-emphasis">
            {{ dayInfo.dateLabel }}
          </p>
        </div>

        <!-- Meal slots: breakfast, lunch, dinner -->
        <div class="d-flex flex-column gap-2">
          <template v-for="mealType in MEAL_TYPES" :key="mealType">
            <!-- Loading skeleton for non-locked slots -->
            <v-skeleton-loader
              v-if="loading && !isSlotLocked(dayInfo.date, mealType)"
              type="card"
              height="100"
            />
            <!-- Meal slot card -->
            <MealSlotCard
              v-else
              :slot="getSlot(dayInfo.date, mealType)"
              :plan-state="planState"
              :show-actions="true"
              @swap="$emit('swap', $event)"
              @lock="$emit('lock', $event)"
              @unlock="$emit('unlock', $event)"
              @remove="$emit('remove', $event)"
              @mark-dining-out="$emit('mark-dining-out', $event)"
              @unmark-dining-out="$emit('unmark-dining-out', $event)"
            />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import type { MealSlotPreview } from "~/lib/api/user/ai-addon";

const MEAL_TYPES = ["breakfast", "lunch", "dinner"] as const;
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_FULL_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().split("T")[0];
}

function formatDateLabel(dateStr: string): string {
  const [, month, day] = dateStr.split("-");
  return `${parseInt(month)}/${parseInt(day)}`;
}

const EMPTY_SLOT = (date: string, mealType: string): MealSlotPreview => ({
  date,
  mealType,
  slotType: "empty",
  recipeId: null,
  recipeName: null,
  recipeSlug: null,
  recipeServings: null,
  title: null,
  effectivePortions: 0,
  isLocked: false,
  isDiningOut: false,
});

export default defineNuxtComponent({
  props: {
    slots: {
      type: Array as () => MealSlotPreview[],
      default: () => [],
    },
    weekStart: {
      type: String,
      required: true,
    },
    planState: {
      type: String as () => "empty" | "config" | "generating" | "preview" | "committed",
      default: "empty",
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },

  emits: ["swap", "lock", "unlock", "remove", "mark-dining-out", "unmark-dining-out"],

  setup(props) {
    // Build the 7 day date strings from weekStart (Monday)
    const gridDays = computed(() =>
      Array.from({ length: 7 }, (_, i) => {
        const date = addDays(props.weekStart, i);
        return {
          date,
          dayName: DAY_NAMES[i],
          fullDayName: DAY_FULL_NAMES[i],
          dateLabel: formatDateLabel(date),
        };
      })
    );

    // Build a lookup map: "date-mealType" -> slot
    const slotMap = computed(() => {
      const map = new Map<string, MealSlotPreview>();
      for (const slot of props.slots) {
        map.set(`${slot.date}-${slot.mealType}`, slot);
      }
      return map;
    });

    function getSlot(date: string, mealType: string): MealSlotPreview {
      return slotMap.value.get(`${date}-${mealType}`) ?? EMPTY_SLOT(date, mealType);
    }

    function isSlotLocked(date: string, mealType: string): boolean {
      return slotMap.value.get(`${date}-${mealType}`)?.isLocked ?? false;
    }

    return {
      MEAL_TYPES,
      gridDays,
      getSlot,
      isSlotLocked,
    };
  },
});
</script>
