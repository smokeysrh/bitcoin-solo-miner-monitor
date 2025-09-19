<template>
  <div>
    <!-- Hero Section with Bitcoin Logo -->
    <v-row class="mb-6">
      <v-col cols="12" class="text-center">
        <div class="bitcoin-hero">
          <BitcoinLogo 
            size="xl" 
            class="bitcoin-hero__logo mb-4"
            data-testid="about-hero-logo"
          />
          <h1 class="text-h3 mb-2 bitcoin-hero__title">
            About Bitcoin Solo Miner Monitor
          </h1>
          <div class="bitcoin-hero__tagline mb-4">
            <p class="text-h5 font-italic text-center">
              "One App to rule them all, One App to find them,<br>
              One App to bring them all, and in the light bind them...<br>
              <span class="text-warning font-weight-bold">to a single dashboard!</span>"
            </p>
          </div>
          <p class="text-h6 bitcoin-hero__subtitle">
            Unified monitoring for your Bitcoin mining operation
          </p>
        </div>
      </v-col>
    </v-row>

    <!-- App Information -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Bitcoin Solo Miner Monitoring App</v-card-title>
          <v-card-text>
            <p class="text-body-1">
              A unified monitoring and management solution for diverse Bitcoin
              mining hardware, specifically targeting solo miners running Magic
              Miner, Avalon Nano, and Bitaxe devices on a local network. BUILT BY PLEBS, FOR PLEBS.
            </p>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-information</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>Version</v-list-item-title>
                <v-list-item-subtitle>{{ appVersion }}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-calendar</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>Release Date</v-list-item-title>
                <v-list-item-subtitle>{{ releaseDate }}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-license</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>License</v-list-item-title>
                <v-list-item-subtitle>MIT License</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>System Information</v-card-title>
          <v-card-text>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-server</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>Backend</v-list-item-title>
                <v-list-item-subtitle
                  >Python {{ systemInfo.pythonVersion }} with
                  FastAPI</v-list-item-subtitle
                >
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-language-javascript</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>Frontend</v-list-item-title>
                <v-list-item-subtitle
                  >Vue.js 3 with Vuetify 3</v-list-item-subtitle
                >
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-database</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>Database</v-list-item-title>
                <v-list-item-subtitle
                  >SQLite for configuration, InfluxDB for time-series
                  data</v-list-item-subtitle
                >
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-icon>
                <v-icon>mdi-chart-line</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>Visualization</v-list-item-title>
                <v-list-item-subtitle
                  >Chart.js for metrics, D3.js for network
                  topology</v-list-item-subtitle
                >
              </v-list-item-content>
            </v-list-item>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Features -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Key Features</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-card outlined>
                  <v-card-title class="text-h6">
                    <v-icon left color="primary">mdi-monitor-dashboard</v-icon>
                    Unified Dashboard
                  </v-card-title>
                  <v-card-text>
                    Monitor all your Bitcoin miners in one place with real-time
                    updates on hashrate, temperature, and other critical
                    metrics.
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" md="4">
                <v-card outlined>
                  <v-card-title class="text-h6">
                    <v-icon left color="primary"
                      >mdi-chart-timeline-variant</v-icon
                    >
                    Performance Analytics
                  </v-card-title>
                  <v-card-text>
                    Track historical performance with detailed charts and
                    analytics to optimize your mining operation.
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" md="4">
                <v-card outlined>
                  <v-card-title class="text-h6">
                    <v-icon left color="primary">mdi-lan</v-icon>
                    Network Discovery
                  </v-card-title>
                  <v-card-text>
                    Automatically discover miners on your local network and add
                    them to your monitoring dashboard.
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <v-row class="mt-4">
              <v-col cols="12" md="4">
                <v-card outlined>
                  <v-card-title class="text-h6">
                    <v-icon left color="primary">mdi-tune</v-icon>
                    Miner Management
                  </v-card-title>
                  <v-card-text>
                    Control your miners remotely with restart capabilities and
                    configuration management.
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" md="4">
                <v-card outlined>
                  <v-card-title class="text-h6">
                    <v-icon left color="primary">mdi-bell-alert</v-icon>
                    Alerts & Notifications
                  </v-card-title>
                  <v-card-text>
                    Set up alerts for critical conditions like high temperature
                    or miner offline status.
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" md="4">
                <v-card outlined>
                  <v-card-title class="text-h6">
                    <v-icon left color="primary">mdi-export</v-icon>
                    Data Export
                  </v-card-title>
                  <v-card-text>
                    Export performance data and charts for external analysis or
                    record-keeping.
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Supported Miners -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Supported Miners</v-card-title>
          <v-card-text>
            <v-tabs v-model="activeTab" background-color="primary" dark>
              <v-tab value="bitaxe">Bitaxe</v-tab>
              <v-tab value="avalon">Avalon Nano</v-tab>
              <v-tab value="magic">Magic Miner</v-tab>
            </v-tabs>

            <v-window v-model="activeTab">
              <v-window-item value="bitaxe">
                <v-card flat>
                  <v-card-text>
                    <h3 class="text-h6 mb-2">Bitaxe Miner</h3>
                    <p class="text-body-1">
                      The Bitaxe is an open-source Bitcoin ASIC miner designed
                      for solo mining. It features:
                    </p>
                    <ul>
                      <li>HTTP REST API with JSON responses</li>
                      <li>
                        Comprehensive endpoints for system info, statistics, and
                        control
                      </li>
                      <li>
                        Well-documented and accessible via standard HTTP
                        requests
                      </li>
                      <li>Customizable settings for optimal performance</li>
                    </ul>
                    <p class="text-body-1">
                      This application connects to Bitaxe miners using their
                      HTTP API to retrieve real-time data and send control
                      commands.
                    </p>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <v-window-item value="avalon">
                <v-card flat>
                  <v-card-text>
                    <h3 class="text-h6 mb-2">Avalon Nano Miner</h3>
                    <p class="text-body-1">
                      The Avalon Nano is a compact Bitcoin ASIC miner. It
                      features:
                    </p>
                    <ul>
                      <li>CGMiner API over TCP port 4028</li>
                      <li>JSON-RPC requests for monitoring and control</li>
                      <li>Well-established standard in the mining community</li>
                      <li>Efficient power consumption for its size</li>
                    </ul>
                    <p class="text-body-1">
                      This application connects to Avalon Nano miners using the
                      CGMiner API protocol to retrieve performance data and send
                      commands.
                    </p>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <v-window-item value="magic">
                <v-card flat>
                  <v-card-text>
                    <h3 class="text-h6 mb-2">Magic Miner</h3>
                    <p class="text-body-1">
                      The Magic Miner is a user-friendly Bitcoin mining device.
                      It features:
                    </p>
                    <ul>
                      <li>Web-based management interface</li>
                      <li>
                        Underlying HTTP API accessible through web interface
                      </li>
                      <li>
                        Can be accessed via web interface scraping or request
                        interception
                      </li>
                      <li>Simple setup and configuration</li>
                    </ul>
                    <p class="text-body-1">
                      This application connects to Magic Miners by interfacing
                      with their web management system to retrieve data and
                      control the device.
                    </p>
                  </v-card-text>
                </v-card>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Documentation -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Documentation</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-card outlined class="text-center">
                  <v-card-title class="justify-center">
                    <v-icon large color="primary"
                      >mdi-book-open-page-variant</v-icon
                    >
                  </v-card-title>
                  <v-card-title class="justify-center">User Guide</v-card-title>
                  <v-card-text>
                    Learn how to use all features of the Bitcoin Solo Miner
                    Monitoring App.
                  </v-card-text>
                  <v-card-actions class="justify-center">
                    <v-btn color="primary" @click="openDocumentation('user')">
                      Open Guide
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>

              <v-col cols="12" md="4">
                <v-card outlined class="text-center">
                  <v-card-title class="justify-center">
                    <v-icon large color="primary">mdi-api</v-icon>
                  </v-card-title>
                  <v-card-title class="justify-center"
                    >API Documentation</v-card-title
                  >
                  <v-card-text>
                    Explore the API endpoints for integration with other tools.
                  </v-card-text>
                  <v-card-actions class="justify-center">
                    <v-btn color="primary" @click="openDocumentation('api')">
                      View API Docs
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>

              <v-col cols="12" md="4">
                <v-card outlined class="text-center">
                  <v-card-title class="justify-center">
                    <v-icon large color="primary"
                      >mdi-frequently-asked-questions</v-icon
                    >
                  </v-card-title>
                  <v-card-title class="justify-center">FAQ</v-card-title>
                  <v-card-text>
                    Find answers to common questions about the application.
                  </v-card-text>
                  <v-card-actions class="justify-center">
                    <v-btn color="primary" @click="openDocumentation('faq')">
                      Read FAQ
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Support -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Support the Project</v-card-title>
          <v-card-text>
            <p class="text-body-1">
              If you find value in this application, please consider supporting its development.
              Your contributions help maintain and improve the Bitcoin Solo Miner Monitor.
            </p>
            <div class="text-center mt-4">
              <v-chip
                class="donation-address-chip"
                color="warning"
                size="large"
                @click="copyDonationAddress"
                :loading="clipboard.isLoading.value"
                prepend-icon="mdi-bitcoin"
                variant="elevated"
              >
                <span class="donation-address-text">
                  bc1qnce06pg2gqewjvjmfavwrjt5f4zc37k5d26c6e
                </span>
                <template v-slot:append>
                  <v-icon>mdi-content-copy</v-icon>
                </template>
              </v-chip>
              <p class="text-caption mt-2 text-medium-emphasis">
                Click to copy Bitcoin address to clipboard
              </p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Credits -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Credits</v-card-title>
          <v-card-text>
            <p class="text-body-1">
              The Bitcoin Solo Miner Monitoring App was developed as a custom
              solution for monitoring and managing diverse Bitcoin mining
              hardware on a local network.
            </p>
            <p class="text-body-1">
              Special thanks to the open-source community for providing the
              tools and libraries that made this application possible.
            </p>
            <v-divider class="my-4"></v-divider>
            <p class="text-body-2 text-center">
              © {{ new Date().getFullYear() }} Bitcoin Solo Miner Monitoring
              App. All rights reserved.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Documentation Dialog -->
    <v-dialog v-model="showDocDialog" max-width="800px">
      <v-card>
        <v-card-title>
          {{ docDialogTitle }}
          <v-spacer></v-spacer>
          <v-btn icon @click="showDocDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <div v-if="activeDoc === 'user'">
            <h3>User Guide</h3>
            <p>
              This guide will help you get started with the Bitcoin Solo Miner
              Monitoring App.
            </p>

            <h4 class="mt-4">Getting Started</h4>
            <ol>
              <li>
                <strong>Dashboard Overview:</strong> The dashboard provides a
                quick summary of all your miners, including their status,
                hashrate, and temperature.
              </li>
              <li>
                <strong>Adding Miners:</strong> You can add miners manually by
                providing their IP address and type, or use the Network
                Discovery feature to automatically find miners on your network.
              </li>
              <li>
                <strong>Monitoring Miners:</strong> Click on any miner in the
                dashboard to view detailed information and performance metrics.
              </li>
            </ol>

            <h4 class="mt-4">Features</h4>
            <ul>
              <li>
                <strong>Real-time Monitoring:</strong> View real-time updates on
                miner status, hashrate, temperature, and other metrics.
              </li>
              <li>
                <strong>Historical Data:</strong> Access historical performance
                data through the Analytics page.
              </li>
              <li>
                <strong>Network Topology:</strong> Visualize your mining network
                on the Network page.
              </li>
              <li>
                <strong>Miner Control:</strong> Restart miners and adjust
                settings directly from the application.
              </li>
            </ul>

            <h4 class="mt-4">Troubleshooting</h4>
            <ul>
              <li>
                <strong>Miner Offline:</strong> Check the physical connection
                and power supply. Verify that the miner's management interface
                is accessible from your browser.
              </li>
              <li>
                <strong>Data Not Updating:</strong> Check your network
                connection and refresh the page. If the issue persists, restart
                the application.
              </li>
              <li>
                <strong>Discovery Not Finding Miners:</strong> Ensure that
                miners are on the same network and that the correct network
                range is specified.
              </li>
            </ul>
          </div>

          <div v-if="activeDoc === 'api'">
            <h3>API Documentation</h3>
            <p>
              The Bitcoin Solo Miner Monitoring App provides a RESTful API for
              integration with other tools.
            </p>

            <h4 class="mt-4">Base URL</h4>
            <pre>http://[server-address]:[port]/api</pre>

            <h4 class="mt-4">API Access</h4>
            <p>
              API requests are available without authentication for local
              network access.
            </p>

            <h4 class="mt-4">Endpoints</h4>

            <h5 class="mt-2">Miners</h5>
            <ul>
              <li><code>GET /miners</code> - Get all miners</li>
              <li>
                <code>GET /miners/{miner_id}</code> - Get a specific miner
              </li>
              <li><code>POST /miners</code> - Add a new miner</li>
              <li><code>PUT /miners/{miner_id}</code> - Update a miner</li>
              <li><code>DELETE /miners/{miner_id}</code> - Remove a miner</li>
              <li>
                <code>POST /miners/{miner_id}/restart</code> - Restart a miner
              </li>
            </ul>

            <h5 class="mt-2">Metrics</h5>
            <ul>
              <li>
                <code>GET /miners/{miner_id}/metrics</code> - Get metrics for a
                specific miner
              </li>
              <li>
                <code>GET /miners/{miner_id}/metrics/latest</code> - Get latest
                metrics for a specific miner
              </li>
            </ul>

            <h5 class="mt-2">Discovery</h5>
            <ul>
              <li>
                <code>POST /discovery</code> - Start discovery of miners on the
                network
              </li>
              <li>
                <code>GET /discovery/status</code> - Get the status of the
                discovery process
              </li>
            </ul>

            <h5 class="mt-2">Settings</h5>
            <ul>
              <li><code>GET /settings</code> - Get application settings</li>
              <li><code>PUT /settings</code> - Update application settings</li>
            </ul>

            <h4 class="mt-4">WebSocket</h4>
            <p>Real-time updates are available through WebSocket:</p>
            <pre>ws://[server-address]:[port]/ws</pre>
          </div>

          <div v-if="activeDoc === 'faq'">
            <h3>Frequently Asked Questions</h3>

            <h4 class="mt-4">General Questions</h4>

            <h5 class="mt-2">What is the Bitcoin Solo Miner Monitoring App?</h5>
            <p>
              The Bitcoin Solo Miner Monitoring App is a unified monitoring and
              management solution for diverse Bitcoin mining hardware,
              specifically targeting solo miners running Magic Miner, Avalon
              Nano, and Bitaxe devices on a local network.
            </p>

            <h5 class="mt-2">What miners are supported?</h5>
            <p>
              Currently, the application supports Bitaxe, Avalon Nano, and Magic
              Miner devices. Support for additional miners may be added in
              future updates.
            </p>

            <h5 class="mt-2">Is this application free to use?</h5>
            <p>
              Yes, the Bitcoin Solo Miner Monitoring App is free to use and is
              released under the MIT License.
            </p>

            <h4 class="mt-4">Technical Questions</h4>

            <h5 class="mt-2">What are the system requirements?</h5>
            <p>The application requires:</p>
            <ul>
              <li>Python 3.11 or higher</li>
              <li>Node.js 14 or higher (for development)</li>
              <li>SQLite and InfluxDB for data storage</li>
              <li>A modern web browser</li>
            </ul>

            <h5 class="mt-2">How do I install the application?</h5>
            <p>
              Installation instructions are provided in the README.md file in
              the application repository. Generally, you'll need to:
            </p>
            <ol>
              <li>Clone the repository</li>
              <li>Install backend dependencies</li>
              <li>Install frontend dependencies</li>
              <li>Configure the application</li>
              <li>Start the backend and frontend servers</li>
            </ol>

            <h5 class="mt-2">How do I update the application?</h5>
            <p>
              To update the application, pull the latest changes from the
              repository and restart the application. Make sure to back up your
              configuration and data before updating.
            </p>

            <h4 class="mt-4">Troubleshooting</h4>

            <h5 class="mt-2">Why can't I connect to my miner?</h5>
            <p>Ensure that:</p>
            <ul>
              <li>The miner is powered on and connected to your network</li>
              <li>The IP address and port are correct</li>
              <li>There are no firewalls blocking the connection</li>
              <li>The miner's API or management interface is enabled</li>
            </ul>

            <h5 class="mt-2">Why is the data not updating?</h5>
            <p>This could be due to:</p>
            <ul>
              <li>Network connectivity issues</li>
              <li>The miner being offline or unresponsive</li>
              <li>The polling interval being set too high</li>
              <li>WebSocket connection issues</li>
            </ul>
            <p>Try refreshing the page or restarting the application.</p>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showDocDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>


  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import axios from "axios";
import { useClipboard } from "@/composables/useClipboard";
import { useGlobalSnackbar } from "@/composables/useGlobalSnackbar";
import BitcoinLogo from "@/components/BitcoinLogo.vue";
export default {
  name: "About",
  
  components: {
    BitcoinLogo,
  },

  setup() {
    // App information
    const appVersion = ref("0.1.0");
    const releaseDate = ref("2025-08-25");

    // System information
    const systemInfo = ref({
      pythonVersion: "3.11",
      nodeVersion: "18.x",
      osInfo: "Linux",
      uptime: "0d 0h 0m",
    });

    // Documentation dialog
    const showDocDialog = ref(false);
    const activeDoc = ref("user");
    const docDialogTitle = ref("User Guide");

    // Tabs
    const activeTab = ref("bitaxe");

    // Clipboard functionality
    const clipboard = useClipboard();

    // Global snackbar functionality
    const { showSnackbar } = useGlobalSnackbar();

    // Methods
    const fetchSystemInfo = async () => {
      try {
        const response = await axios.get("/api/system/info");
        systemInfo.value = response.data;
      } catch (error) {
        console.error("Error fetching system info:", error);
      }
    };

    const openDocumentation = (docType) => {
      activeDoc.value = docType;

      switch (docType) {
        case "user":
          docDialogTitle.value = "User Guide";
          break;
        case "api":
          docDialogTitle.value = "API Documentation";
          break;
        case "faq":
          docDialogTitle.value = "Frequently Asked Questions";
          break;
        default:
          docDialogTitle.value = "Documentation";
      }

      showDocDialog.value = true;
    };

    // showSnackbar is now provided by the global composable

    const copyDonationAddress = async () => {
      try {
        const result = await clipboard.copyDonationAddress();
        
        if (result.success) {
          showSnackbar(result.message, 'success');
        } else {
          showSnackbar(result.message, 'error');
        }
      } catch (error) {
        console.error('Error copying donation address:', error);
        showSnackbar('Failed to copy donation address. Please copy manually.', 'error');
      }
    };

    // Lifecycle hooks
    onMounted(() => {
      fetchSystemInfo();
    });

    return {
      // State
      appVersion,
      releaseDate,
      systemInfo,
      showDocDialog,
      activeDoc,
      docDialogTitle,
      activeTab,
      clipboard,

      // Methods
      openDocumentation,
      copyDonationAddress,
    };
  },
};
</script>

<style scoped>
.bitcoin-hero {
  padding: var(--spacing-xxl) 0;
  background: linear-gradient(
    135deg,
    var(--color-primary-alpha-10) 0%,
    rgba(247, 147, 26, 0.02) 50%,
    transparent 100%
  );
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-md);
  border: 1px solid var(--color-border-subtle);
}

.bitcoin-hero__logo {
  margin: 0 auto;
}

.bitcoin-hero__title {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-sm);
}

.bitcoin-hero__tagline {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  line-height: 1.4;
  max-width: 600px;
  margin: 0 auto;
  padding: var(--spacing-md);
  background: rgba(247, 147, 26, 0.05);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-warning);
}

.bitcoin-hero__tagline p {
  margin: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.bitcoin-hero__subtitle {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-regular);
  opacity: 0.9;
}

/* Snackbar styling handled globally in main.css */

/* Enhanced card styling */
:deep(.v-card) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
  transition: all var(--transition-normal);
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

/* Outlined cards for features */
:deep(.v-card[outlined]) {
  border: 1px solid var(--color-border);
  background-color: var(--color-surface-variant) !important;
}

:deep(.v-card[outlined]:hover) {
  border-color: var(--color-primary);
  background-color: var(--color-surface) !important;
}

/* List styling */
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

:deep(.v-list-item-icon .v-icon) {
  color: var(--color-primary) !important;
}

/* Tabs styling */
:deep(.v-tabs) {
  background-color: var(--color-surface-secondary) !important;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

:deep(.v-tab) {
  color: var(--color-text-secondary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.v-tab--selected) {
  color: var(--color-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-tab-item) {
  background-color: var(--color-surface) !important;
}

/* Window styling */
:deep(.v-window) {
  background-color: var(--color-surface) !important;
}

:deep(.v-window-item) {
  background-color: var(--color-surface) !important;
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
  font-weight: var(--font-weight-semibold);
}

:deep(.v-dialog .v-card-text) {
  color: var(--color-text-primary) !important;
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

/* Icon styling */
:deep(.v-icon) {
  color: var(--color-primary);
}

/* Divider styling */
:deep(.v-divider) {
  border-color: var(--color-border-subtle) !important;
}

/* Code styling */
:deep(pre) {
  background-color: var(--color-surface-secondary) !important;
  color: var(--color-text-primary) !important;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  font-family: var(--font-family-mono);
}

:deep(code) {
  background-color: var(--color-surface-secondary) !important;
  color: var(--color-primary-light) !important;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
}

/* List styling in dialog content */
:deep(.v-dialog .v-card-text ul) {
  color: var(--color-text-primary);
  padding-left: var(--spacing-lg);
}

:deep(.v-dialog .v-card-text li) {
  margin-bottom: var(--spacing-xs);
  color: var(--color-text-primary);
}

:deep(.v-dialog .v-card-text ol) {
  color: var(--color-text-primary);
  padding-left: var(--spacing-lg);
}

:deep(.v-dialog .v-card-text h3) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-md);
}

:deep(.v-dialog .v-card-text h4) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
}

:deep(.v-dialog .v-card-text h5) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  margin-top: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
}

:deep(.v-dialog .v-card-text p) {
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

/* Responsive adjustments */
@media (max-width: 960px) {
  .bitcoin-hero {
    padding: var(--spacing-xl) 0;
  }

  .bitcoin-hero__title {
    font-size: var(--font-size-h3);
  }

  .bitcoin-hero__tagline {
    max-width: 500px;
    padding: var(--spacing-sm);
  }

  .bitcoin-hero__tagline p {
    font-size: var(--font-size-h6);
  }

  .bitcoin-hero__subtitle {
    font-size: var(--font-size-h4);
  }
}

@media (max-width: 600px) {
  .bitcoin-hero {
    padding: var(--spacing-lg) 0;
  }

  .bitcoin-hero__title {
    font-size: var(--font-size-h4);
  }

  .bitcoin-hero__tagline {
    max-width: 100%;
    padding: var(--spacing-xs);
    margin: 0 var(--spacing-sm);
  }

  .bitcoin-hero__tagline p {
    font-size: var(--font-size-body);
    line-height: 1.3;
  }

  .bitcoin-hero__subtitle {
    font-size: var(--font-size-body);
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
  .bitcoin-hero,
  :deep(.v-card),
  :deep(.v-dialog .v-card) {
    border-width: 2px;
  }

  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }
}
</style>
