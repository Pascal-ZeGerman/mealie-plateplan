<template>
  <!-- Dining-out slot -->
  <v-card
    v-if="slot.isDiningOut"
    variant="tonal"
    color="secondary"
    rounded="lg"
    class="pa-2 slot-card"
    min-height="44"
  >
    <div class="d-flex align-center justify-space-between mb-1">
      <v-chip
        :color="mealTypeColor"
        size="x-small"
        variant="flat"
        class="text-uppercase"
      >
        {{ slot.mealType }}
      </v-chip>
      <v-icon size="small" color="secondary">
        {{ $globals.icons.silverwareForkKnife || $globals.icons.restaurant }}
      </v-icon>
    </div>
    <p class="text-body-1 font-weight-bold mb-2" style="color: inherit;">
      Dining Out
    </p>
    <v-btn
      variant="text"
      size="x-small"
      color="secondary"
      @click="$emit('unmark-dining-out', slot)"
    >
      Un-mark dining out
    </v-btn>
  </v-card>

  <!-- Empty slot -->
  <v-card
    v-else-if="slot.slotType === 'empty' || (!slot.recipeId && !slot.title && !slot.isDiningOut)"
    variant="outlined"
    rounded="lg"
    class="pa-2 slot-card d-flex align-center justify-center"
    min-height="44"
    style="border-style: dashed; border-color: rgba(var(--v-theme-on-surface), 0.2); cursor: pointer;"
    @click="$emit('mark-dining-out', slot)"
  >
    <v-icon color="medium-emphasis" size="small">
      {{ $globals.icons.plus }}
    </v-icon>
  </v-card>

  <!-- Text slot (leftover/text type) -->
  <v-card
    v-else-if="slot.slotType === 'text'"
    variant="flat"
    rounded="lg"
    class="pa-2 slot-card"
    min-height="44"
  >
    <v-chip
      :color="mealTypeColor"
      size="x-small"
      variant="flat"
      class="text-uppercase mb-1"
    >
      {{ slot.mealType }}
    </v-chip>
    <p class="text-body-1 mb-2" style="font-style: italic;">
      {{ slot.title }}
    </p>
    <div v-if="showActions && planState === 'preview'" class="d-flex justify-end slot-actions">
      <v-btn
        icon
        size="x-small"
        variant="text"
        :aria-label="'Remove from plan'"
        @click="$emit('remove', slot)"
      >
        <v-icon size="small">{{ $globals.icons.delete }}</v-icon>
      </v-btn>
    </div>
  </v-card>

  <!-- Locked recipe slot -->
  <v-card
    v-else-if="slot.isLocked"
    variant="outlined"
    rounded="lg"
    class="pa-2 slot-card"
    min-height="44"
    :style="{ borderColor: 'rgb(var(--v-theme-success))' }"
  >
    <div class="d-flex align-center justify-space-between mb-1">
      <v-chip
        :color="mealTypeColor"
        size="x-small"
        variant="flat"
        class="text-uppercase"
      >
        {{ slot.mealType }}
      </v-chip>
      <v-icon size="small" color="success">
        {{ $globals.icons.lock }}
      </v-icon>
    </div>
    <p
      class="text-body-1 font-weight-bold mb-1"
      style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
    >
      {{ slot.recipeName }}
    </p>
    <p
      v-if="showPortionBadge"
      class="text-caption text-medium-emphasis mb-1"
    >
      Serves {{ slot.effectivePortions }}×
    </p>
    <div v-if="showActions" class="d-flex justify-end slot-actions">
      <v-btn
        icon
        size="x-small"
        variant="text"
        color="success"
        :aria-label="'Unlock this meal'"
        @click="$emit('unlock', slot)"
      >
        <v-icon size="small">{{ $globals.icons.lock }}</v-icon>
      </v-btn>
    </div>
  </v-card>

  <!-- Normal recipe slot -->
  <v-card
    v-else
    variant="outlined"
    rounded="lg"
    class="pa-2 slot-card"
    min-height="44"
  >
    <div class="d-flex align-center justify-space-between mb-1">
      <v-chip
        :color="mealTypeColor"
        size="x-small"
        variant="flat"
        class="text-uppercase"
      >
        {{ slot.mealType }}
      </v-chip>
    </div>
    <p
      class="text-body-1 font-weight-bold mb-1"
      style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
    >
      {{ slot.recipeName }}
    </p>
    <p
      v-if="showPortionBadge"
      class="text-caption text-medium-emphasis mb-1"
    >
      Serves {{ slot.effectivePortions }}×
    </p>
    <div v-if="showActions" class="d-flex justify-end gap-1 slot-actions">
      <v-btn
        icon
        size="x-small"
        variant="text"
        :aria-label="'Swap this meal'"
        @click="$emit('swap', slot)"
      >
        <v-icon size="small">{{ $globals.icons.sync }}</v-icon>
      </v-btn>
      <v-btn
        icon
        size="x-small"
        variant="text"
        :aria-label="'Lock this meal — it will survive regeneration'"
        @click="$emit('lock', slot)"
      >
        <v-icon size="small">{{ $globals.icons.lockOpen }}</v-icon>
      </v-btn>
      <v-btn
        v-if="planState === 'preview'"
        icon
        size="x-small"
        variant="text"
        :aria-label="'Remove from plan'"
        @click="$emit('remove', slot)"
      >
        <v-icon size="small">{{ $globals.icons.delete }}</v-icon>
      </v-btn>
    </div>
  </v-card>
</template>

<script lang="ts">
import type { MealSlotPreview } from "~/lib/api/user/ai-addon";

export default defineNuxtComponent({
  props: {
    slot: {
      type: Object as () => MealSlotPreview,
      required: true,
    },
    planState: {
      type: String as () => "preview" | "committed" | "empty",
      default: "preview",
    },
    showActions: {
      type: Boolean,
      default: true,
    },
  },

  emits: ["swap", "lock", "unlock", "remove", "mark-dining-out", "unmark-dining-out"],

  setup(props) {
    const { $globals } = useNuxtApp();

    const mealTypeColor = computed(() => {
      switch (props.slot.mealType) {
        case "breakfast": return "info";
        case "lunch": return "secondary";
        case "dinner": return "primary";
        default: return "secondary";
      }
    });

    const showPortionBadge = computed(() => {
      return props.slot.effectivePortions !== props.slot.recipeServings
        && props.slot.recipeServings !== null;
    });

    return {
      $globals,
      mealTypeColor,
      showPortionBadge,
    };
  },
});
</script>

<style scoped>
.slot-card .slot-actions {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.slot-card:hover .slot-actions {
  opacity: 1;
}

@media (max-width: 600px) {
  .slot-card .slot-actions {
    opacity: 1;
  }
}
</style>
