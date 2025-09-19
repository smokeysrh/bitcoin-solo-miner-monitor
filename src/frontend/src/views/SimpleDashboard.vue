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

    <!-- Status Overview -->
    <v-card class="mb-6">
      <v-card-title class="headline">
        Mining Status
        <InfoBubble
          tooltip-text="Overall status of your mining operation"
          dialog-title="Mining Status Information"
          dialog-content="<p>This section shows the current status of your mining operation:</p><ul><li><strong>Total Miners:</strong> Number of miners configured in the system</li><li><strong>Online Miners:</strong> Number of miners currently online and mining</li><li><strong>Offline Miners:</strong> Number of miners that are offline or experiencing issues</li><li><strong>Total Hashrate:</strong> Combined mining power of all your miners</li></ul>"
          aria-label="mining status section"
          class="ml-2"
        />
      </v-card-title>
      <v-card-text>
        <v-row>
          <!-- Total Miners Card -->
          <v-col cols="12" sm="6" md="3">
            <v-card
              class="mx-auto status-card"
              :color="miners.length > 0 ? 'primary' : 'grey'"
              dark
            >
              <v-card-text class="text-center">
                <div class="text-h3">{{ miners.length }}</div>
                <div class="text-subtitle-1">Total Miners</div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Online Miners Card -->
          <v-col cols="12" sm="6" md="3">
            <v-card class="mx-auto status-card" color="success" dark>
              <v-card-text class="text-center">
                <div class="text-h3">{{ onlineMiners.length }}</div>
                <div class="text-subtitle-1">Online Miners</div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Offline Miners Card -->
          <v-col cols="12" sm="6" md="3">
            <v-card
              class="mx-auto status-card"
              :color="offlineMiners.length > 0 ? 'error' : 'grey'"
              dark
            >
              <v-card-text class="text-center">
                <div class="text-h3">{{ offlineMiners.length }}</div>
                <div class="text-subtitle-1">Offline Miners</div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Total Hashrate Card -->
          <v-col cols="12" sm="6" md="3">
            <v-card class="mx-auto status-card" color="info" dark>
              <v-card-text class="text-center">
                <div class="text-h3">{{ formatHashrate(totalHashrate) }}</div>
                <div class="text-subtitle-1">Total Hashrate</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Quick Actions -->
    <QuickActions
      default-network="192.168.1.0/24"
      @scan-network="handleQuickScanNetwork"
      @add-miner="handleQuickAddMiner"
      @restart-all="handleQuickRestartAll"
      @view-analytics="handleQuickViewAnalytics"
      @miner-added="handleMinerAdded"
      @miner-error="handleMinerError"
    />

    <!-- Miners Overview -->
    <v-card>
      <v-card-title class="headline">
        Miners Overview
        <InfoBubble
          tooltip-text="Status of all your mining devices"
          dialog-title="Miners Overview Information"
          dialog-content="<p>The miners table shows all your mining devices with their current status:</p><ul><li><strong>Search:</strong> Use the search box to find specific miners by name or IP</li><li><strong>Status:</strong> Shows if each miner is online, offline, or has warnings</li><li><strong>Actions:</strong> View detailed information or restart individual miners</li><li><strong>Performance:</strong> Monitor hashrate and temperature for each device</li></ul><p>Click on any miner row to view more detailed information.</p>"
          aria-label="miners overview section"
          class="ml-2"
        />
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
          class="ml-2"
        ></v-text-field>
      </v-card-title>
      <v-data-table
        :headers="headers"
        :items="miners"
        :search="search"
        :loading="loading"
        :items-per-page="5"
        class="elevation-1"
      >
        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" dark small>
            {{ item.status }}
          </v-chip>
        </template>
        <template v-slot:item.hashrate="{ item }">
          {{ formatHashrate(item.hashrate) }}
        </template>
        <template v-slot:item.temperature="{ item }">
          <v-chip :color="getTemperatureColor(item.temperature)" dark small>
            {{ formatTemperature(item.temperature) }}
          </v-chip>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                icon
                small
                v-bind="attrs"
                v-on="on"
                @click="viewMiner(item)"
              >
                <v-icon small>mdi-eye</v-icon>
              </v-btn>
            </template>
            <span>View Details</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                icon
                small
                v-bind="attrs"
                v-on="on"
                @click="restartMiner(item)"
              >
                <v-icon small>mdi-restart</v-icon>
              </v-btn>
            </template>
            <span>Restart Miner</span>
          </v-tooltip>
        </template>
      </v-data-table>
    </v-card>



    <!-- Help Overlay -->
    <v-dialog v-model="showHelp" max-width="700px">
      <v-card>
        <v-card-title class="headline">Dashboard Help</v-card-title>
        <v-card-text>
          <h3>Welcome to Simple Mode!</h3>
          <p>
            This simplified dashboard provides an easy way to monitor and manage
            your Bitcoin miners.
          </p>

          <h4 class="mt-4">Mining Status</h4>
          <p>The top section shows your overall mining status:</p>
          <ul>
            <li>
              <strong>Total Miners:</strong> Number of miners configured in the
              system
            </li>
            <li>
              <strong>Online Miners:</strong> Number of miners currently online
              and mining
            </li>
            <li>
              <strong>Offline Miners:</strong> Number of miners that are offline
              or experiencing issues
            </li>
            <li>
              <strong>Total Hashrate:</strong> Combined mining power of all your
              miners
            </li>
          </ul>

          <h4 class="mt-4">Quick Actions</h4>
          <p>Common tasks you can perform:</p>
          <ul>
            <li>
              <strong>Scan Network:</strong> Search your network for new miners
            </li>
            <li>
              <strong>Add Miner:</strong> Manually add a new miner to monitor
            </li>
            <li>
              <strong>Restart All:</strong> Restart all miners (use with
              caution)
            </li>
            <li>
              <strong>Analytics:</strong> View detailed performance charts
            </li>
          </ul>

          <h4 class="mt-4">Miners Overview</h4>
          <p>
            The table shows all your miners with their current status. You can:
          </p>
          <ul>
            <li>Search for specific miners</li>
            <li>View detailed information for each miner</li>
            <li>Restart individual miners</li>
          </ul>

          <p class="mt-4">
            Need more advanced features? Toggle off "Simple Mode" in the top
            right corner.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="showHelp = false">Got it!</v-btn>
          <v-checkbox
            v-model="dontShowAgain"
            label="Don't show again"
          ></v-checkbox>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useMinersStore } from "../stores/miners";
import InfoBubble from "../components/InfoBubble.vue";
import AddMinerDialog from "../components/AddMinerDialog.vue";
import QuickActions from "../components/QuickActions.vue";
import { formatTemperature } from "../utils/formatters";

export default {
  name: "SimpleDashboard",
  components: {
    InfoBubble,
    AddMinerDialog,
    QuickActions,
  },
  setup() {
    const router = useRouter();
    const minersStore = useMinersStore();

    // Reactive data
    const simpleMode = ref(true);
    const search = ref("");
    const loading = ref(false);
    const scanning = ref(false);
    const showHelp = ref(false);
    const dontShowAgain = ref(false);

    const headers = ref([
      { text: "Name", value: "name" },
      { text: "Type", value: "type" },
      { text: "Status", value: "status" },
      { text: "Hashrate", value: "hashrate" },
      { text: "Temperature", value: "temperature" },
      { text: "Actions", value: "actions", sortable: false },
    ]);

    // Computed properties
    const miners = computed(() => minersStore.miners);
    const onlineMiners = computed(() => minersStore.onlineMiners);
    const offlineMiners = computed(() => minersStore.offlineMiners);
    const totalHashrate = computed(() => minersStore.totalHashrate);

    // Methods
    const toggleMode = () => {
      // Update localStorage
      const newMode = simpleMode.value ? "simple" : "advanced";
      localStorage.setItem("uiMode", newMode);
      
      // Navigate to appropriate dashboard
      const targetRoute = simpleMode.value ? "/dashboard-simple" : "/";
      router.push(targetRoute);
    };

    const formatHashrate = (hashrate) => {
      if (!hashrate) return "0 H/s";

      const units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s"];
      let unitIndex = 0;
      let value = hashrate;

      while (value >= 1000 && unitIndex < units.length - 1) {
        value /= 1000;
        unitIndex++;
      }

      return `${value.toFixed(2)} ${units[unitIndex]}`;
    };

    const getStatusColor = (status) => {
      switch (status.toLowerCase()) {
        case "online":
          return "success";
        case "offline":
          return "error";
        case "warning":
          return "warning";
        default:
          return "grey";
      }
    };

    const getTemperatureColor = (temp) => {
      if (temp < 60) return "success";
      if (temp < 75) return "warning";
      return "error";
    };

    const viewMiner = (miner) => {
      router.push(`/miners/${miner.id}`);
    };

    const addMiner = () => {
      // This method is now handled by QuickActions component
      console.log("Add miner triggered from SimpleDashboard");
    };

    const handleMinerAdded = (miner) => {
      console.log(`Miner "${miner.name}" added successfully`);
      // Optionally show a success message or refresh data
    };

    const handleMinerError = (error) => {
      console.error('Error adding miner:', error);
      // Optionally show an error message
    };

    const restartMiner = async (miner) => {
      try {
        await minersStore.restartMiner(miner.id);
      } catch (error) {
        console.error("Error restarting miner:", error);
      }
    };

    const restartAll = async () => {
      try {
        await minersStore.restartAllMiners();
      } catch (error) {
        console.error("Error restarting all miners:", error);
      }
    };

    const scanNetwork = async () => {
      scanning.value = true;
      try {
        // Use default network range for simple dashboard
        const defaultNetwork = "192.168.1.0/24";
        await minersStore.startDiscovery(defaultNetwork);
        
        // Optionally show a success message or update UI
        console.log("Network scan initiated");
      } catch (error) {
        console.error("Error scanning network:", error);
      } finally {
        scanning.value = false;
      }
    };

    const viewAnalytics = () => {
      router.push("/analytics");
    };

    // Quick Actions event handlers
    const handleQuickScanNetwork = async (network) => {
      // Use the existing scanNetwork method
      await scanNetwork();
    };

    const handleQuickAddMiner = () => {
      // Use the existing addMiner method
      addMiner();
    };

    const handleQuickRestartAll = async () => {
      // Use the existing restartAll method
      await restartAll();
    };

    const handleQuickViewAnalytics = () => {
      // Use the existing viewAnalytics method
      viewAnalytics();
    };

    // Watchers
    watch(showHelp, (val) => {
      if (!val && dontShowAgain.value) {
        localStorage.setItem("simpleDashboardHelpShown", "true");
      }
    });

    // Lifecycle
    onMounted(() => {
      minersStore.fetchMiners();

      // Show help dialog on first visit
      const helpShown = localStorage.getItem("simpleDashboardHelpShown");
      if (!helpShown) {
        showHelp.value = true;
      }
    });

    return {
      // Refs
      simpleMode,
      search,
      loading,
      scanning,
      showHelp,
      dontShowAgain,
      headers,

      // Computed
      miners,
      onlineMiners,
      offlineMiners,
      totalHashrate,

      // Methods
      toggleMode,
      formatHashrate,
      formatTemperature,
      getStatusColor,
      getTemperatureColor,
      viewMiner,
      addMiner,
      handleMinerAdded,
      handleMinerError,
      restartMiner,
      restartAll,
      scanNetwork,
      viewAnalytics,
      handleQuickScanNetwork,
      handleQuickAddMiner,
      handleQuickRestartAll,
      handleQuickViewAnalytics,
    };
  },
};
</script>

<style scoped>
/* Use CSS custom properties from the theme system */
.status-card {
  transition: all var(--transition-normal);
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-3);
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
}

:deep(.v-card-text) {
  color: var(--color-text-primary) !important;
}

/* Data table styling */
:deep(.v-data-table) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
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

/* Dialog styling */
:deep(.v-dialog .v-card) {
  background-color: var(--color-surface-elevated) !important;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-4);
}

:deep(.v-dialog .v-card-title) {
  background-color: var(--color-surface-secondary);
  border-bottom: 1px solid var(--color-border-subtle);
  color: var(--color-text-primary) !important;
}

/* Switch styling */
:deep(.v-switch) {
  color: var(--color-text-primary) !important;
}

:deep(.v-switch .v-selection-control__wrapper) {
  color: var(--color-text-primary) !important;
}

/* Chip styling for status indicators */
:deep(.v-chip) {
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
}

/* Tooltip styling */
:deep(.v-tooltip .v-overlay__content) {
  background-color: var(--color-surface-elevated) !important;
  color: var(--color-text-primary) !important;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-2);
}

/* Button enhancements */
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

/* Icon styling */
:deep(.v-icon) {
  color: inherit;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .status-card {
    margin-bottom: var(--spacing-md);
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .status-card,
  :deep(.v-card),
  :deep(.v-btn) {
    transition: none;
    transform: none !important;
  }

  .status-card:hover,
  :deep(.v-btn:hover) {
    transform: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .status-card,
  :deep(.v-card) {
    border-width: 2px;
    border-color: var(--color-text-primary);
  }

  :deep(.v-data-table) {
    border-width: 2px;
  }
}
</style>
