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
                      <v-col cols="12">
                        <h3 class="text-h6 mb-2">Port Configuration</h3>
                        <p class="text-caption mb-4">
                          Specify which ports to scan (comma-separated)
                        </p>

                        <v-text-field
                          v-model="portsInput"
                          label="Ports to Scan"
                          hint="e.g., 80, 4028, 8332, 18332, 8333 (Bitcoin P2P port)"
                          persistent-hint
                          variant="outlined"
                          prepend-inner-icon="mdi-ethernet"
                          :rules="[portsValidationRule]"
                        ></v-text-field>
                      </v-col>
                    </v-row>

                    <v-row>
                      <v-col cols="12" class="text-center">
                        <v-btn
                          v-if="!scanning"
                          color="primary"
                          size="large"
                          :disabled="!ipRangeValid"
                          @click="startScan"
                        >
                          <v-icon start>mdi-radar</v-icon>
                          Start Network Scan
                        </v-btn>

                        <v-btn
                          v-else
                          color="error"
                          size="large"
                          @click="stopScan"
                        >
                          <v-icon start>mdi-stop</v-icon>
                          Stop Scan
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
                          <span v-if="currentIp"
                            >Scanning IP {{ currentIp }}...</span
                          >
                          <span v-else>Starting network scan...</span>
                        </p>
                        <p class="text-center text-caption">
                          Found {{ discoveredMiners.length }} miner{{
                            discoveredMiners.length === 1 ? "" : "s"
                          }}
                          so far
                        </p>
                      </v-col>
                    </v-row>

                    <!-- Error/Status Messages -->
                    <v-row v-if="statusMessage">
                      <v-col cols="12">
                        <v-alert
                          :type="statusMessage.type"
                          variant="outlined"
                          class="mb-4"
                        >
                          {{ statusMessage.text }}
                        </v-alert>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Manual Entry Tab -->
              <v-window-item>
                <v-card flat>
                  <v-card-text>
                    <div class="text-center">
                      <h3 class="text-h6 mb-4">Add Miner Manually</h3>
                      <p class="text-body-2 mb-6">
                        If you know the exact details of your miner, you can add
                        it directly using the standardized form.
                      </p>
                      <v-btn
                        color="primary"
                        size="large"
                        @click="openAddMinerDialog"
                      >
                        <v-icon start>mdi-plus-circle</v-icon>
                        Add Miner
                      </v-btn>
                    </div>
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

    <!-- Add Miner Dialog -->
    <AddMinerDialog
      v-model="addMinerDialog"
      @miner-added="handleMinerAdded"
      @error="handleMinerError"
    />
  </div>
</template>

<script>
import BitcoinLogo from "../BitcoinLogo.vue";
import AddMinerDialog from "../AddMinerDialog.vue";
import { DEFAULT_SCAN_PORTS, formatPortList } from "../../config/ports.config";

export default {
  name: "NetworkDiscoveryScreen",

  components: {
    BitcoinLogo,
    AddMinerDialog,
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
      websocket: null,
      statusMessage: null,

      ipRange: {
        start: "192.168.1.1",
        end: "192.168.1.254",
      },

      scanOptions: {
        minerTypes: ["Magic Miner", "Avalon Nano", "Bitaxe", "Bitcoin Node"],
        timeout: 3,
      },

      portsInput: formatPortList(DEFAULT_SCAN_PORTS),

      addMinerDialog: false,

      discoveredMiners: [],

      minerTypeOptions: [
        "Magic Miner",
        "Avalon Nano",
        "Bitaxe",
        "Bitcoin Node",
      ],

      minerHeaders: [
        { title: "Name", key: "name" },
        { title: "IP Address", key: "ip" },
        { title: "Port", key: "port" },
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

    parsedPorts() {
      try {
        if (!this.portsInput || this.portsInput.trim() === "") {
          return DEFAULT_SCAN_PORTS;
        }

        const ports = this.portsInput
          .split(",")
          .map((p) => p.trim())
          .filter((p) => p !== "")
          .map((p) => parseInt(p))
          .filter((p) => !isNaN(p) && p >= 1 && p <= 65535);

        return ports.length > 0 ? ports : DEFAULT_SCAN_PORTS;
      } catch (error) {
        console.error("Error parsing ports:", error);
        return DEFAULT_SCAN_PORTS;
      }
    },
  },

  methods: {
    ipAddressRule(value) {
      const pattern =
        /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      return pattern.test(value) || "Invalid IP address format";
    },

    portsValidationRule(value) {
      if (!value || value.trim() === "") {
        return true; // Allow empty, will use defaults
      }

      const ports = value
        .split(",")
        .map((p) => p.trim())
        .filter((p) => p);

      if (ports.length === 0) {
        return true; // Allow empty
      }

      if (ports.length > 20) {
        return "Maximum 20 ports allowed";
      }

      for (const port of ports) {
        const portNum = parseInt(port);
        if (isNaN(portNum)) {
          return `"${port}" is not a valid port number`;
        }
        if (portNum < 1 || portNum > 65535) {
          return `Port ${portNum} must be between 1 and 65535`;
        }
      }

      return true;
    },

    async startScan() {
      if (!this.ipRangeValid) return;

      this.scanning = true;
      this.scanProgress = 0;
      this.currentIp = this.ipRange.start;
      this.discoveredMiners = [];
      this.statusMessage = null;

      try {
        // Use real network discovery API
        await this.performRealScan();
      } catch (error) {
        console.error("Error during network scan:", error);
        this.scanning = false;
        this.statusMessage = {
          type: "error",
          text: "Network scan failed. Please try again or add miners manually.",
        };
      }
    },

    async stopScan() {
      try {
        // Stop the discovery via API
        const response = await fetch("/api/discovery/stop", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          console.log("Discovery stopped successfully");
        }
      } catch (error) {
        console.error("Error stopping discovery:", error);
      }

      // Clean up local state
      this.scanning = false;

      if (this.websocket) {
        this.websocket.close();
        this.websocket = null;
      }
    },

    async performRealScan() {
      try {
        // Convert IP range to CIDR notation for the API
        const networkCidr = this.convertRangeToCidr();
        console.log("Starting scan with network:", networkCidr);

        // Use the universal network scan service for consistent port handling
        const { networkScanService } = await import(
          "../../services/networkScanService"
        );

        const scanOptions = {
          network: networkCidr,
          // Use parsed ports from user input
          ports: this.parsedPorts,
          timeout: this.scanOptions.timeout,
        };

        await networkScanService.startScan(scanOptions);
        return; // Let the universal service handle the rest

        console.log("Discovery request:", requestBody);

        // First test if the API endpoint is reachable
        console.log("Testing API endpoint reachability...");
        try {
          // Test a simple GET endpoint first
          const testResponse = await fetch("/api/miners");
          console.log("Miners API test response:", testResponse.status);
          if (testResponse.ok) {
            const testData = await testResponse.json();
            console.log("Miners API test data:", testData);
          } else {
            console.log("Miners API test failed:", testResponse.status);
          }
        } catch (testError) {
          console.error("API test failed:", testError);
        }

        // Test the discovery status endpoint
        try {
          const statusResponse = await fetch("/api/discovery/status");
          console.log("Discovery status test response:", statusResponse.status);
          if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            console.log("Discovery status test data:", statusData);
          }
        } catch (statusError) {
          console.error("Discovery status test failed:", statusError);
        }

        // Test a simple health check endpoint
        try {
          const healthResponse = await fetch("/api/health");
          console.log("Health check test response:", healthResponse.status);
          if (healthResponse.ok) {
            const healthData = await healthResponse.json();
            console.log("Health check test data:", healthData);
          }
        } catch (healthError) {
          console.error("Health check test failed:", healthError);
        }

        // All endpoint tests completed successfully

        // Start the discovery via API
        console.log("Making discovery API request...");

        let response;
        try {
          // Add timeout to the fetch request
          const controller = new AbortController();
          const timeoutId = setTimeout(() => {
            console.log("Discovery API request timed out after 30 seconds");
            controller.abort();
          }, 30000);

          response = await fetch("/api/discovery", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
            signal: controller.signal,
          });

          clearTimeout(timeoutId);
          console.log("Discovery API request completed");
        } catch (fetchError) {
          console.error("Fetch request failed:", fetchError);
          if (fetchError.name === "AbortError") {
            throw new Error("Discovery API request timed out after 30 seconds");
          }
          throw new Error(`Network request failed: ${fetchError.message}`);
        }

        console.log("Discovery response status:", response.status);
        console.log(
          "Discovery response headers:",
          Object.fromEntries(response.headers.entries())
        );

        if (!response.ok) {
          let errorText;
          try {
            errorText = await response.text();
            console.error("Discovery API error response:", errorText);
          } catch (textError) {
            console.error("Could not read error response:", textError);
            errorText = "Unknown error";
          }
          throw new Error(
            `Discovery API error: ${response.status} - ${errorText}`
          );
        }

        let result;
        try {
          result = await response.json();
          console.log("Discovery started successfully:", result);
        } catch (jsonError) {
          console.error("Could not parse JSON response:", jsonError);
          const responseText = await response.text();
          console.error("Raw response:", responseText);
          throw new Error("Invalid JSON response from discovery API");
        }

        // Validate that the response contains expected data
        if (!result || typeof result !== "object") {
          console.error("Invalid discovery response format:", result);
          throw new Error("Invalid response from discovery API");
        }

        // Set up WebSocket connection for real-time updates
        this.connectWebSocketForDiscovery();

        // Poll for status updates as fallback
        this.pollDiscoveryStatus();
      } catch (error) {
        console.error("Error starting real network scan:", error);
        this.scanning = false;
        throw error;
      }
    },

    convertRangeToCidr() {
      // Convert IP range (start-end) to a list of individual IPs
      // This gives us precise control over the scan range
      const startParts = this.ipRange.start.split(".").map(Number);
      const endParts = this.ipRange.end.split(".").map(Number);

      // For now, we'll create a custom range format that the backend can handle
      // Format: "192.168.1.83-192.168.1.88" for precise range scanning
      const rangeFormat = `${this.ipRange.start}-${this.ipRange.end}`;

      console.log(
        `Converting IP range: ${this.ipRange.start} to ${this.ipRange.end}`
      );
      console.log(`Range format: ${rangeFormat}`);

      return rangeFormat;
    },

    connectWebSocketForDiscovery() {
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
          console.log("WebSocket connected for discovery");
          // Subscribe to discovery updates
          const subscribeMessage = {
            type: "subscribe",
            topics: ["discovery"],
          };
          console.log("Sending WebSocket subscription:", subscribeMessage);
          this.websocket.send(JSON.stringify(subscribeMessage));
        };

        this.websocket.onmessage = (event) => {
          try {
            console.log("WebSocket message received:", event.data);
            const message = JSON.parse(event.data);
            console.log("Parsed WebSocket message:", message);

            if (message.type === "discovery_update" && message.data) {
              console.log("Processing discovery update:", message.data);
              this.handleDiscoveryUpdate(message.data);
            } else if (message.type === "connection_established") {
              console.log("WebSocket connection established:", message);
            } else if (message.type === "subscription_update") {
              console.log("WebSocket subscription confirmed:", message);
            } else {
              console.log("Unhandled WebSocket message type:", message.type);
            }
          } catch (error) {
            console.error(
              "Error parsing WebSocket message:",
              error,
              event.data
            );
          }
        };

        this.websocket.onclose = () => {
          console.log("WebSocket disconnected");
          this.websocket = null;
        };

        this.websocket.onerror = (error) => {
          console.error("WebSocket error:", error);
        };
      } catch (error) {
        console.error("Error connecting WebSocket:", error);
      }
    },

    handleDiscoveryUpdate(data) {
      console.log("=== DISCOVERY UPDATE ===");
      console.log("Raw data:", data);
      console.log("Data type:", typeof data);
      console.log("Data keys:", Object.keys(data || {}));

      // Update progress
      if (data.total_hosts && data.scanned_hosts !== undefined) {
        const newProgress = (data.scanned_hosts / data.total_hosts) * 100;
        console.log(
          `Progress update: ${data.scanned_hosts}/${data.total_hosts} = ${newProgress}%`
        );
        this.scanProgress = newProgress;
      } else {
        console.log("No progress data available:", {
          total_hosts: data.total_hosts,
          scanned_hosts: data.scanned_hosts,
        });
      }

      // Update current IP
      if (data.current_ip) {
        console.log("Current IP update:", data.current_ip);
        this.currentIp = data.current_ip;
      } else {
        console.log("No current IP in update");
      }

      // Update found miners
      if (data.found_miners && Array.isArray(data.found_miners)) {
        console.log("Found miners update:", data.found_miners);
        this.discoveredMiners = data.found_miners.map((miner) => ({
          name:
            miner.device_info?.model || `${miner.type} (${miner.ip_address})`,
          ip: miner.ip_address,
          type: this.mapMinerType(miner.type),
          status: "online",
          port: miner.port,
        }));

        // Automatically emit miners found to parent to enable Continue button
        this.$emit("miners-found", this.discoveredMiners);
      } else {
        console.log("No miners data or invalid format:", data.found_miners);
      }

      // Handle completion
      if (data.status === "completed") {
        this.scanning = false;
        this.activeTab = 2; // Switch to results tab

        if (this.websocket) {
          this.websocket.close();
          this.websocket = null;
        }

        const minerCount = this.discoveredMiners.length;
        this.statusMessage = {
          type: minerCount > 0 ? "success" : "info",
          text:
            minerCount > 0
              ? `Discovery completed! Found ${minerCount} miner${minerCount === 1 ? "" : "s"}.`
              : "Discovery completed. No miners found on the network.",
        };

        console.log(`Discovery completed. Found ${minerCount} miners.`);
      } else if (data.status === "error") {
        this.scanning = false;
        this.statusMessage = {
          type: "error",
          text: `Discovery failed: ${data.error || "Unknown error occurred"}`,
        };
        console.error("Discovery error:", data.error);

        if (this.websocket) {
          this.websocket.close();
          this.websocket = null;
        }
      }
    },

    mapMinerType(apiType) {
      // Map API miner types to display names
      const typeMap = {
        bitaxe: "Bitaxe",
        avalon_nano: "Avalon Nano",
        magic_miner: "Magic Miner",
        bitcoin_node: "Bitcoin Node",
      };
      return typeMap[apiType] || apiType;
    },

    async pollDiscoveryStatus() {
      // Fallback polling in case WebSocket fails
      console.log("Starting discovery status polling...");
      const pollInterval = setInterval(async () => {
        if (!this.scanning) {
          console.log("Stopping discovery polling - scan no longer active");
          clearInterval(pollInterval);
          return;
        }

        try {
          console.log("Polling discovery status...");
          const response = await fetch("/api/discovery/status");
          console.log("Discovery status response:", response.status);

          if (response.ok) {
            const status = await response.json();
            console.log("Discovery status data:", status);

            // Always update from polling for debugging
            this.handleDiscoveryUpdate(status);
          } else {
            console.error("Discovery status request failed:", response.status);
          }
        } catch (error) {
          console.error("Error polling discovery status:", error);
        }
      }, 2000); // Poll every 2 seconds
    },

    openAddMinerDialog() {
      this.addMinerDialog = true;
    },

    handleMinerAdded(miner) {
      // Add the miner to the discovered miners list
      this.discoveredMiners.push({
        name: miner.name,
        ip: miner.ip_address,
        type: this.mapMinerType(miner.type),
        port: miner.port || null,
        status: "unknown", // Status is unknown until we connect to it
      });

      // Automatically emit miners found to parent to enable Continue button
      this.$emit("miners-found", this.discoveredMiners);

      // Switch to results tab to show the added miner
      this.activeTab = 2;
    },

    handleMinerError(error) {
      console.error("Error adding miner in wizard:", error);
      // Could show a snackbar or alert here if needed
    },

    removeMiner(miner) {
      const index = this.discoveredMiners.findIndex(
        (m) => m.ip === miner.ip && m.port === miner.port
      );
      if (index !== -1) {
        this.discoveredMiners.splice(index, 1);

        // Automatically emit miners found to parent to update Continue button state
        this.$emit("miners-found", this.discoveredMiners);
      }
    },

    emitMinersFound() {
      // Emit the discovered miners to the parent component
      this.$emit("miners-found", this.discoveredMiners);
    },
  },

  beforeUnmount() {
    // Clean up WebSocket connection when component is destroyed
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
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
