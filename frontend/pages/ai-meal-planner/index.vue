<template>
  <v-container class="px-2 py-4">
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold">
              AI Meal Planner
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              AI-powered meal planning
            </p>
          </div>
          <div class="d-flex align-center">
            <v-icon
              color="success"
              size="small"
              class="mr-1"
            >
              {{ $globals.icons.checkboxMarkedCircle }}
            </v-icon>
            <span class="text-caption text-medium-emphasis">Active</span>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-text>
            <p class="text-body-1 mb-4">
              Your AI meal planner is set up and ready. Feature availability is coming in future updates.
            </p>
            <div class="d-flex gap-3 flex-wrap">
              <v-tooltip
                v-for="tab in tabs"
                :key="tab.label"
                location="bottom"
                :text="tab.tooltip"
              >
                <template #activator="{ props }">
                  <v-chip
                    v-bind="props"
                    :prepend-icon="tab.icon"
                    disabled
                    variant="tonal"
                    class="cursor-not-allowed"
                  >
                    {{ tab.label }}
                  </v-chip>
                </template>
              </v-tooltip>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row
      v-if="isAdmin"
      class="mt-2"
    >
      <v-col cols="12">
        <v-card
          variant="outlined"
        >
          <v-card-text class="py-2">
            <div class="d-flex align-center">
              <v-icon
                size="small"
                color="secondary"
                class="mr-2"
              >
                {{ $globals.icons.wrench }}
              </v-icon>
              <span class="text-caption text-medium-emphasis mr-3">Admin</span>
              <NuxtLink
                to="/ai-meal-planner/debug"
                class="text-caption text-decoration-none text-primary"
              >
                View addon debug info
              </NuxtLink>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
export default defineNuxtComponent({
  setup() {
    const { $globals } = useNuxtApp();
    const auth = useMealieAuth();

    const isAdmin = computed(() => auth.user.value?.admin ?? false);

    const tabs = [
      {
        label: "Meal Plans",
        icon: $globals.icons.calendarMultiselect,
        tooltip: "Coming in a future update",
      },
      {
        label: "Preferences",
        icon: $globals.icons.cog,
        tooltip: "Coming in a future update",
      },
      {
        label: "Settings",
        icon: $globals.icons.cog,
        tooltip: "Coming in a future update",
      },
    ];

    return {
      isAdmin,
      tabs,
    };
  },
});
</script>
