<template>
  <div>
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center">
          <h1 class="text-h4 mb-4">Dashboard</h1>
          <v-spacer></v-spacer>
          <v-switch
            v-model="simpleMode"
            label="Simple Mode"
            @change="toggleMode"
            hide-details
            class="mt-0 pt-0"
          ></v-switch>
        </div>
      </v-col>
    </v-row>

    <!-- Summary Cards -->
    <v-row>
      <!-- Total Miners Card -->
      <v-col cols="12" sm="6" md="3">
        <v-card class="mx-auto" color="primary" dark>
          <v-card-text>
            <div class="text-h4 text-center">{{ miners.length }}</div>
            <div class="text-subtitle-1 text-center">Total Miners</div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Online Miners Card -->
      <v-col cols="12" sm="6" md="3">
        <v-card class="mx-auto" color="success" dark>
          <v-card-text>
            <div class="text-h4 text-center">{{ onlineMiners.length }}</div>
            <div class="text-subtitle-1 text-center">Online Miners</div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Offline Miners Card -->
      <v-col cols="12" sm="6" md="3">
        <v-card class="mx-auto" color="error" dark>
          <v-card-text>
            <div class="text-h4 text-center">{{ offlineMiners.length }}</div>
            <div class="text-subtitle-1 text-center">Offline Miners</div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Total Hashrate Card -->
      <v-col cols="12" sm="6" md="3">
        <v-card class="mx-auto" color="info" dark>
          <v-card-text>
            <div class="text-h4 text-center">
              {{ formatHashrate(totalHashrate) }}
            </div>
            <div class="text-subtitle-1 text-center">Total Hashrate</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-4">
      <v-col cols="12">
        <QuickActions
          :default-network="discoveryNetwork"
          @scan-network="handleQuickScanNetwork"
          @add-miner="handleQuickAddMiner"
          @restart-all="handleQuickRestartAll"
          @view-analytics="handleQuickViewAnalytics"
          @miner-added="handleMinerAdded"
          @miner-error="handleMinerError"
        />
      </v-col>
    </v-row>

    <!-- Miners Status Table -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Miners Status
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="Search"
              single-line
              hide-details
            ></v-text-field>
          </v-card-title>

          <v-data-table
            :headers="headers"
            :items="miners"
            :search="search"
            :loading="loading"
            item-key="id"
            class="elevation-1"
          >
            <!-- Custom loading slot with Bitcoin spinner -->
            <template v-slot:loading>
              <div class="loading-container">
                <BitcoinLoadingSpinner
                  size="md"
                  loading-text="Loading miners..."
                  :show-text="true"
                  speed="normal"
                />
              </div>
            </template>

            <!-- Empty state slot -->
            <template v-slot:no-data>
              <div class="empty-state-container">
                <v-icon size="64" color="grey lighten-1">mdi-server-off</v-icon>
                <h3 class="mt-3 mb-2">No Miners Connected</h3>
                <p class="grey--text mb-4">
                  Get started by adding your first miner or running network discovery to find miners automatically.
                </p>
                <div class="empty-state-actions">
                  <v-btn color="primary" class="mr-2" @click="openAddMinerDialog">
                    <v-icon left>mdi-plus</v-icon>
                    Add Miner
                  </v-btn>
                  <v-btn color="secondary" @click="startDiscovery" :disabled="!discoveryFormValid">
                    <v-icon left>mdi-magnify</v-icon>
                    Scan Network
                  </v-btn>
                </div>
              </div>
            </template>

            <!-- Status Column -->
            <template v-slot:item.status="{ item }">
              <v-chip :color="getStatusColor(item.status)" dark small>
                {{ item.status }}
              </v-chip>
            </template>

            <!-- Hashrate Column -->
            <template v-slot:item.hashrate="{ item }">
              {{ formatHashrate(item.hashrate) }}
            </template>

            <!-- Temperature Column -->
            <template v-slot:item.temperature="{ item }">
              <v-progress-linear
                :value="item.temperature"
                :color="getTemperatureColor(item.temperature)"
                height="20"
              >
                <template v-slot:default="{ value }">
                  <strong>{{ formatTemperature(value) }}</strong>
                </template>
              </v-progress-linear>
            </template>

            <!-- Actions Column -->
            <template v-slot:item.actions="{ item }">
              <v-btn icon small :to="`/miners/${item.id}`" title="View Details">
                <v-icon>mdi-eye</v-icon>
              </v-btn>

              <v-btn
                icon
                small
                @click="restartMiner(item.id)"
                title="Restart Miner"
                :disabled="
                  item.status === 'offline' || item.status === 'restarting'
                "
              >
                <v-icon>mdi-restart</v-icon>
              </v-btn>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Network Discovery Section -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Network Discovery</v-card-title>
          <v-card-text>
            <v-form ref="discoveryForm" v-model="discoveryFormValid">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="discoveryNetwork"
                    label="Network Range"
                    hint="e.g., 192.168.1.0/24"
                    :rules="[
                      (v) => !!v || 'Network range is required',
                      (v) =>
                        /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/.test(v) ||
                        'Invalid network range format',
                    ]"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-btn
                    color="primary"
                    :loading="discoveryLoading"
                    :disabled="!discoveryFormValid || discoveryLoading"
                    @click="startDiscovery"
                  >
                    <v-icon left>mdi-magnify</v-icon>
                    Start Discovery
                  </v-btn>
                </v-col>
              </v-row>
            </v-form>

            <v-alert
              v-if="discoveryStatus && discoveryStatus.status === 'in_progress'"
              type="info"
              class="mt-4"
            >
              Discovery in progress...
            </v-alert>

            <v-alert
              v-if="discoveryStatus && discoveryStatus.status === 'completed'"
              type="success"
              class="mt-4"
            >
              Discovery completed. Found
              {{ discoveryStatus.miners_found }} miners.
            </v-alert>

            <v-alert
              v-if="discoveryStatus && discoveryStatus.status === 'error'"
              type="error"
              class="mt-4"
            >
              Discovery error: {{ discoveryStatus.error }}
            </v-alert>

            <!-- Discovery Results -->
            <v-expansion-panels
              v-if="
                discoveryStatus &&
                discoveryStatus.status === 'completed' &&
                discoveryStatus.result &&
                discoveryStatus.result.length > 0
              "
              class="mt-4"
            >
              <v-expansion-panel>
                <v-expansion-panel-title>
                  Discovery Results ({{ discoveryStatus.result.length }} miners
                  found)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-list>
                    <v-list-item
                      v-for="(miner, index) in discoveryStatus.result"
                      :key="index"
                    >
                      <v-list-item-title
                        >{{ miner.type }} at
                        {{ miner.ip_address }}</v-list-item-title
                      >
                      <v-list-item-subtitle>{{
                        miner.device_info.model || "Unknown Model"
                      }}</v-list-item-subtitle>
                      <template v-slot:append>
                        <v-btn
                          color="primary"
                          size="small"
                          @click="addDiscoveredMiner(miner)"
                        >
                          Add Miner
                        </v-btn>
                      </template>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

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
import { useGlobalSnackbar } from "../composables/useGlobalSnackbar";
import BitcoinLoadingSpinner from "../components/BitcoinLoadingSpinner.vue";
import AddMinerDialog from "../components/AddMinerDialog.vue";
import QuickActions from "../components/QuickActions.vue";
import { formatTemperature } from "../utils/formatters";

export default {
  name: "Dashboard",

  components: {
    BitcoinLoadingSpinner,
    AddMinerDialog,
    QuickActions,
  },

  setup() {
    const minersStore = useMinersStore();
    const settingsStore = useSettingsStore();
    const router = useRouter();
    const { showSuccess, showError, showWarning, showInfo } = useGlobalSnackbar();

    // Simple Mode toggle
    const simpleMode = ref((localStorage.getItem('uiMode') || 'advanced') === 'simple');

    // Table search
    const search = ref("");

    // Table headers
    const headers = [
      { title: "Name", key: "name" },
      { title: "Type", key: "type" },
      { title: "IP Address", key: "ip_address" },
      { title: "Status", key: "status" },
      { title: "Hashrate", key: "hashrate" },
      { title: "Temperature", key: "temperature" },
      { title: "Actions", key: "actions", sortable: false },
    ];

    // Discovery form
    const discoveryForm = ref(null);
    const discoveryFormValid = ref(false);
    const discoveryNetwork = ref("192.168.1.0/24");
    const discoveryLoading = ref(false);
    const discoveryStatus = ref(null);

    // Refresh interval
    let refreshInterval = null;

    // Computed properties from store
    const miners = computed(() => minersStore.miners);
    const onlineMiners = computed(() => minersStore.onlineMiners);
    const offlineMiners = computed(() => minersStore.offlineMiners);
    const totalHashrate = computed(() => minersStore.totalHashrate);
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

    const getStatusColor = (status) => {
      switch (status) {
        case "online":
          return "success";
        case "offline":
          return "error";
        case "restarting":
          return "warning";
        case "error":
          return "error";
        default:
          return "grey";
      }
    };

    const getTemperatureColor = (temp) => {
      if (!temp) return "grey";

      if (temp < 50) return "success";
      if (temp < 70) return "warning";
      return "error";
    };

    const restartMiner = async (minerId) => {
      try {
        await minersStore.restartMiner(minerId);
      } catch (error) {
        console.error(`Error restarting miner ${minerId}:`, error);
      }
    };

    const startDiscovery = async () => {
      discoveryLoading.value = true;

      try {
        const result = await minersStore.startDiscovery(discoveryNetwork.value);
        discoveryStatus.value = { status: "in_progress", ...result };
        
        // Poll for status updates
        const pollStatus = async () => {
          try {
            const status = await minersStore.getDiscoveryStatus();
            discoveryStatus.value = status;
            
            if (status.status === "in_progress") {
              setTimeout(pollStatus, 2000); // Poll every 2 seconds
            }
          } catch (error) {
            console.error("Error polling discovery status:", error);
            discoveryStatus.value = { status: "error", error: error.message };
          }
        };
        
        setTimeout(pollStatus, 2000);
      } catch (error) {
        console.error("Error starting discovery:", error);
        discoveryStatus.value = { status: "error", error: error.message };
      } finally {
        discoveryLoading.value = false;
      }
    };

    const pollDiscoveryStatus = async () => {
      try {
        // Mock polling - discovery status is already managed in startDiscovery
        console.log("Mock: Polling discovery status");
      } catch (error) {
        console.error("Error polling discovery status:", error);
      }
    };

    const addDiscoveredMiner = async (miner) => {
      try {
        const minerData = {
          type: miner.type,
          ip_address: miner.ip_address,
          port: miner.port,
          name: miner.name || `${miner.type} (${miner.ip_address})`,
        };
        await minersStore.addMiner(minerData);
      } catch (error) {
        console.error("Error adding discovered miner:", error);
      }
    };

    const addMinerDialog = ref(false);

    const openAddMinerDialog = () => {
      addMinerDialog.value = true;
    };

    const handleMinerAdded = (miner) => {
      console.log(`Miner "${miner.name}" added successfully`);
      showSuccess(`Miner "${miner.name}" added successfully`);
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
        console.error("Error initializing dashboard:", error);
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

      // Initialize discovery status
      discoveryStatus.value = { status: "idle", found_miners: [] };
    });

    onUnmounted(() => {
      // Clear refresh interval
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    });

    // Simple Mode toggle function
    const toggleMode = () => {
      // Update localStorage
      const newMode = simpleMode.value ? "simple" : "advanced";
      localStorage.setItem("uiMode", newMode);
      
      // Navigate to appropriate dashboard
      const targetRoute = simpleMode.value ? "/dashboard-simple" : "/";
      router.push(targetRoute);
    };

    // Quick Actions event handlers
    const handleQuickScanNetwork = async (network) => {
      // Use the existing startDiscovery method
      await startDiscovery();
    };

    const handleQuickAddMiner = () => {
      // Use the existing openAddMinerDialog method
      openAddMinerDialog();
    };

    const handleQuickRestartAll = async () => {
      // Restart all miners using the store
      try {
        await minersStore.restartAllMiners();
      } catch (error) {
        console.error("Error restarting all miners:", error);
      }
    };

    const handleQuickViewAnalytics = () => {
      // Navigate to analytics page
      router.push("/analytics");
    };

    return {
      // State
      search,
      headers,
      discoveryForm,
      discoveryFormValid,
      discoveryNetwork,
      discoveryLoading,
      discoveryStatus,
      simpleMode,
      addMinerDialog,

      // Computed
      miners,
      onlineMiners,
      offlineMiners,
      totalHashrate,
      loading,

      // Methods
      formatHashrate,
      formatTemperature,
      getStatusColor,
      getTemperatureColor,
      restartMiner,
      startDiscovery,
      addDiscoveredMiner,
      openAddMinerDialog,
      handleMinerAdded,
      handleMinerError,
      toggleMode,
      handleQuickScanNetwork,
      handleQuickAddMiner,
      handleQuickRestartAll,
      handleQuickViewAnalytics,
    };
  },
};
</script>

<style scoped>
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-xxl);
  min-height: 200px;
  background-color: var(--color-surface);
  border-radius: var(--radius-md);
}

.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  min-height: 300px;
  text-align: center;
}

.empty-state-container .v-icon {
  color: var(--color-text-disabled) !important;
  margin-bottom: var(--spacing-md);
}

.empty-state-container h3 {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

.empty-state-container p {
  color: var(--color-text-secondary) !important;
  max-width: 400px;
}

.empty-state-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  justify-content: center;
}

/* Enhanced card styling */
:deep(.v-card) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
  transition: all var(--transition-normal);
}

:deep(.v-card:hover) {
  box-shadow: var(--shadow-2);
}

:deep(.v-card-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
  background-color: var(--color-surface-secondary);
  border-bottom: 1px solid var(--color-border-subtle);
}

:deep(.v-card-text) {
  color: var(--color-text-primary) !important;
}

/* Status cards with enhanced styling */
:deep(.v-card[color="primary"]) {
  background-color: var(--color-primary) !important;
  border: 1px solid var(--color-primary-dark);
}

:deep(.v-card[color="success"]) {
  background-color: var(--color-success) !important;
  border: 1px solid var(--color-success-dark);
}

:deep(.v-card[color="error"]) {
  background-color: var(--color-error) !important;
  border: 1px solid var(--color-error-dark);
}

:deep(.v-card[color="info"]) {
  background-color: var(--color-info) !important;
  border: 1px solid var(--color-info-dark);
}

:deep(.v-card[color="grey"]) {
  background-color: var(--color-surface-secondary) !important;
  border: 1px solid var(--color-border);
}

/* Data table styling */
:deep(.v-data-table) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

:deep(.v-data-table .v-data-table__wrapper) {
  background-color: var(--color-surface) !important;
}

:deep(.v-data-table-header) {
  background-color: var(--color-surface-secondary) !important;
}

:deep(.v-data-table-header th) {
  background-color: var(--color-surface-secondary) !important;
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
  border-bottom: 1px solid var(--color-border-subtle);
}

:deep(.v-data-table tbody tr) {
  background-color: var(--color-surface) !important;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background-color var(--transition-fast);
}

:deep(.v-data-table tbody tr:nth-child(even)) {
  background-color: var(--color-surface-variant) !important;
}

:deep(.v-data-table tbody tr:hover) {
  background-color: var(--color-surface-hover) !important;
}

:deep(.v-data-table tbody td) {
  color: var(--color-text-primary) !important;
  border-bottom: 1px solid var(--color-border-subtle);
}

/* Form input styling */
:deep(.v-text-field .v-field) {
  background-color: var(--color-surface-secondary) !important;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

:deep(.v-text-field .v-field:hover) {
  border-color: var(--color-primary);
}

:deep(.v-text-field .v-field--focused) {
  border-color: var(--color-primary) !important;
  box-shadow: var(--shadow-focus);
}

:deep(.v-text-field input) {
  color: var(--color-text-primary) !important;
}

:deep(.v-text-field .v-field__input::placeholder) {
  color: var(--color-text-hint) !important;
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

:deep(.v-btn--variant-elevated) {
  box-shadow: var(--shadow-1);
}

:deep(.v-btn--variant-elevated:hover) {
  box-shadow: var(--shadow-2);
}

/* Chip styling for status indicators */
:deep(.v-chip) {
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
}

/* Progress bar styling */
:deep(.v-progress-linear) {
  border-radius: var(--radius-sm);
  background-color: var(--color-surface-secondary) !important;
}

/* Alert styling */
:deep(.v-alert) {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

:deep(.v-alert.v-alert--type-info) {
  background-color: rgba(var(--color-info), 0.1) !important;
  border-color: var(--color-info);
  color: var(--color-text-primary) !important;
}

:deep(.v-alert.v-alert--type-success) {
  background-color: rgba(var(--color-success), 0.1) !important;
  border-color: var(--color-success);
  color: var(--color-text-primary) !important;
}

:deep(.v-alert.v-alert--type-error) {
  background-color: rgba(var(--color-error), 0.1) !important;
  border-color: var(--color-error);
  color: var(--color-text-primary) !important;
}

/* Expansion panels styling */
:deep(.v-expansion-panels) {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

:deep(.v-expansion-panel) {
  background-color: var(--color-surface) !important;
}

:deep(.v-expansion-panel-title) {
  background-color: var(--color-surface-secondary) !important;
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.v-expansion-panel-text) {
  background-color: var(--color-surface) !important;
  color: var(--color-text-primary) !important;
}

/* List styling */
:deep(.v-list) {
  background-color: var(--color-surface) !important;
}

:deep(.v-list-item) {
  color: var(--color-text-primary) !important;
}

:deep(.v-list-item-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.v-list-item-subtitle) {
  color: var(--color-text-secondary) !important;
}

/* Tooltip styling */
:deep(.v-tooltip .v-overlay__content) {
  background-color: var(--color-surface-elevated) !important;
  color: var(--color-text-primary) !important;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-2);
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-card),
  :deep(.v-btn),
  :deep(.v-data-table tbody tr) {
    transition: none;
  }

  :deep(.v-btn:hover) {
    transform: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-card),
  :deep(.v-data-table),
  :deep(.v-alert),
  :deep(.v-expansion-panels) {
    border-width: 2px;
  }

  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }
}
</style>
