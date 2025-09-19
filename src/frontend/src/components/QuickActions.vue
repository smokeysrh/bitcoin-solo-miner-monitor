<template>
  <v-card class="mb-6">
    <v-card-title class="headline">
      Quick Actions
      <InfoBubble
        tooltip-text="Common actions you can perform on your miners"
        dialog-title="Quick Actions Information"
        dialog-content="<p>Common tasks you can perform:</p><ul><li><strong>Scan Network:</strong> Search your network for new miners automatically</li><li><strong>Add Miner:</strong> Manually add a new miner to monitor and manage</li><li><strong>Restart All:</strong> Restart all miners simultaneously (use with caution)</li><li><strong>Analytics:</strong> View detailed performance charts and historical data</li></ul>"
        aria-label="quick actions section"
        class="ml-2"
      />
    </v-card-title>
    <v-card-text>
      <v-row>
        <v-col cols="6" sm="3">
          <v-btn
            block
            color="primary"
            class="action-button"
            @click="handleScanNetwork"
            :loading="scanning"
          >
            <v-icon left>mdi-refresh</v-icon>
            Scan Network
          </v-btn>
        </v-col>
        <v-col cols="6" sm="3">
          <v-btn
            block
            color="success"
            class="action-button"
            @click="handleAddMiner"
          >
            <v-icon left>mdi-plus</v-icon>
            Add Miner
          </v-btn>
        </v-col>
        <v-col cols="6" sm="3">
          <v-btn
            block
            color="warning"
            class="action-button"
            @click="handleRestartAll"
            :disabled="miners.length === 0"
          >
            <v-icon left>mdi-restart</v-icon>
            Restart All
          </v-btn>
        </v-col>
        <v-col cols="6" sm="3">
          <v-btn
            block
            color="info"
            class="action-button"
            @click="handleViewAnalytics"
          >
            <v-icon left>mdi-chart-line</v-icon>
            Analytics
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>

    <!-- Add Miner Dialog -->
    <AddMinerDialog
      v-model="addMinerDialog"
      @miner-added="handleMinerAdded"
      @error="handleMinerError"
    />
  </v-card>
</template>

<script>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useMinersStore } from "../stores/miners";
import InfoBubble from "./InfoBubble.vue";
import AddMinerDialog from "./AddMinerDialog.vue";

export default {
  name: "QuickActions",
  
  components: {
    InfoBubble,
    AddMinerDialog,
  },

  props: {
    // Configuration props for different dashboard contexts
    showInfoBubble: {
      type: Boolean,
      default: true,
    },
    defaultNetwork: {
      type: String,
      default: "192.168.1.0/24",
    },
    // Allow parent to override button configurations
    buttonConfig: {
      type: Object,
      default: () => ({
        scanNetwork: { show: true, color: "primary" },
        addMiner: { show: true, color: "success" },
        restartAll: { show: true, color: "warning" },
        analytics: { show: true, color: "info" },
      }),
    },
  },

  emits: [
    'scan-network',
    'add-miner',
    'restart-all',
    'view-analytics',
    'miner-added',
    'miner-error'
  ],

  setup(props, { emit }) {
    const router = useRouter();
    const minersStore = useMinersStore();

    // Reactive data
    const scanning = ref(false);
    const addMinerDialog = ref(false);

    // Computed properties
    const miners = computed(() => minersStore.miners);

    // Methods
    const handleScanNetwork = async () => {
      scanning.value = true;
      try {
        // Emit event to parent component for handling
        emit('scan-network', props.defaultNetwork);
        
        // Also handle directly if parent doesn't override
        await minersStore.startDiscovery(props.defaultNetwork);
        console.log("Network scan initiated");
      } catch (error) {
        console.error("Error scanning network:", error);
      } finally {
        scanning.value = false;
      }
    };

    const handleAddMiner = () => {
      addMinerDialog.value = true;
      emit('add-miner');
    };

    const handleRestartAll = async () => {
      try {
        emit('restart-all');
        await minersStore.restartAllMiners();
      } catch (error) {
        console.error("Error restarting all miners:", error);
      }
    };

    const handleViewAnalytics = () => {
      emit('view-analytics');
      router.push("/analytics");
    };

    const handleMinerAdded = (miner) => {
      console.log(`Miner "${miner.name}" added successfully`);
      emit('miner-added', miner);
    };

    const handleMinerError = (error) => {
      console.error('Error adding miner:', error);
      emit('miner-error', error);
    };

    return {
      // Refs
      scanning,
      addMinerDialog,

      // Computed
      miners,

      // Methods
      handleScanNetwork,
      handleAddMiner,
      handleRestartAll,
      handleViewAnalytics,
      handleMinerAdded,
      handleMinerError,
    };
  },
};
</script>

<style scoped>
.action-button {
  height: var(--button-height-large, 48px);
  font-weight: var(--font-weight-medium, 500);
  transition: all var(--transition-fast, 0.2s ease);
}

.action-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-2, 0 4px 8px rgba(0, 0, 0, 0.12));
}

/* Enhanced card styling */
:deep(.v-card) {
  background-color: var(--color-surface, #ffffff) !important;
  border: 1px solid var(--color-border-subtle, #e0e0e0);
  box-shadow: var(--shadow-1, 0 2px 4px rgba(0, 0, 0, 0.1));
  transition: all var(--transition-normal, 0.3s ease);
}

:deep(.v-card:hover) {
  box-shadow: var(--shadow-2, 0 4px 8px rgba(0, 0, 0, 0.12));
}

:deep(.v-card-title) {
  color: var(--color-text-primary, #000000) !important;
  font-weight: var(--font-weight-semibold, 600);
}

:deep(.v-card-text) {
  color: var(--color-text-primary, #000000) !important;
}

/* Button enhancements */
:deep(.v-btn) {
  font-weight: var(--font-weight-medium, 500);
  transition: all var(--transition-fast, 0.2s ease);
  border-radius: var(--radius-md, 8px);
}

:deep(.v-btn:hover) {
  transform: translateY(-1px);
}

:deep(.v-btn--variant-elevated) {
  box-shadow: var(--shadow-1, 0 2px 4px rgba(0, 0, 0, 0.1));
}

:deep(.v-btn--variant-elevated:hover) {
  box-shadow: var(--shadow-2, 0 4px 8px rgba(0, 0, 0, 0.12));
}

/* Icon styling */
:deep(.v-icon) {
  color: inherit;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .action-button {
    height: var(--button-height, 40px);
    font-size: var(--font-size-small, 14px);
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .action-button,
  :deep(.v-card),
  :deep(.v-btn) {
    transition: none;
    transform: none !important;
  }

  .action-button:hover,
  :deep(.v-btn:hover) {
    transform: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-card) {
    border-width: 2px;
    border-color: var(--color-text-primary, #000000);
  }
}
</style>