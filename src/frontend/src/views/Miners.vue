<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Miners</h1>
      </v-col>
    </v-row>

    <!-- Miners Grid -->
    <v-row>
      <v-col
        v-for="miner in miners"
        :key="miner.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card
          :color="getStatusColor(miner.status, 'lighten-5')"
          :class="{
            border: true,
            'border-left-4': true,
            [getBorderColor(miner.status)]: true,
          }"
          class="mx-auto"
          @click="goToMinerDetail(miner.id)"
        >
          <v-card-title class="d-flex justify-space-between">
            <span class="text-truncate">{{ miner.name }}</span>
            <v-chip :color="getStatusColor(miner.status)" small dark>
              {{ miner.status }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <v-row no-gutters>
              <v-col cols="6">
                <div class="text-subtitle-2">Type</div>
                <div>{{ miner.type }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-2">IP Address</div>
                <div>{{ miner.ip_address }}</div>
              </v-col>
            </v-row>

            <v-row no-gutters class="mt-3">
              <v-col cols="6">
                <div class="text-subtitle-2">Hashrate</div>
                <div>{{ formatHashrate(miner.hashrate) }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-2">Temperature</div>
                <div>
                  {{ formatTemperature(miner.temperature) }}
                </div>
              </v-col>
            </v-row>

            <v-row no-gutters class="mt-3">
              <v-col cols="12">
                <div class="text-subtitle-2">Shares</div>
                <div>
                  {{ miner.shares_accepted || 0 }} accepted /
                  {{ miner.shares_rejected || 0 }} rejected
                </div>
              </v-col>
            </v-row>
          </v-card-text>

          <v-divider></v-divider>

          <v-card-actions>
            <v-btn text color="primary" :to="`/miners/${miner.id}`">
              <v-icon left>mdi-eye</v-icon>
              Details
            </v-btn>

            <v-spacer></v-spacer>

            <v-btn
              text
              color="warning"
              @click.stop="confirmRestart(miner)"
              :disabled="
                miner.status === 'offline' || miner.status === 'restarting'
              "
            >
              <v-icon left>mdi-restart</v-icon>
              Restart
            </v-btn>

            <v-btn text color="error" @click.stop="confirmRemove(miner)">
              <v-icon left>mdi-delete</v-icon>
              Remove
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Empty State -->
      <v-col v-if="miners.length === 0 && !loading" cols="12">
        <v-card class="text-center pa-5">
          <v-card-text>
            <v-icon size="64" color="grey lighten-1">mdi-server-off</v-icon>
            <h3 class="mt-3">No Miners Found</h3>
            <p class="grey--text">
              Add a miner to get started or run network discovery.
            </p>
            <v-btn color="primary" class="mt-3" @click="openAddMinerDialog">
              <v-icon left>mdi-plus</v-icon>
              Add Miner
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Restart Confirmation Dialog -->
    <v-dialog v-model="restartDialog.show" max-width="400px">
      <v-card>
        <v-card-title>Restart Miner</v-card-title>
        <v-card-text>
          Are you sure you want to restart
          {{ restartDialog.miner ? restartDialog.miner.name : "" }}?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="restartDialog.show = false"> Cancel </v-btn>
          <v-btn color="warning" @click="restartMiner"> Restart </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Remove Confirmation Dialog -->
    <v-dialog v-model="removeDialog.show" max-width="400px">
      <v-card>
        <v-card-title>Remove Miner</v-card-title>
        <v-card-text>
          Are you sure you want to remove
          {{ removeDialog.miner ? removeDialog.miner.name : "" }}? This action
          cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="removeDialog.show = false"> Cancel </v-btn>
          <v-btn color="error" @click="removeMiner"> Remove </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Miner Dialog -->
    <AddMinerDialog
      v-model="addMinerDialog"
      @miner-added="handleMinerAdded"
      @error="handleMinerError"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useMinersStore } from "../stores/miners";
import { useSettingsStore } from "../stores/settings";
import { formatTemperature } from "../utils/formatters";
import AddMinerDialog from "../components/AddMinerDialog.vue";

export default {
  name: "Miners",

  components: {
    AddMinerDialog,
  },

  setup() {
    const router = useRouter();
    const minersStore = useMinersStore();
    const settingsStore = useSettingsStore();

    // Dialogs
    const restartDialog = ref({
      show: false,
      miner: null,
    });

    const removeDialog = ref({
      show: false,
      miner: null,
    });

    // Refresh interval
    let refreshInterval = null;

    // Computed properties from store
    const miners = computed(() => minersStore.miners);
    const loading = computed(() => minersStore.loading);

    // Methods
    const formatHashrate = (hashrate) => {
      if (!hashrate) return "0 H/s";

      const units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s"];
      let unitIndex = 0;

      while (hashrate >= 1000 && unitIndex < units.length - 1) {
        hashrate /= 1000;
        unitIndex++;
      }

      return `${hashrate.toFixed(2)} ${units[unitIndex]}`;
    };

    const getStatusColor = (status, variant = "") => {
      let color = "grey";

      switch (status) {
        case "online":
          color = "success";
          break;
        case "offline":
          color = "error";
          break;
        case "restarting":
          color = "warning";
          break;
        case "error":
          color = "error";
          break;
      }

      return variant ? `${color} ${variant}` : color;
    };

    const getBorderColor = (status) => {
      switch (status) {
        case "online":
          return "success-border";
        case "offline":
          return "error-border";
        case "restarting":
          return "warning-border";
        case "error":
          return "error-border";
        default:
          return "grey-border";
      }
    };

    const goToMinerDetail = (minerId) => {
      router.push(`/miners/${minerId}`);
    };

    const confirmRestart = (miner) => {
      restartDialog.value = {
        show: true,
        miner,
      };
    };

    const restartMiner = async () => {
      if (!restartDialog.value.miner) return;

      try {
        await minersStore.restartMiner(restartDialog.value.miner.id);
        restartDialog.value.show = false;
      } catch (error) {
        console.error(
          `Error restarting miner ${restartDialog.value.miner.id}:`,
          error,
        );
      }
    };

    const confirmRemove = (miner) => {
      removeDialog.value = {
        show: true,
        miner,
      };
    };

    const removeMiner = async () => {
      if (!removeDialog.value.miner) return;

      try {
        await minersStore.removeMiner(removeDialog.value.miner.id);
        removeDialog.value.show = false;
      } catch (error) {
        console.error(
          `Error removing miner ${removeDialog.value.miner.id}:`,
          error,
        );
      }
    };

    const addMinerDialog = ref(false);

    const openAddMinerDialog = () => {
      addMinerDialog.value = true;
    };

    const handleMinerAdded = (miner) => {
      console.log(`Miner "${miner.name}" added successfully`);
      // Optionally show a success message or refresh data
    };

    const handleMinerError = (error) => {
      console.error('Error adding miner:', error);
      // Optionally show an error message
    };

    // Lifecycle hooks
    onMounted(async () => {
      // Initialize miners store
      try {
        await minersStore.fetchMiners();
        minersStore.connectWebSocket();
      } catch (error) {
        console.error("Error initializing miners page:", error);
      }

      // Set up refresh interval
      const refreshTime = settingsStore.settings.refresh_interval * 1000 || 10000;
      refreshInterval = setInterval(async () => {
        try {
          await minersStore.fetchMiners();
        } catch (error) {
          console.error("Error refreshing miner data:", error);
        }
      }, refreshTime);
    });

    onUnmounted(() => {
      // Clear refresh interval
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    });

    return {
      // State
      restartDialog,
      removeDialog,
      addMinerDialog,

      // Computed
      miners,
      loading,

      // Methods
      formatHashrate,
      formatTemperature,
      getStatusColor,
      getBorderColor,
      goToMinerDetail,
      confirmRestart,
      restartMiner,
      confirmRemove,
      removeMiner,
      openAddMinerDialog,
      handleMinerAdded,
      handleMinerError,
    };
  },
};
</script>

<style scoped>
.border {
  border: 1px solid var(--color-border-subtle);
}

.border-left-4 {
  border-left-width: 4px;
}

.success-border {
  border-left-color: var(--color-success);
}

.error-border {
  border-left-color: var(--color-error);
}

.warning-border {
  border-left-color: var(--color-warning);
}

.grey-border {
  border-left-color: var(--color-border);
}

/* Enhanced card styling */
:deep(.v-card) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
  transition: all var(--transition-normal);
  cursor: pointer;
}

:deep(.v-card:hover) {
  box-shadow: var(--shadow-2);
  transform: translateY(-2px);
}

:deep(.v-card-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-card-text) {
  color: var(--color-text-primary) !important;
}

:deep(.v-card-text .text-subtitle-2) {
  color: var(--color-text-secondary) !important;
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-small);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-xs);
}

/* Status-based card colors */
:deep(.v-card[color*="success"]) {
  background-color: rgba(var(--color-success), 0.05) !important;
  border-color: rgba(var(--color-success), 0.2);
}

:deep(.v-card[color*="error"]) {
  background-color: rgba(var(--color-error), 0.05) !important;
  border-color: rgba(var(--color-error), 0.2);
}

:deep(.v-card[color*="warning"]) {
  background-color: rgba(var(--color-warning), 0.05) !important;
  border-color: rgba(var(--color-warning), 0.2);
}

:deep(.v-card[color*="grey"]) {
  background-color: var(--color-surface-variant) !important;
  border-color: var(--color-border);
}

/* Chip styling */
:deep(.v-chip) {
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
}

/* Button styling */
:deep(.v-btn) {
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
  border-radius: var(--radius-md);
}

:deep(.v-btn:hover) {
  transform: translateY(-1px);
}

:deep(.v-btn--variant-text) {
  color: var(--color-text-secondary) !important;
}

:deep(.v-btn--variant-text:hover) {
  background-color: var(--color-surface-hover) !important;
}

:deep(.v-btn[color="primary"]) {
  color: var(--color-primary) !important;
}

:deep(.v-btn[color="warning"]) {
  color: var(--color-warning) !important;
}

:deep(.v-btn[color="error"]) {
  color: var(--color-error) !important;
}

/* Divider styling */
:deep(.v-divider) {
  border-color: var(--color-border-subtle) !important;
}

/* Empty state styling */
:deep(.v-card .pa-5) {
  padding: var(--spacing-xxl) !important;
}

:deep(.v-card .pa-5 .v-icon) {
  color: var(--color-text-disabled) !important;
}

:deep(.v-card .pa-5 h3) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
  margin-top: var(--spacing-md);
}

:deep(.v-card .pa-5 p) {
  color: var(--color-text-secondary) !important;
}

/* Dialog styling */
:deep(.v-dialog .v-card) {
  background-color: var(--color-surface-elevated) !important;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-4);
  cursor: default;
}

:deep(.v-dialog .v-card:hover) {
  transform: none;
}

:deep(.v-dialog .v-card-title) {
  background-color: var(--color-surface-secondary);
  border-bottom: 1px solid var(--color-border-subtle);
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-dialog .v-card-text) {
  color: var(--color-text-primary) !important;
}

/* Card actions styling */
:deep(.v-card-actions) {
  background-color: var(--color-surface-variant);
  border-top: 1px solid var(--color-border-subtle);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  :deep(.v-card) {
    margin-bottom: var(--spacing-md);
  }

  :deep(.v-card-title) {
    font-size: var(--font-size-body);
  }

  :deep(.v-card-text) {
    font-size: var(--font-size-small);
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-card),
  :deep(.v-btn) {
    transition: none;
    transform: none !important;
  }

  :deep(.v-card:hover),
  :deep(.v-btn:hover) {
    transform: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-card),
  :deep(.v-dialog .v-card) {
    border-width: 2px;
  }

  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }

  .border-left-4 {
    border-left-width: 6px;
  }
}

/* Focus management for keyboard navigation */
:deep(.v-card:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

:deep(.v-btn:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
