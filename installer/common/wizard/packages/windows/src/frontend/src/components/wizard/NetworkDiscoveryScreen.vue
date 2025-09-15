<template>
  <div class="discovery-screen">
    <div class="discovery-content">
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center discovery-header">
            <div class="mb-4">
              <BitcoinLogo 
                size="md" 
                class="discovery-logo"
                aria-label="Bitcoin Network Discovery"
              />
            </div>
            <h1 class="text-h4 mb-4 discovery-title">Network Discovery</h1>
            <p class="text-subtitle-1 mb-6 discovery-subtitle">
              Let's find <span class="text-primary">Bitcoin</span> miners on
              your network. You can scan automatically or add miners manually.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12">
            <v-tabs v-model="activeTab" grow class="discovery-tabs">
              <v-tab class="discovery-tab">
                <v-icon start>mdi-magnify</v-icon>
                Auto Scan
              </v-tab>
              <v-tab class="discovery-tab">
                <v-icon start>mdi-plus-circle</v-icon>
                Manual Entry
              </v-tab>
              <v-tab class="discovery-tab">
                <v-icon start>mdi-format-list-bulleted</v-icon>
                Results
              </v-tab>
            </v-tabs>

            <v-window v-model="activeTab">
              <!-- Auto Scan Tab -->
              <v-window-item>
                <v-card flat>
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" md="6">
                        <h3 class="text-h6 mb-2">IP Range</h3>
                        <p class="text-caption mb-4">
                          Specify the IP range to scan for miners
                        </p>

                        <v-text-field
                          v-model="ipRange.start"
                          label="Start IP"
                          hint="e.g. 192.168.1.1"
                          persistent-hint
                          variant="outlined"
                          :rules="[
                            (v) => !!v || 'Start IP is required',
                            ipAddressRule,
                          ]"
                        ></v-text-field>

                        <v-text-field
                          v-model="ipRange.end"
                          label="End IP"
                          hint="e.g. 192.168.1.254"
                          persistent-hint
                          variant="outlined"
                          class="mt-4"
                          :rules="[
                            (v) => !!v || 'End IP is required',
                            ipAddressRule,
                          ]"
                        ></v-text-field>
                      </v-col>

                      <v-col cols="12" md="6">
                        <h3 class="text-h6 mb-2">Scan Options</h3>
                        <p class="text-caption mb-4">
                          Configure how the scan should be performed
                        </p>

                        <v-select
                          v-model="scanOptions.minerTypes"
                          :items="minerTypeOptions"
                          label="Miner Types"
                          multiple
                          chips
                          variant="outlined"
                          hint="Select the types of miners to look for"
                          persistent-hint
                          attach
                          :menu-props="{
                            closeOnContentClick: false,
                            maxHeight: 300,
                            transition: 'slide-y-transition',
                          }"
                        ></v-select>

                        <v-slider
                          v-model="scanOptions.timeout"
                          label="Scan Timeout (seconds)"
                          min="5"
                          max="60"
                          thumb-label
                          class="mt-6"
                        ></v-slider>
                      </v-col>
                    </v-row>

                    <v-row>
                      <v-col cols="12" class="text-center">
                        <v-btn
                          color="primary"
                          size="large"
                          :loading="scanning"
                          :disabled="!ipRangeValid"
                          @click="startScan"
                        >
                          <v-icon start>mdi-radar</v-icon>
                          Start Network Scan
                        </v-btn>
                      </v-col>
                    </v-row>

                    <v-row v-if="scanning">
                      <v-col cols="12">
                        <v-progress-linear
                          :value="scanProgress"
                          color="primary"
                          height="25"
                          striped
                        >
                          <template v-slot:default="{ value }">
                            <strong>{{ Math.ceil(value) }}%</strong>
                          </template>
                        </v-progress-linear>
                        <p class="text-center mt-2">
                          Scanning IP {{ currentIp }}...
                        </p>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Manual Entry Tab -->
              <v-window-item>
                <v-card flat>
                  <v-card-text>
                    <v-form ref="manualForm" v-model="manualFormValid">
                      <v-row>
                        <v-col cols="12" md="6">
                          <v-text-field
                            v-model="manualMiner.name"
                            label="Miner Name"
                            variant="outlined"
                            :rules="[(v) => !!v || 'Name is required']"
                          ></v-text-field>
                        </v-col>

                        <v-col cols="12" md="6">
                          <v-text-field
                            v-model="manualMiner.ip"
                            label="IP Address"
                            variant="outlined"
                            :rules="[
                              (v) => !!v || 'IP Address is required',
                              ipAddressRule,
                            ]"
                          ></v-text-field>
                        </v-col>
                      </v-row>

                      <v-row>
                        <v-col cols="12" md="6">
                          <v-select
                            v-model="manualMiner.type"
                            :items="minerTypeOptions"
                            label="Miner Type"
                            variant="outlined"
                            :rules="[(v) => !!v || 'Miner type is required']"
                            attach
                            :menu-props="{
                              closeOnContentClick: true,
                              maxHeight: 300,
                              transition: 'slide-y-transition',
                            }"
                          ></v-select>
                        </v-col>

                        <v-col cols="12" md="6">
                          <v-text-field
                            v-model="manualMiner.port"
                            label="Port (Optional)"
                            type="number"
                            variant="outlined"
                            hint="Leave empty for default port"
                            persistent-hint
                          ></v-text-field>
                        </v-col>
                      </v-row>

                      <v-row>
                        <v-col cols="12" class="text-center">
                          <v-btn
                            color="primary"
                            @click="addManualMiner"
                            :disabled="!manualFormValid"
                          >
                            <v-icon start>mdi-plus</v-icon>
                            Add Miner
                          </v-btn>
                        </v-col>
                      </v-row>
                    </v-form>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Results Tab -->
              <v-window-item>
                <v-card flat>
                  <v-card-text>
                    <v-data-table
                      :headers="minerHeaders"
                      :items="discoveredMiners"
                      :loading="scanning"
                      :no-data-text="noMinersText"
                      class="elevation-1"
                    >
                      <template v-slot:item.status="{ item }">
                        <v-chip
                          :color="
                            item.status === 'online' ? 'success' : 'error'
                          "
                          size="small"
                        >
                          {{ item.status }}
                        </v-chip>
                      </template>

                      <template v-slot:item.actions="{ item }">
                        <v-btn
                          icon="mdi-delete"
                          size="small"
                          @click="removeMiner(item)"
                          color="error"
                        >
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-window-item>
            </v-window>
          </v-col>
        </v-row>

        <v-row v-if="experienceLevel === 'beginner'" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" variant="outlined">
              <h3 class="text-h6">What is network discovery?</h3>
              <p>
                Network discovery helps find Bitcoin miners connected to your
                local network. The scan will look for devices running mining
                software on your network and automatically add them to your
                monitoring dashboard.
              </p>
              <p class="mb-0">
                If you know the exact IP address of your miners, you can also
                add them manually.
              </p>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </div>


  </div>
</template>

<script>
import BitcoinLogo from '../BitcoinLogo.vue'

export default {
  name: "NetworkDiscoveryScreen",
  
  components: {
    BitcoinLogo
  },

  props: {
    experienceLevel: {
      type: String,
      default: "beginner",
    },
  },

  data() {
    return {
      activeTab: 0,
      scanning: false,
      scanProgress: 0,
      currentIp: "",
      skipDiscovery: false,

      ipRange: {
        start: "192.168.1.1",
        end: "192.168.1.254",
      },

      scanOptions: {
        minerTypes: ["Magic Miner", "Avalon Nano", "Bitaxe"],
        timeout: 15,
      },

      manualFormValid: false,
      manualMiner: {
        name: "",
        ip: "",
        type: "",
        port: "",
      },

      discoveredMiners: [],

      minerTypeOptions: ["Magic Miner", "Avalon Nano", "Bitaxe"],

      minerHeaders: [
        { title: "Name", key: "name" },
        { title: "IP Address", key: "ip" },
        { title: "Type", key: "type" },
        { title: "Status", key: "status" },
        { title: "Actions", key: "actions", sortable: false },
      ],
    };
  },

  computed: {
    ipRangeValid() {
      return (
        this.ipAddressRule(this.ipRange.start) === true &&
        this.ipAddressRule(this.ipRange.end) === true
      );
    },

    noMinersText() {
      return this.scanning ? "Scanning network..." : "No miners discovered yet";
    },
  },

  methods: {
    ipAddressRule(value) {
      const pattern =
        /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      return pattern.test(value) || "Invalid IP address format";
    },

    startScan() {
      if (!this.ipRangeValid) return;

      this.scanning = true;
      this.scanProgress = 0;
      this.currentIp = this.ipRange.start;

      // Simulate network scanning
      this.simulateScan();
    },

    simulateScan() {
      // This is a simulation of a network scan
      // In a real implementation, this would be replaced with actual network scanning logic

      const totalIps = this.calculateTotalIps();
      let scannedIps = 0;

      // Generate some random miners for demonstration
      const potentialMiners = [
        {
          name: "MagicMiner-01",
          type: "Magic Miner",
          ip: "10.0.0.100",
          status: "online",
        },
        {
          name: "AvalonNano-02",
          type: "Avalon Nano",
          ip: "10.0.0.101",
          status: "online",
        },
        {
          name: "Bitaxe-03",
          type: "Bitaxe",
          ip: "10.0.0.102",
          status: "offline",
        },
      ];

      const scanInterval = setInterval(() => {
        scannedIps++;
        this.scanProgress = (scannedIps / totalIps) * 100;

        // Update current IP being scanned (simplified)
        const ipParts = this.currentIp.split(".");
        let lastOctet = parseInt(ipParts[3]);
        lastOctet++;
        this.currentIp = `${ipParts[0]}.${ipParts[1]}.${ipParts[2]}.${lastOctet}`;

        // Randomly discover miners
        if (scannedIps === Math.floor(totalIps * 0.3)) {
          this.discoveredMiners.push(potentialMiners[0]);
        } else if (scannedIps === Math.floor(totalIps * 0.6)) {
          this.discoveredMiners.push(potentialMiners[1]);
        } else if (scannedIps === Math.floor(totalIps * 0.9)) {
          this.discoveredMiners.push(potentialMiners[2]);
        }

        if (scannedIps >= totalIps) {
          clearInterval(scanInterval);
          this.scanning = false;
          this.activeTab = 2; // Switch to results tab
        }
      }, 100);
    },

    calculateTotalIps() {
      // Simple calculation of IP range size
      const start = this.ipRange.start.split(".")[3];
      const end = this.ipRange.end.split(".")[3];
      return end - start + 1;
    },

    addManualMiner() {
      if (!this.$refs.manualForm.validate()) return;

      // Add the manually entered miner to the discovered miners list
      this.discoveredMiners.push({
        name: this.manualMiner.name,
        ip: this.manualMiner.ip,
        type: this.manualMiner.type,
        port: this.manualMiner.port || null,
        status: "unknown", // Status is unknown until we connect to it
      });

      // Reset the form
      this.manualMiner = {
        name: "",
        ip: "",
        type: "",
        port: "",
      };

      // Switch to results tab
      this.activeTab = 2;
    },

    removeMiner(miner) {
      const index = this.discoveredMiners.findIndex((m) => m.ip === miner.ip);
      if (index !== -1) {
        this.discoveredMiners.splice(index, 1);
      }
    },

    emitMinersFound() {
      // Emit the discovered miners to the parent component
      this.$emit("miners-found", this.discoveredMiners);
    },
  },
};
</script>

<style scoped>
/* Import shared wizard styles for standardized info bubbles */
@import "./shared-wizard-styles.css";

/* Discovery screen layout - Fixed for proper scrolling */
.discovery-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  /* Ensure the screen takes full height of step-content */
  min-height: 100%;
}

.discovery-content {
  flex: 1;
  /* Remove overflow-y: auto to prevent nested scrolling - parent .step-content handles scrolling */
  padding: var(--spacing-lg);
  min-height: 0;
  /* Allow content to expand naturally */
  overflow: visible;
}

.discovery-footer {
  flex-shrink: 0;
  padding: 16px 24px;
  background: rgb(var(--v-theme-surface));
  /* Add border and shadow to make footer more prominent */
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  /* Ensure footer stays at bottom with static positioning */
  margin-top: auto;
  position: static; /* Ensure static positioning, not fixed */
}

/* Button styling */
.discovery-btn {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 120px;
}

.discovery-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* Ensure proper scrolling and container sizing */
.discovery-content :deep(.v-container) {
  padding: 0; /* Remove padding since .discovery-content now handles it */
  max-width: none;
  /* Ensure container doesn't constrain height */
  height: auto;
}

/* Discovery screen header styling */
.discovery-header {
  padding: 24px 0;
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.05) 0%,
    transparent 100%
  );
  border-radius: 16px;
  margin-bottom: 32px;
}

.discovery-logo {
  margin: 0 auto;
  filter: drop-shadow(0 2px 6px rgba(247, 147, 26, 0.3));
  animation: logoGlow 2s ease-in-out infinite alternate;
}

@keyframes logoGlow {
  0% {
    filter: drop-shadow(0 2px 6px rgba(247, 147, 26, 0.3));
  }
  100% {
    filter: drop-shadow(0 4px 12px rgba(247, 147, 26, 0.5));
  }
}

.discovery-title {
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}

.discovery-subtitle {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 1.1rem;
  line-height: 1.6;
}

/* Enhanced tab styling */
.discovery-tabs {
  border-radius: 12px;
  overflow: hidden;
  background: rgb(var(--v-theme-surface-variant));
  margin-bottom: 24px;
}

.discovery-tab {
  min-width: 140px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.discovery-tab:hover {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.discovery-tab.v-tab--selected {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

/* Enhanced form styling */
:deep(.v-text-field) {
  margin-bottom: 16px;
}

:deep(.v-text-field .v-field) {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 12px;
  transition: all 0.3s ease;
}

:deep(.v-text-field .v-field:hover) {
  background: rgb(var(--v-theme-surface-bright));
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

:deep(.v-text-field .v-field--focused) {
  background: rgb(var(--v-theme-surface-bright));
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.3);
}

:deep(.v-select .v-field) {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 12px;
  transition: all 0.3s ease;
}

:deep(.v-select .v-field:hover) {
  background: rgb(var(--v-theme-surface-bright));
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

:deep(.v-select .v-field--focused) {
  background: rgb(var(--v-theme-surface-bright));
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.3);
}

/* Enhanced button styling */
:deep(.v-btn) {
  border-radius: 12px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

:deep(.v-btn:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

:deep(.v-btn--variant-elevated) {
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

:deep(.v-btn--variant-elevated:hover) {
  box-shadow: 0 6px 16px rgba(var(--v-theme-primary), 0.4);
}

/* Enhanced slider styling */
:deep(.v-slider) {
  margin-top: 24px;
}

:deep(.v-slider .v-slider-track__fill) {
  background: linear-gradient(
    90deg,
    rgb(var(--v-theme-primary)),
    rgb(var(--v-theme-primary-lighten-1))
  );
}

:deep(.v-slider .v-slider-thumb) {
  background: rgb(var(--v-theme-primary));
  box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.4);
}

/* Enhanced progress bar styling */
:deep(.v-progress-linear) {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

:deep(.v-progress-linear .v-progress-linear__determinate) {
  background: linear-gradient(
    90deg,
    rgb(var(--v-theme-primary)),
    rgb(var(--v-theme-primary-lighten-1))
  );
}

/* Enhanced data table styling */
:deep(.v-data-table) {
  border-radius: 12px;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

:deep(.v-data-table .v-data-table__thead) {
  background: rgb(var(--v-theme-surface-variant));
}

:deep(.v-data-table .v-data-table__tbody tr:hover) {
  background: rgba(var(--v-theme-primary), 0.05);
}

:deep(.v-data-table .v-data-table__tbody tr:nth-child(even)) {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}

/* Enhanced chip styling */
:deep(.v-chip) {
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.v-chip:hover) {
  transform: scale(1.05);
}

/* Enhanced card styling */
:deep(.v-card) {
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgb(var(--v-theme-surface));
}

:deep(.v-card-text) {
  padding: 24px;
}

:deep(.v-card-actions) {
  padding: 16px 24px 24px 24px;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(var(--v-theme-surface-variant), 0.3) 100%
  );
}

/* Window item styling */
:deep(.v-window-item) {
  padding: 24px 0;
}

/* Section headers */
.text-h6 {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
  margin-bottom: 8px;
}

.text-caption {
  color: rgb(var(--v-theme-on-surface-variant));
  margin-bottom: 16px;
}

/* Responsive design */
@media (max-width: 960px) {
  .discovery-content {
    padding: var(--spacing-md);
  }

  .discovery-footer {
    padding: 12px 16px;
  }

  .discovery-header {
    padding: 20px 16px;
    margin-bottom: 24px;
  }

  .discovery-title {
    font-size: 1.6rem !important;
  }

  .discovery-subtitle {
    font-size: 1rem;
  }

  .discovery-tab {
    min-width: 100px;
    font-size: 0.9rem;
  }
}

@media (max-width: 600px) {
  .discovery-content {
    padding: var(--spacing-sm);
  }

  .discovery-footer {
    padding: 12px;
  }

  .discovery-footer .d-flex {
    flex-direction: column;
    gap: 12px;
  }

  .discovery-btn {
    width: 100%;
  }

  .discovery-header {
    padding: 16px 12px;
  }

  .discovery-title {
    font-size: 1.4rem !important;
  }

  .discovery-subtitle {
    font-size: 0.95rem;
  }

  .discovery-tab {
    min-width: 80px;
    font-size: 0.8rem;
    padding: 8px 12px;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .discovery-logo,
  .discovery-tab,
  :deep(.v-text-field .v-field),
  :deep(.v-select .v-field),
  :deep(.v-btn),
  :deep(.v-chip),
  :deep(.v-alert),
  :deep(.v-card) {
    animation: none;
    transition: none;
  }

  .discovery-tab:hover,
  :deep(.v-text-field .v-field:hover),
  :deep(.v-select .v-field:hover),
  :deep(.v-btn:hover),
  :deep(.v-chip:hover),
  :deep(.v-alert:hover) {
    transform: none;
  }
}

/* Comprehensive dropdown overlay fixes for Vuetify 3.x */
:deep(.v-overlay) {
  z-index: 10001 !important;
  position: fixed !important;
}

:deep(.v-overlay__content) {
  z-index: 10002 !important;
  position: fixed !important;
}

:deep(.v-overlay__scrim) {
  z-index: 10000 !important;
  position: fixed !important;
}

:deep(.v-menu) {
  z-index: 10003 !important;
}

:deep(.v-menu > .v-overlay__content) {
  z-index: 10003 !important;
  position: fixed !important;
}

:deep(.v-select__content) {
  z-index: 10003 !important;
}

:deep(.v-list) {
  z-index: 10004 !important;
  background: rgb(var(--v-theme-surface)) !important;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
  max-height: 300px !important;
  overflow-y: auto !important;
}

:deep(.v-list-item) {
  color: rgb(var(--v-theme-on-surface)) !important;
  transition: all 0.2s ease;
  padding: 12px 16px !important;
  min-height: 48px !important;
  position: relative;
  z-index: 1;
}

:deep(.v-list-item:hover) {
  background: rgba(var(--v-theme-primary), 0.1) !important;
  color: rgb(var(--v-theme-primary)) !important;
}

:deep(.v-list-item--active) {
  background: rgba(255, 152, 0, 0.25) !important;
  color: #ff9800 !important;
}

:deep(.v-list-item-title) {
  color: inherit !important;
  font-weight: 400;
  position: relative;
  z-index: 2;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* Additional dropdown title visibility improvements */
:deep(.v-list-item:hover .v-list-item-title) {
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

:deep(.v-list-item--active .v-list-item-title) {
  color: #ff9800 !important;
  font-weight: 500;
}

/* Ensure dropdown menu borders don't interfere with text */
:deep(.v-list-item::before) {
  z-index: 0 !important;
}

:deep(.v-list-item::after) {
  z-index: 0 !important;
}

/* Improve dropdown menu contrast */
:deep(.v-menu .v-overlay__content) {
  backdrop-filter: blur(8px);
}

:deep(.v-list) {
  backdrop-filter: blur(8px);
}

/* Ensure select field interaction */
:deep(.v-select .v-field__input) {
  cursor: pointer !important;
}

:deep(.v-select .v-field) {
  cursor: pointer !important;
}

/* Ensure dropdown arrow is visible and clickable */
:deep(.v-select .v-field__append-inner) {
  pointer-events: auto !important;
  cursor: pointer !important;
  color: rgb(var(--v-theme-on-surface-variant));
}

:deep(.v-select.v-select--active-menu .v-field__append-inner .v-icon) {
  transform: rotate(180deg);
  color: rgb(var(--v-theme-primary));
}

/* Fix overlay positioning */
:deep(.v-overlay) {
  position: fixed !important;
}

:deep(.v-overlay__scrim) {
  position: fixed !important;
  z-index: 9999 !important;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .discovery-header {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  .discovery-tabs {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  :deep(.v-text-field .v-field),
  :deep(.v-select .v-field) {
    border: 2px solid rgb(var(--v-theme-outline));
  }

  :deep(.v-btn) {
    border: 2px solid rgb(var(--v-theme-primary));
  }

  :deep(.v-data-table) {
    border: 2px solid rgb(var(--v-theme-outline));
  }
}
</style>
