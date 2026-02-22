<template>
  <v-container class="px-2 py-4">
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold">
              Addon Debug
            </h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              AI Addon health and status information
            </p>
          </div>
          <div class="d-flex gap-2">
            <v-btn
              :loading="loading"
              variant="tonal"
              :prepend-icon="$globals.icons.refresh"
              @click="fetchHealth"
            >
              Refresh
            </v-btn>
            <v-btn
              variant="text"
              :to="'/ai-meal-planner'"
              :prepend-icon="$globals.icons.arrowLeftBold"
            >
              Back
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-row v-if="error">
      <v-col cols="12">
        <v-alert
          type="error"
          variant="tonal"
        >
          Failed to fetch addon health: {{ error }}
        </v-alert>
      </v-col>
    </v-row>

    <v-row v-if="health">
      <!-- Overall Status -->
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title class="text-subtitle-1 font-weight-medium">
            Overall Status
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon
                    :color="health.status === 'healthy' ? 'success' : 'warning'"
                    class="mr-2"
                  >
                    {{ health.status === 'healthy' ? $globals.icons.checkboxMarkedCircle : $globals.icons.alertCircle }}
                  </v-icon>
                </template>
                <v-list-item-title>Addon Status</v-list-item-title>
                <template #append>
                  <v-chip
                    :color="health.status === 'healthy' ? 'success' : 'warning'"
                    size="small"
                    variant="tonal"
                  >
                    {{ health.status }}
                  </v-chip>
                </template>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Addon Version</v-list-item-title>
                <template #append>
                  <span class="text-caption text-medium-emphasis">{{ health.addonVersion }}</span>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Connectivity -->
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title class="text-subtitle-1 font-weight-medium">
            Connectivity
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon
                    :color="health.databaseOk ? 'success' : 'error'"
                    class="mr-2"
                  >
                    {{ health.databaseOk ? $globals.icons.checkboxMarkedCircle : $globals.icons.alertCircle }}
                  </v-icon>
                </template>
                <v-list-item-title>Database</v-list-item-title>
                <template #append>
                  <v-chip
                    :color="health.databaseOk ? 'success' : 'error'"
                    size="small"
                    variant="tonal"
                  >
                    {{ health.databaseOk ? 'Connected' : 'Failed' }}
                  </v-chip>
                </template>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon
                    :color="health.mealieApiOk ? 'success' : 'error'"
                    class="mr-2"
                  >
                    {{ health.mealieApiOk ? $globals.icons.checkboxMarkedCircle : $globals.icons.alertCircle }}
                  </v-icon>
                </template>
                <v-list-item-title>Mealie API</v-list-item-title>
                <template #append>
                  <v-chip
                    :color="health.mealieApiOk ? 'success' : 'error'"
                    size="small"
                    variant="tonal"
                  >
                    {{ health.mealieApiOk ? 'OK' : 'Failed' }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Config Summary -->
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-subtitle-1 font-weight-medium">
            Config Summary
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item
                v-for="(value, key) in health.configSummary"
                :key="key"
              >
                <v-list-item-title>{{ formatKey(String(key)) }}</v-list-item-title>
                <template #append>
                  <span class="text-caption text-medium-emphasis">{{ value }}</span>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="!health && !loading && !error">
      <v-col cols="12">
        <v-card>
          <v-card-text class="text-center text-medium-emphasis py-8">
            No health data available. Click Refresh to fetch addon status.
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import type { AddonHealthResponse } from "~/lib/api/user/ai-addon";

definePageMeta({
  middleware: ["auth"],
});

export default defineNuxtComponent({
  setup() {
    const { $api, $globals } = useNuxtApp();

    const health = ref<AddonHealthResponse | null>(null);
    const loading = ref<boolean>(false);
    const error = ref<string | null>(null);

    async function fetchHealth() {
      loading.value = true;
      error.value = null;
      try {
        const { data, error: apiError } = await $api.aiAddon.getHealth();
        if (apiError) {
          error.value = String(apiError);
        }
        else {
          health.value = data;
        }
      }
      catch (e) {
        error.value = String(e);
      }
      finally {
        loading.value = false;
      }
    }

    function formatKey(key: string): string {
      return key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
    }

    onMounted(() => {
      fetchHealth();
    });

    return {
      health,
      loading,
      error,
      fetchHealth,
      formatKey,
    };
  },
});
</script>
