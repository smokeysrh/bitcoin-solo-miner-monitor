<template>
  <div class="miner-detail">
    <!-- Loading State -->
    <div v-if="loading && !miner" class="loading-container">
      <v-progress-circular
        indeterminate
        color="primary"
        size="64"
      ></v-progress-circular>
      <p class="mt-4 text-center">Loading miner details...</p>
    </div>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
    </v-alert>

    <!-- Not Found State -->
    <v-alert v-else-if="!loading && !miner" type="warning" class="mb-4">
      Miner not found
    </v-alert>

    <!-- Miner Details - Only render when miner exists -->
    <div v-else-if="miner">
      <!-- Header -->
      <v-row>
        <v-col cols="12" md="8">
          <div class="d-flex align-center">
            <v-btn icon class="mr-4" @click="$router.back()">
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-h4">{{ miner.name }}</h1>
            <v-chip :color="getStatusColor(miner.status)" class="ml-4" dark>
              {{ miner.status }}
            </v-chip>
          </div>
        </v-col>
        <v-col cols="12" md="4" class="d-flex justify-end align-center">
          <v-btn color="primary" class="mr-2" @click="openEditDialog">
            <v-icon left>mdi-pencil</v-icon>
            Edit
          </v-btn>
          <v-btn
            color="warning"
            class="mr-2"
            @click="confirmRestart"
            :disabled="
              miner.status === 'offline' || miner.status === 'restarting'
            "
          >
            <v-icon left>mdi-restart</v-icon>
            Restart
          </v-btn>
          <v-btn color="error" @click="confirmRemove">
            <v-icon left>mdi-delete</v-icon>
            Remove
          </v-btn>
        </v-col>
      </v-row>

      <!-- Summary Cards -->
      <v-row class="mt-4">
        <!-- Hashrate Card -->
        <v-col cols="12" sm="6" md="3">
          <v-card class="mx-auto" color="primary" dark>
            <v-card-text>
              <div class="text-h5 text-center">
                {{ formatHashrate(miner.hashrate) }}
              </div>
              <div class="text-subtitle-1 text-center">Hashrate</div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Temperature Card -->
        <v-col cols="12" sm="6" md="3">
          <v-card
            class="mx-auto"
            :color="getTemperatureColor(miner.temperature)"
            dark
          >
            <v-card-text>
              <div class="text-h5 text-center">
                {{ formatTemperature(miner.temperature) }}
              </div>
              <div class="text-subtitle-1 text-center">Temperature</div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Shares Card -->
        <v-col cols="12" sm="6" md="3">
          <v-card class="mx-auto" color="success" dark>
            <v-card-text>
              <div class="text-h5 text-center">
                {{ miner.shares_accepted || 0 }}
              </div>
              <div class="text-subtitle-1 text-center">Accepted Shares</div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Uptime Card -->
        <v-col cols="12" sm="6" md="3">
          <v-card class="mx-auto" color="info" dark>
            <v-card-text>
              <div class="text-h5 text-center">
                {{ formatUptime(miner.uptime) }}
              </div>
              <div class="text-subtitle-1 text-center">Uptime</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Tabs -->
      <v-card class="mt-4">
        <v-tabs v-model="activeTab" background-color="primary" dark>
          <v-tab>Overview</v-tab>
          <v-tab>Performance</v-tab>
          <v-tab>Pool</v-tab>
          <v-tab>Settings</v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Overview Tab -->
          <v-window-item>
            <v-card flat>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Device Information</v-card-title>
                      <v-card-text>
                        <v-table>
                          <tbody>
                            <tr>
                              <td>Type</td>
                              <td>{{ miner.type }}</td>
                            </tr>
                            <tr>
                              <td>Model</td>
                              <td>{{ getDeviceInfo("model") }}</td>
                            </tr>
                            <tr>
                              <td>IP Address</td>
                              <td>{{ miner.ip_address }}</td>
                            </tr>
                            <tr>
                              <td>Port</td>
                              <td>{{ miner.port || "Default" }}</td>
                            </tr>
                            <tr>
                              <td>Firmware Version</td>
                              <td>{{ getDeviceInfo("firmware_version") }}</td>
                            </tr>
                            <tr>
                              <td>MAC Address</td>
                              <td>{{ getDeviceInfo("mac_address") }}</td>
                            </tr>
                            <tr>
                              <td>Added On</td>
                              <td>{{ formatDate(miner.added_at) }}</td>
                            </tr>
                            <tr>
                              <td>Last Updated</td>
                              <td>{{ formatDate(miner.last_updated) }}</td>
                            </tr>
                          </tbody>
                        </v-table>
                      </v-card-text>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Status Information</v-card-title>
                      <v-card-text>
                        <v-table>
                          <tbody>
                            <tr>
                              <td>Status</td>
                              <td>
                                <v-chip
                                  :color="getStatusColor(miner.status)"
                                  size="small"
                                  dark
                                >
                                  {{ miner.status }}
                                </v-chip>
                              </td>
                            </tr>
                            <tr>
                              <td>Hashrate</td>
                              <td>{{ formatHashrate(miner.hashrate) }}</td>
                            </tr>
                            <tr>
                              <td>Temperature</td>
                              <td>
                                {{ formatTemperature(miner.temperature) }}
                              </td>
                            </tr>
                            <tr>
                              <td>Fan Speed</td>
                              <td>
                                {{
                                  miner.fan_speed
                                    ? `${miner.fan_speed}%`
                                    : "N/A"
                                }}
                              </td>
                            </tr>
                            <tr>
                              <td>Power</td>
                              <td>
                                {{ miner.power ? `${miner.power}W` : "N/A" }}
                              </td>
                            </tr>
                            <tr>
                              <td>Efficiency</td>
                              <td>
                                {{
                                  calculateEfficiency(
                                    miner.hashrate,
                                    miner.power,
                                  )
                                }}
                              </td>
                            </tr>
                            <tr>
                              <td>Accepted Shares</td>
                              <td>{{ miner.shares_accepted || 0 }}</td>
                            </tr>
                            <tr>
                              <td>Rejected Shares</td>
                              <td>{{ miner.shares_rejected || 0 }}</td>
                            </tr>
                            <tr>
                              <td>Hardware Errors</td>
                              <td>{{ miner.hardware_errors || 0 }}</td>
                            </tr>
                            <tr>
                              <td>Uptime</td>
                              <td>{{ formatUptime(miner.uptime) }}</td>
                            </tr>
                          </tbody>
                        </v-table>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- Performance Tab -->
          <v-window-item>
            <v-card flat>
              <v-card-text>
                <v-row>
                  <v-col cols="12">
                    <v-card outlined>
                      <v-card-title>
                        Analytics Preview
                        <v-spacer></v-spacer>
                        <v-btn
                          color="primary"
                          :to="`/analytics?miner=${props.id}`"
                          size="small"
                        >
                          <v-icon left>mdi-chart-line</v-icon>
                          See Full Analytics
                        </v-btn>
                      </v-card-title>
                      <v-card-text>
                        <div class="text-center" v-if="loadingMetrics">
                          <v-progress-circular
                            indeterminate
                            color="primary"
                          ></v-progress-circular>
                          <div class="mt-2">Loading metrics...</div>
                        </div>
                        <div
                          v-else-if="metricsError"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="error"
                            >mdi-alert-circle</v-icon
                          >
                          <div class="mt-3 text-error">
                            {{ metricsError }}
                          </div>
                          <v-btn
                            color="primary"
                            class="mt-3"
                            @click="fetchPreviewMetrics"
                          >
                            Retry
                          </v-btn>
                        </div>
                        <div
                          v-else-if="!hashrateData.length && !temperatureData.length && !powerData.length"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="grey lighten-1"
                            >mdi-chart-line</v-icon
                          >
                          <div class="mt-3">
                            No performance data available yet
                          </div>
                          <div class="text-caption mt-2">
                            Data will appear once metrics are collected
                          </div>
                        </div>
                        <v-row v-else>
                          <v-col cols="12">
                            <div class="text-subtitle-2 mb-2">Hashrate History (Last 6 Hours)</div>
                            <div style="position: relative; height: 200px;">
                              <canvas ref="previewHashrateChart"></canvas>
                            </div>
                          </v-col>
                          <v-col cols="12" md="6">
                            <div class="text-subtitle-2 mb-2">Temperature History</div>
                            <div style="position: relative; height: 150px;">
                              <canvas ref="previewTemperatureChart"></canvas>
                            </div>
                          </v-col>
                          <v-col cols="12" md="6">
                            <div class="text-subtitle-2 mb-2">Power Consumption</div>
                            <div style="position: relative; height: 150px;">
                              <canvas ref="previewPowerChart"></canvas>
                            </div>
                          </v-col>
                        </v-row>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- Pool Tab -->
          <v-window-item>
            <v-card flat>
              <v-card-text>
                <v-row>
                  <v-col cols="12">
                    <v-card outlined>
                      <v-card-title>Pool Information</v-card-title>
                      <v-card-text>
                        <div
                          v-if="!miner.pool_info || !miner.pool_info.length"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="grey lighten-1"
                            >mdi-server-network</v-icon
                          >
                          <div class="mt-3">No pool information available</div>
                        </div>
                        <v-table v-else>
                          <thead>
                            <tr>
                              <th>URL</th>
                              <th>User</th>
                              <th>Status</th>
                              <th>Difficulty</th>
                              <th>Active</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr
                              v-for="(pool, index) in miner.pool_info"
                              :key="index"
                            >
                              <td>{{ pool.url }}:{{ pool.port }}</td>
                              <td>{{ pool.user }}</td>
                              <td>
                                <v-chip
                                  :color="pool.is_active ? 'success' : 'grey'"
                                  size="small"
                                  dark
                                >
                                  {{
                                    pool.status ||
                                    (pool.is_active ? "Active" : "Inactive")
                                  }}
                                </v-chip>
                              </td>
                              <td>{{ pool.difficulty || "N/A" }}</td>
                              <td>
                                <v-icon
                                  :color="pool.is_active ? 'success' : 'grey'"
                                >
                                  {{
                                    pool.is_active ? "mdi-check" : "mdi-close"
                                  }}
                                </v-icon>
                              </td>
                            </tr>
                          </tbody>
                        </v-table>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>

                <v-row class="mt-4">
                  <v-col cols="12">
                    <v-card outlined>
                      <v-card-title>Add Backup Pool</v-card-title>
                      <v-card-text>
                        <v-form ref="poolForm" v-model="poolFormValid">
                          <v-row>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="poolConfig.url"
                                label="Pool URL"
                                hint="e.g., solo.ckpool.org"
                                :rules="[(v) => !!v || 'Pool URL is required']"
                              ></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="poolConfig.port"
                                label="Pool Port"
                                type="number"
                                hint="e.g., 3333"
                                :rules="[(v) => !!v || 'Pool port is required']"
                              ></v-text-field>
                            </v-col>
                          </v-row>
                          <v-row>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="poolConfig.user"
                                label="Worker Username"
                                hint="Your Bitcoin address or worker name"
                                :rules="[
                                  (v) => !!v || 'Worker username is required',
                                ]"
                              ></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="poolConfig.pass"
                                label="Worker Password"
                                hint="Usually 'x' or your worker name"
                              ></v-text-field>
                            </v-col>
                          </v-row>
                          <v-btn
                            color="primary"
                            :disabled="!poolFormValid || updatingPool"
                            :loading="updatingPool"
                            @click="updatePoolConfig"
                          >
                            Add Pool
                          </v-btn>
                        </v-form>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- Settings Tab -->
          <v-window-item>
            <v-card flat>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Miner Settings</v-card-title>
                      <v-card-text>
                        <v-form ref="settingsForm" v-model="settingsFormValid">
                          <v-text-field
                            v-model="minerSettings.name"
                            label="Miner Name"
                            :rules="[(v) => !!v || 'Miner name is required']"
                          ></v-text-field>

                          <v-slider
                            v-model="minerSettings.fan_speed"
                            label="Fan Speed"
                            thumb-label
                            min="0"
                            max="100"
                            :rules="[
                              (v) =>
                                (v >= 0 && v <= 100) ||
                                'Fan speed must be between 0 and 100',
                            ]"
                          ></v-slider>

                          <v-text-field
                            v-model="minerSettings.frequency"
                            label="Frequency (MHz)"
                            type="number"
                            :rules="[
                              (v) =>
                                (v >= 100 && v <= 1500) ||
                                'Frequency must be between 100 and 1500',
                            ]"
                          ></v-text-field>

                          <v-btn
                            color="primary"
                            :disabled="!settingsFormValid || updatingSettings"
                            :loading="updatingSettings"
                            @click="updateMinerSettings"
                          >
                            Update Settings
                          </v-btn>
                        </v-form>
                      </v-card-text>
                    </v-card>
                  </v-col>

                </v-row>
              </v-card-text>
            </v-card>
          </v-window-item>
        </v-window>
      </v-card>
    </div>

    <!-- Edit Miner Dialog -->
    <v-dialog v-model="editDialog" max-width="500px">
      <v-card>
        <v-card-title>Edit Miner</v-card-title>
        <v-card-text>
          <v-form ref="editForm" v-model="editFormValid">
            <v-text-field
              v-model="editMiner.name"
              label="Name"
              required
              :rules="[(v) => !!v || 'Name is required']"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="editDialog = false"> Cancel </v-btn>
          <v-btn
            color="primary"
            text
            @click="saveMinerEdit"
            :disabled="!editFormValid"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Restart Confirmation Dialog -->
    <v-dialog v-model="restartDialog" max-width="400px">
      <v-card>
        <v-card-title>Restart Miner</v-card-title>
        <v-card-text>
          Are you sure you want to restart {{ miner ? miner.name : "" }}?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="restartDialog = false"> Cancel </v-btn>
          <v-btn color="warning" @click="restartMiner"> Restart </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Remove Confirmation Dialog -->
    <v-dialog v-model="removeDialog" max-width="400px">
      <v-card>
        <v-card-title>Remove Miner</v-card-title>
        <v-card-text>
          Are you sure you want to remove {{ miner ? miner.name : "" }}? This
          action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="removeDialog = false"> Cancel </v-btn>
          <v-btn color="error" @click="removeMiner"> Remove </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useMinersStore } from "../stores/miners";
import { useSettingsStore } from "../stores/settings";
import { formatTemperature } from "../utils/formatters";
import { usePollingManager } from "../composables/usePollingManager";
import { Chart, registerables } from "chart.js";
import { addMessageHandler, removeMessageHandler } from "../services/websocket";

// Register Chart.js components
Chart.register(...registerables);

export default {
  name: "MinerDetail",
  props: {
    id: {
      type: String,
      required: true,
    },
  },

  setup(props) {
    const router = useRouter();
    const minersStore = useMinersStore();
    const settingsStore = useSettingsStore();

    // State
    const activeTab = ref(0);
    const loadingMetrics = ref(false);
    const metricsError = ref(null);
    const hashrateData = ref([]);
    const temperatureData = ref([]);
    const powerData = ref([]);
    
    // Chart refs
    const previewHashrateChart = ref(null);
    const previewTemperatureChart = ref(null);
    const previewPowerChart = ref(null);
    
    // Chart instances
    let hashrateChartInstance = null;
    let temperatureChartInstance = null;
    let powerChartInstance = null;

    // Dialogs
    const editDialog = ref(false);
    const restartDialog = ref(false);
    const removeDialog = ref(false);

    // Forms
    const editForm = ref(null);
    const editFormValid = ref(false);
    const editMiner = ref({
      name: "",
    });

    const poolForm = ref(null);
    const poolFormValid = ref(false);
    const poolConfig = ref({
      url: "",
      port: "",
      user: "",
      pass: "",
    });
    const updatingPool = ref(false);

    const settingsForm = ref(null);
    const settingsFormValid = ref(false);
    const minerSettings = ref({
      name: "",
      fan_speed: 50,
      frequency: 0,
    });
    const updatingSettings = ref(false);

    // Set up polling manager
    const { startPolling, stopPolling } = usePollingManager({
      fetchFunction: () => minersStore.fetchMiner(props.id),
      intervalKey: "refresh_interval",
      componentName: "MinerDetail",
      enabled: true,
    });

    // Computed properties
    const miner = computed(() => {
      const minerGetter = minersStore.getMinerById;
      return minerGetter ? minerGetter(props.id) : null;
    });
    const loading = computed(() => minersStore.loading);
    const error = computed(() => minersStore.error);

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

    const formatUptime = (seconds) => {
      if (!seconds) return "N/A";

      const days = Math.floor(seconds / 86400);
      const hours = Math.floor((seconds % 86400) / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);

      let result = "";
      if (days > 0) result += `${days}d `;
      if (hours > 0 || days > 0) result += `${hours}h `;
      result += `${minutes}m`;

      return result;
    };

    const formatDate = (dateString) => {
      if (!dateString) return "N/A";

      try {
        const date = new Date(dateString);
        return date.toLocaleString();
      } catch (error) {
        return dateString;
      }
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

    const calculateEfficiency = (hashrate, power) => {
      // Check if miner already has efficiency calculated by backend
      if (miner.value && miner.value.efficiency && miner.value.efficiency > 0) {
        return `${miner.value.efficiency.toFixed(2)} W/TH`;
      }

      // Fallback: calculate efficiency if not provided by backend
      if (!hashrate || !power || power === 0) return "N/A";

      // Convert hashrate from H/s to TH/s (1 TH = 10^12 H)
      const hashrateInTH = hashrate / 1000000000000;

      if (hashrateInTH === 0) return "N/A";

      // Calculate efficiency as watts per terahash (W/TH)
      // Lower values indicate better efficiency
      const efficiency = power / hashrateInTH;

      return `${efficiency.toFixed(2)} W/TH`;
    };

    const getDeviceInfo = (key) => {
      if (!miner.value) return "N/A";

      if (miner.value[key]) return miner.value[key];

      // Check in device_info if available
      if (miner.value.device_info && miner.value.device_info[key]) {
        return miner.value.device_info[key];
      }

      return "N/A";
    };
    const openEditDialog = () => {
      if (!miner.value) return;

      editMiner.value = {
        name: miner.value.name,
      };

      editDialog.value = true;
    };

    const saveMinerEdit = async () => {
      if (!miner.value) return;

      try {
        await minersStore.updateMiner(miner.value.id, {
          name: editMiner.value.name,
        });

        editDialog.value = false;
      } catch (error) {
        console.error(`Error updating miner ${miner.value.id}:`, error);
      }
    };

    const confirmRestart = () => {
      restartDialog.value = true;
    };

    const restartMiner = async () => {
      if (!miner.value) return;

      try {
        await minersStore.restartMiner(miner.value.id);
        restartDialog.value = false;
      } catch (error) {
        console.error(`Error restarting miner ${miner.value.id}:`, error);
      }
    };

    const confirmRemove = () => {
      removeDialog.value = true;
    };

    const removeMiner = async () => {
      if (!miner.value) return;

      try {
        await minersStore.removeMiner(miner.value.id);
        removeDialog.value = false;
        router.push("/miners");
      } catch (error) {
        console.error(`Error removing miner ${miner.value.id}:`, error);
      }
    };

    const updatePoolConfig = async () => {
      if (!miner.value) return;

      updatingPool.value = true;

      try {
        await minersStore.updateMiner(miner.value.id, {
          settings: {
            pool_url: poolConfig.value.url,
            pool_port: parseInt(poolConfig.value.port),
            pool_user: poolConfig.value.user,
            pool_pass: poolConfig.value.pass,
          },
        });

        // Refresh miner data
        await minersStore.fetchMiner(miner.value.id);
      } catch (error) {
        console.error(
          `Error updating pool config for miner ${miner.value.id}:`,
          error,
        );
      } finally {
        updatingPool.value = false;
      }
    };

    const updateMinerSettings = async () => {
      if (!miner.value) return;

      updatingSettings.value = true;

      try {
        const settings = {
          name: minerSettings.value.name,
          fan_speed: minerSettings.value.fan_speed,
          frequency: minerSettings.value.frequency,
        };

        await minersStore.updateMiner(miner.value.id, {
          name: settings.name,
          settings,
        });

        // Refresh miner data
        await minersStore.fetchMiner(miner.value.id);
      } catch (error) {
        console.error(
          `Error updating settings for miner ${miner.value.id}:`,
          error,
        );
      } finally {
        updatingSettings.value = false;
      }
    };

    const fetchPreviewMetrics = async () => {
      console.log('[fetchPreviewMetrics] Called, miner.value:', miner.value);
      
      if (!miner.value) {
        console.warn('[fetchPreviewMetrics] No miner data available, skipping metrics fetch');
        return;
      }

      if (!miner.value.id) {
        console.error('[fetchPreviewMetrics] Miner has no ID:', miner.value);
        metricsError.value = "Miner ID is missing";
        return;
      }

      loadingMetrics.value = true;
      metricsError.value = null;

      try {
        console.log('[fetchPreviewMetrics] Fetching metrics for miner ID:', miner.value.id);
        
        // Get metrics for the last 6 hours with 15-minute intervals
        const endTime = new Date();
        const startTime = new Date(endTime.getTime() - 6 * 60 * 60 * 1000);

        console.log('[fetchPreviewMetrics] Time range:', {
          start: startTime.toISOString(),
          end: endTime.toISOString(),
          interval: '15m'
        });

        const metrics = await minersStore.fetchMinerMetrics(
          miner.value.id,
          startTime.toISOString(),
          endTime.toISOString(),
          "15m",
        );

        console.log('[fetchPreviewMetrics] Metrics received:', metrics?.length || 0, 'data points');

        // Process metrics data for charts
        processMetricsData(metrics);
        
        // Only try to render if we have data
        if (hashrateData.value.length > 0 || temperatureData.value.length > 0 || powerData.value.length > 0) {
          // Wait for DOM to update with the new data
          await nextTick();
          await nextTick();
          
          // Try to render charts with retry logic
          let retries = 0;
          const maxRetries = 5;
          const tryRender = async () => {
            // Check if all required refs exist and are valid DOM elements
            const hasValidRefs = 
              previewHashrateChart.value instanceof HTMLCanvasElement &&
              previewTemperatureChart.value instanceof HTMLCanvasElement &&
              previewPowerChart.value instanceof HTMLCanvasElement;
            
            if (hasValidRefs) {
              // Extra safety: ensure canvases are actually in the DOM and visible
              const allVisible = 
                previewHashrateChart.value.offsetParent !== null &&
                previewTemperatureChart.value.offsetParent !== null &&
                previewPowerChart.value.offsetParent !== null;
              
              if (allVisible) {
                renderPreviewCharts();
              } else if (retries < maxRetries) {
                retries++;
                console.log(`Canvas elements not visible yet, retry ${retries}/${maxRetries}`);
                setTimeout(tryRender, 150);
              } else {
                console.warn('Failed to render charts: canvas elements not visible after max retries');
              }
            } else if (retries < maxRetries) {
              retries++;
              console.log(`Canvas refs not ready, retry ${retries}/${maxRetries}`);
              setTimeout(tryRender, 150);
            } else {
              console.warn('Failed to render charts: refs not ready after max retries');
            }
          };
          tryRender();
        }
      } catch (error) {
        console.error(
          `[fetchPreviewMetrics] Error fetching metrics for miner ${miner.value?.id}:`,
          error,
        );
        
        // Check if it's a 404 error
        if (error.response?.status === 404) {
          metricsError.value = "Miner not found. The miner may still be initializing.";
        } else {
          metricsError.value = "Failed to load metrics data. Please try again.";
        }
      } finally {
        loadingMetrics.value = false;
      }
    };

    const processMetricsData = (metrics) => {
      if (!metrics || metrics.length === 0) {
        hashrateData.value = [];
        temperatureData.value = [];
        powerData.value = [];
        return;
      }

      // Process hashrate data - API returns metric_type, time_bucket, and avg_value
      hashrateData.value = metrics
        .filter((m) => m.metric_type === "hashrate")
        .map((m) => ({
          time: new Date(m.time_bucket),
          value: m.avg_value,
        }));

      // Process temperature data
      temperatureData.value = metrics
        .filter((m) => m.metric_type === "temperature")
        .map((m) => ({
          time: new Date(m.time_bucket),
          value: m.avg_value,
        }));

      // Process power data
      powerData.value = metrics
        .filter((m) => m.metric_type === "power")
        .map((m) => ({
          time: new Date(m.time_bucket),
          value: m.avg_value,
        }));
      
      console.log('Processed metrics data:', {
        hashrate: hashrateData.value.length,
        temperature: temperatureData.value.length,
        power: powerData.value.length
      });
    };
    
    const renderPreviewCharts = () => {
      console.log('=== renderPreviewCharts CALLED ===');
      
      // Validate canvas refs are HTMLCanvasElements before proceeding
      if (!(previewHashrateChart.value instanceof HTMLCanvasElement) ||
          !(previewTemperatureChart.value instanceof HTMLCanvasElement) ||
          !(previewPowerChart.value instanceof HTMLCanvasElement)) {
        console.warn("Canvas refs not available or not valid HTMLCanvasElements");
        return;
      }
      
      // Ensure canvases are in the DOM and visible
      if (previewHashrateChart.value.offsetParent === null ||
          previewTemperatureChart.value.offsetParent === null ||
          previewPowerChart.value.offsetParent === null) {
        console.warn("Canvas elements are not visible in the DOM");
        return;
      }
      
      // Destroy existing chart instances safely
      try {
        if (hashrateChartInstance) {
          console.log('Destroying existing hashrate chart instance');
          hashrateChartInstance.destroy();
          hashrateChartInstance = null;
        }
        if (temperatureChartInstance) {
          console.log('Destroying existing temperature chart instance');
          temperatureChartInstance.destroy();
          temperatureChartInstance = null;
        }
        if (powerChartInstance) {
          console.log('Destroying existing power chart instance');
          powerChartInstance.destroy();
          powerChartInstance = null;
        }
      } catch (error) {
        console.error('Error destroying chart instances:', error);
      }
      
      // Log canvas dimensions before rendering
      console.log('Canvas dimensions BEFORE rendering:', {
        hashrate: {
          width: previewHashrateChart.value.width,
          height: previewHashrateChart.value.height,
          clientWidth: previewHashrateChart.value.clientWidth,
          clientHeight: previewHashrateChart.value.clientHeight,
          offsetWidth: previewHashrateChart.value.offsetWidth,
          offsetHeight: previewHashrateChart.value.offsetHeight,
          style: previewHashrateChart.value.style.cssText
        },
        temperature: {
          width: previewTemperatureChart.value.width,
          height: previewTemperatureChart.value.height,
          clientWidth: previewTemperatureChart.value.clientWidth,
          clientHeight: previewTemperatureChart.value.clientHeight
        },
        power: {
          width: previewPowerChart.value.width,
          height: previewPowerChart.value.height,
          clientWidth: previewPowerChart.value.clientWidth,
          clientHeight: previewPowerChart.value.clientHeight
        }
      });
      
      // Render hashrate chart
      if (hashrateData.value.length > 0) {
        const hashrateLabels = hashrateData.value.map(d => 
          d.time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        );
        const hashrateValues = hashrateData.value.map(d => d.value);
        
        console.log('Creating hashrate chart with data points:', hashrateValues.length);
        hashrateChartInstance = new Chart(previewHashrateChart.value, {
          type: 'line',
          data: {
            labels: hashrateLabels,
            datasets: [{
              label: 'Hashrate',
              data: hashrateValues,
              borderColor: 'rgba(75, 192, 192, 1)',
              backgroundColor: 'rgba(75, 192, 192, 0.2)',
              fill: true,
              tension: 0.4,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                callbacks: {
                  label: (context) => {
                    return `${formatHashrate(context.parsed.y)}`;
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: (value) => formatHashrate(value)
                }
              }
            }
          }
        });
        console.log('Hashrate chart created, canvas dimensions AFTER:', {
          width: previewHashrateChart.value.width,
          height: previewHashrateChart.value.height,
          clientWidth: previewHashrateChart.value.clientWidth,
          clientHeight: previewHashrateChart.value.clientHeight,
          style: previewHashrateChart.value.style.cssText
        });
      }
      
      // Render temperature chart
      if (temperatureData.value.length > 0) {
        const tempLabels = temperatureData.value.map(d => 
          d.time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        );
        const tempValues = temperatureData.value.map(d => d.value);
        
        console.log('Creating temperature chart with data points:', tempValues.length);
        temperatureChartInstance = new Chart(previewTemperatureChart.value, {
          type: 'line',
          data: {
            labels: tempLabels,
            datasets: [{
              label: 'Temperature',
              data: tempValues,
              borderColor: 'rgba(255, 99, 132, 1)',
              backgroundColor: 'rgba(255, 99, 132, 0.2)',
              fill: true,
              tension: 0.4,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                callbacks: {
                  label: (context) => {
                    return `${context.parsed.y}°C`;
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: false,
                ticks: {
                  callback: (value) => `${value}°C`
                }
              }
            }
          }
        });
        console.log('Temperature chart created');
      }
      
      // Render power chart
      if (powerData.value.length > 0) {
        const powerLabels = powerData.value.map(d => 
          d.time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        );
        const powerValues = powerData.value.map(d => d.value);
        
        console.log('Creating power chart with data points:', powerValues.length);
        powerChartInstance = new Chart(previewPowerChart.value, {
          type: 'line',
          data: {
            labels: powerLabels,
            datasets: [{
              label: 'Power',
              data: powerValues,
              borderColor: 'rgba(255, 206, 86, 1)',
              backgroundColor: 'rgba(255, 206, 86, 0.2)',
              fill: true,
              tension: 0.4,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                callbacks: {
                  label: (context) => {
                    return `${context.parsed.y}W`;
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: (value) => `${value}W`
                }
              }
            }
          }
        });
        console.log('Power chart created');
      }
      
      console.log('=== renderPreviewCharts COMPLETE ===');
    };

    // WebSocket message handler - DISABLED for preview (static snapshot only)
    // The analytics preview shows a static 6-hour snapshot, not real-time updates
    // For real-time charts, users should navigate to the full Analytics page
    const handleMetricsUpdate = (message) => {
      // Intentionally disabled - preview charts are static snapshots
      return;
    };
    
    // REMOVED: updatePreviewCharts() function
    // Preview charts are now static snapshots and don't update in real-time
    // This prevents the page from continuously growing as new data arrives
    
    // Lifecycle hooks
    onMounted(async () => {
      console.log('[MinerDetail] onMounted - Starting initialization for miner:', props.id);
      
      // Fetch miner data and wait for it to complete
      try {
        await minersStore.fetchMiner(props.id);
        console.log('[MinerDetail] Miner data fetched, miner.value:', miner.value);
      } catch (error) {
        console.error('[MinerDetail] Error fetching miner:', error);
      }

      // Wait for next tick to ensure reactive updates have propagated
      await nextTick();

      // Initialize form data if miner exists
      if (miner.value) {
        console.log('[MinerDetail] Miner exists, initializing forms');
        
        // Initialize settings form
        minerSettings.value = {
          name: miner.value.name,
          fan_speed: miner.value.fan_speed || 50,
          frequency: miner.value.frequency || 0,
        };

        // Initialize pool form if pool info is available
        if (miner.value.pool_info && miner.value.pool_info.length > 0) {
          const activePool =
            miner.value.pool_info.find((p) => p.is_active) ||
            miner.value.pool_info[0];

          poolConfig.value = {
            url: activePool.url || "",
            port: activePool.port || "",
            user: activePool.user || "",
            pass: activePool.pass || "",
          };
        }

        // Fetch preview metrics only after miner is confirmed loaded
        console.log('[MinerDetail] Fetching preview metrics for miner:', miner.value.id);
        // Don't await - let it load in the background
        fetchPreviewMetrics();
      } else {
        console.warn('[MinerDetail] Miner not found after fetch attempt');
      }

      // WebSocket metrics updates disabled for preview (static snapshot only)
      // addMessageHandler(handleMetricsUpdate);

      // Start polling with usePollingManager
      startPolling();
    });
    
    // Cleanup on unmount
    onUnmounted(() => {
      // WebSocket handler not registered, so no need to remove
      // removeMessageHandler(handleMetricsUpdate);
      
      // Destroy chart instances
      if (hashrateChartInstance) hashrateChartInstance.destroy();
      if (temperatureChartInstance) temperatureChartInstance.destroy();
      if (powerChartInstance) powerChartInstance.destroy();
    });

    // Watch for miner changes
    watch(
      () => miner.value,
      (newMiner) => {
        if (newMiner) {
          // Update settings form
          minerSettings.value = {
            name: newMiner.name,
            fan_speed: newMiner.fan_speed || 50,
            frequency: newMiner.frequency || 0,
          };

          // Update pool form if pool info is available
          if (newMiner.pool_info && newMiner.pool_info.length > 0) {
            const activePool =
              newMiner.pool_info.find((p) => p.is_active) ||
              newMiner.pool_info[0];

            poolConfig.value = {
              url: activePool.url || "",
              port: activePool.port || "",
              user: activePool.user || "",
              pass: activePool.pass || "",
            };
          }
        }
      },
    );
    
    // Watch for tab changes to render charts when Performance tab is selected
    watch(
      () => activeTab.value,
      async (newTab, oldTab) => {
        console.log(`Tab changed from ${oldTab} to ${newTab}`);
        // Performance tab is index 1
        if (newTab === 1 && hashrateData.value.length > 0) {
          console.log('Switching to Performance tab, will render charts after DOM update');
          // Wait for DOM to update
          await nextTick();
          await nextTick();
          
          // Try to render charts
          setTimeout(() => {
            if (previewHashrateChart.value && previewTemperatureChart.value && previewPowerChart.value) {
              console.log('Canvas refs available, rendering charts');
              renderPreviewCharts();
            } else {
              console.warn('Canvas refs not available after tab switch');
            }
          }, 100);
        }
      },
    );

    return {
      // State
      miner,
      loading,
      error,
      activeTab,
      loadingMetrics,
      metricsError,
      hashrateData,
      temperatureData,
      powerData,
      
      // Chart refs
      previewHashrateChart,
      previewTemperatureChart,
      previewPowerChart,

      // Dialogs
      editDialog,
      restartDialog,
      removeDialog,

      // Forms
      editForm,
      editFormValid,
      editMiner,
      poolForm,
      poolFormValid,
      poolConfig,
      updatingPool,
      settingsForm,
      settingsFormValid,
      minerSettings,
      updatingSettings,

      // Methods
      formatHashrate,
      formatTemperature,
      formatUptime,
      formatDate,
      getStatusColor,
      getTemperatureColor,
      calculateEfficiency,
      getDeviceInfo,
      openEditDialog,
      saveMinerEdit,
      confirmRestart,
      restartMiner,
      confirmRemove,
      removeMiner,
      updatePoolConfig,
      updateMinerSettings,
      fetchPreviewMetrics,
      
      // Props
      props,
    };
  },
};
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
