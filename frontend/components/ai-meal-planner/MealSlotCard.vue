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
      <v-btn
        v-if="showActions"
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
      <v-btn
        v-if="showActions"
        icon
        size="x-small"
        variant="text"
        :aria-label="'Lock this meal — it will survive regeneration'"
        @click="$emit('lock', slot)"
      >
        <v-icon size="small">{{ $globals.icons.lockOpen }}</v-icon>
      </v-btn>
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

    <!-- Star row: always visible on committed recipe slots, OUTSIDE .slot-actions -->
    <div v-if="planState === 'committed' && slot.slotType === 'recipe'" class="star-row mt-1 mb-1">
      <v-rating
        v-model="displayStarValue"
        :length="5"
        size="small"
        color="warning"
        empty-icon="mdi-star-outline"
        :half-increments="false"
        :readonly="ratingPending"
        @update:model-value="onStarClick"
      />
      <v-progress-circular
        v-if="ratingPending"
        indeterminate
        :size="16"
        class="ml-1"
      />
    </div>

    <div v-if="showActions" class="d-flex justify-end slot-actions">
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

    <!-- Rating confirmation dialog -->
    <v-dialog v-model="showRatingDialog" max-width="360">
      <v-card>
        <v-card-title class="text-h6">
          {{ isClearing ? 'Remove rating?' : 'Save rating?' }}
        </v-card-title>
        <v-card-text>
          {{ isClearing
            ? `Remove your rating for ${slot.recipeName}? This cannot be undone.`
            : `Rate ${slot.recipeName} ${pendingValue} star${pendingValue !== 1 ? 's' : ''}?`
          }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelRating">
            {{ isClearing ? 'Keep rating' : 'Keep current rating' }}
          </v-btn>
          <v-btn
            :variant="'flat'"
            :color="isClearing ? 'error' : 'primary'"
            :loading="ratingPending"
            @click="confirmRating"
          >
            {{ isClearing ? 'Remove Rating' : 'Save Rating' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="showRatingError" :timeout="4000" color="error" location="bottom">
      Could not save your rating. Check your connection and try again.
    </v-snackbar>
  </v-card>
</template>

<script lang="ts">
import { useUserApi } from "~/composables/api";
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
    groupMealPlanId: {
      type: Number,
      default: null,
    },
  },

  emits: ["swap", "lock", "unlock", "remove", "mark-dining-out", "unmark-dining-out", "rate"],

  setup(props, { emit }) {
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

    // Rating state
    const confirmedRating = ref(props.slot.currentRating ?? 0);
    const displayStarValue = ref(props.slot.currentRating ?? 0);
    const pendingValue = ref(0);
    const showRatingDialog = ref(false);
    const ratingPending = ref(false);
    const isClearing = ref(false);
    const showRatingError = ref(false);

    // Sync when prop changes (parent updates slot after successful API call)
    watch(() => props.slot.currentRating, (newVal) => {
      confirmedRating.value = newVal ?? 0;
      displayStarValue.value = newVal ?? 0;
    });

    function onStarClick(newVal: number) {
      if (newVal === confirmedRating.value) {
        // Tapping same star = clear rating
        isClearing.value = true;
        pendingValue.value = 0;
      }
      else {
        isClearing.value = false;
        pendingValue.value = newVal;
      }
      // Immediately revert display to confirmed value (no premature visual update)
      displayStarValue.value = confirmedRating.value;
      showRatingDialog.value = true;
    }

    async function confirmRating() {
      ratingPending.value = true;
      showRatingDialog.value = false;
      try {
        const api = useUserApi();
        await api.aiAddon.submitRating({
          recipeId: props.slot.recipeId!,
          recipeName: props.slot.recipeName!,
          rating: pendingValue.value,
          groupMealPlanId: props.groupMealPlanId ?? null,
        });
        confirmedRating.value = pendingValue.value;
        displayStarValue.value = pendingValue.value;
        emit("rate", { slot: props.slot, rating: pendingValue.value });
      }
      catch (_e) {
        displayStarValue.value = confirmedRating.value;
        showRatingError.value = true;
      }
      finally {
        ratingPending.value = false;
      }
    }

    function cancelRating() {
      showRatingDialog.value = false;
      displayStarValue.value = confirmedRating.value;
    }

    return {
      $globals,
      mealTypeColor,
      showPortionBadge,
      displayStarValue,
      pendingValue,
      showRatingDialog,
      ratingPending,
      isClearing,
      showRatingError,
      onStarClick,
      confirmRating,
      cancelRating,
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

.star-row {
  /* Always visible — NOT inside .slot-actions which has hover-only opacity */
  display: flex;
  align-items: center;
}
</style>
