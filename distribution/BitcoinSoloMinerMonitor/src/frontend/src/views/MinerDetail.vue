<template>
  <div>
    <!-- Loading State -->
    <v-skeleton-loader
      v-if="loading && !miner"
      type="card, list-item-three-line, card-heading, card-heading"
      class="mx-auto"
    ></v-skeleton-loader>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
    </v-alert>

    <!-- Not Found State -->
    <v-alert v-else-if="!miner" type="warning" class="mb-4">
      Miner not found
    </v-alert>

    <!-- Miner Details -->
    <template v-else>
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

        <v-tabs-items v-model="activeTab">
          <!-- Overview Tab -->
          <v-tab-item>
            <v-card flat>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Device Information</v-card-title>
                      <v-card-text>
                        <v-simple-table>
                          <template v-slot:default>
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
                          </template>
                        </v-simple-table>
                      </v-card-text>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Status Information</v-card-title>
                      <v-card-text>
                        <v-simple-table>
                          <template v-slot:default>
                            <tbody>
                              <tr>
                                <td>Status</td>
                                <td>
                                  <v-chip
                                    :color="getStatusColor(miner.status)"
                                    small
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
                          </template>
                        </v-simple-table>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-tab-item>

          <!-- Performance Tab -->
          <v-tab-item>
            <v-card flat>
              <v-card-text>
                <v-row>
                  <v-col cols="12">
                    <v-card outlined>
                      <v-card-title>Hashrate History</v-card-title>
                      <v-card-text>
                        <div class="text-center" v-if="loadingMetrics">
                          <v-progress-circular
                            indeterminate
                            color="primary"
                          ></v-progress-circular>
                          <div class="mt-2">Loading metrics...</div>
                        </div>
                        <div
                          v-else-if="!hashrateData.length"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="grey lighten-1"
                            >mdi-chart-line</v-icon
                          >
                          <div class="mt-3">
                            No performance data available yet
                          </div>
                        </div>
                        <div v-else style="height: 300px">
                          <!-- Placeholder for chart component -->
                          <div class="text-center">
                            Hashrate chart will be displayed here
                          </div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>

                <v-row class="mt-4">
                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Temperature History</v-card-title>
                      <v-card-text>
                        <div class="text-center" v-if="loadingMetrics">
                          <v-progress-circular
                            indeterminate
                            color="primary"
                          ></v-progress-circular>
                          <div class="mt-2">Loading metrics...</div>
                        </div>
                        <div
                          v-else-if="!temperatureData.length"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="grey lighten-1"
                            >mdi-thermometer</v-icon
                          >
                          <div class="mt-3">
                            No temperature data available yet
                          </div>
                        </div>
                        <div v-else style="height: 200px">
                          <!-- Placeholder for chart component -->
                          <div class="text-center">
                            Temperature chart will be displayed here
                          </div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Power Consumption</v-card-title>
                      <v-card-text>
                        <div class="text-center" v-if="loadingMetrics">
                          <v-progress-circular
                            indeterminate
                            color="primary"
                          ></v-progress-circular>
                          <div class="mt-2">Loading metrics...</div>
                        </div>
                        <div
                          v-else-if="!powerData.length"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="grey lighten-1"
                            >mdi-flash</v-icon
                          >
                          <div class="mt-3">No power data available yet</div>
                        </div>
                        <div v-else style="height: 200px">
                          <!-- Placeholder for chart component -->
                          <div class="text-center">
                            Power chart will be displayed here
                          </div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-tab-item>

          <!-- Pool Tab -->
          <v-tab-item>
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
                        <v-simple-table v-else>
                          <template v-slot:default>
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
                                    small
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
                          </template>
                        </v-simple-table>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>

                <v-row class="mt-4">
                  <v-col cols="12">
                    <v-card outlined>
                      <v-card-title>Update Pool Configuration</v-card-title>
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
                            Update Pool Configuration
                          </v-btn>
                        </v-form>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-tab-item>

          <!-- Settings Tab -->
          <v-tab-item>
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
                            v-if="supportsFanControl"
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
                            v-if="supportsFrequencyControl"
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

                  <v-col cols="12" md="6">
                    <v-card outlined>
                      <v-card-title>Supported Features</v-card-title>
                      <v-card-text>
                        <v-chip-group column>
                          <v-chip
                            v-for="feature in supportedFeatures"
                            :key="feature"
                            color="primary"
                            outlined
                          >
                            {{ formatFeatureName(feature) }}
                          </v-chip>
                        </v-chip-group>

                        <div
                          v-if="!supportedFeatures.length"
                          class="text-center pa-5"
                        >
                          <v-icon size="64" color="grey lighten-1"
                            >mdi-cog</v-icon
                          >
                          <div class="mt-3">
                            No feature information available
                          </div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-tab-item>
        </v-tabs-items>
      </v-card>
    </template>

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
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useMinersStore } from "../stores/miners";
import { useSettingsStore } from "../stores/settings";
import { formatTemperature } from "../utils/formatters";

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
    const hashrateData = ref([]);
    const temperatureData = ref([]);
    const powerData = ref([]);

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

    // Refresh interval
    let refreshInterval = null;

    // Computed properties
    const miner = computed(() => minersStore.getMinerById(props.id));
    const loading = computed(() => minersStore.loading);
    const error = computed(() => minersStore.error);

    const supportedFeatures = computed(() => {
      if (!miner.value) return [];
      return miner.value.supported_features || [];
    });

    const supportsFanControl = computed(() => {
      return supportedFeatures.value.includes("fan_control");
    });

    const supportsFrequencyControl = computed(() => {
      return supportedFeatures.value.includes("frequency_control");
    });

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
      if (!hashrate || !power || power === 0) return "N/A";

      // Convert to TH/s per watt
      const efficiency = hashrate / power / 1000000000;

      return `${efficiency.toFixed(6)} TH/s/W`;
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

    const formatFeatureName = (feature) => {
      return feature
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
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
        };

        if (supportsFanControl.value) {
          settings.fan_speed = minerSettings.value.fan_speed;
        }

        if (supportsFrequencyControl.value) {
          settings.frequency = minerSettings.value.frequency;
        }

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

    const fetchMetrics = async () => {
      if (!miner.value) return;

      loadingMetrics.value = true;

      try {
        // Get metrics for the last 24 hours
        const endTime = new Date();
        const startTime = new Date(endTime.getTime() - 24 * 60 * 60 * 1000);

        const metrics = await minersStore.fetchMinerMetrics(
          miner.value.id,
          startTime.toISOString(),
          endTime.toISOString(),
          "5m",
        );

        // Process metrics data for charts
        processMetricsData(metrics);
      } catch (error) {
        console.error(
          `Error fetching metrics for miner ${miner.value.id}:`,
          error,
        );
      } finally {
        loadingMetrics.value = false;
      }
    };

    const processMetricsData = (metrics) => {
      // Process hashrate data
      hashrateData.value = metrics
        .filter((m) => m.field === "hashrate")
        .map((m) => ({
          time: new Date(m.time),
          value: m.value,
        }));

      // Process temperature data
      temperatureData.value = metrics
        .filter((m) => m.field === "temperature")
        .map((m) => ({
          time: new Date(m.time),
          value: m.value,
        }));

      // Process power data
      powerData.value = metrics
        .filter((m) => m.field === "power")
        .map((m) => ({
          time: new Date(m.time),
          value: m.value,
        }));
    };

    // Lifecycle hooks
    onMounted(async () => {
      // Fetch miner data
      await minersStore.fetchMiner(props.id);

      // Initialize form data if miner exists
      if (miner.value) {
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

        // Fetch metrics
        fetchMetrics();
      }

      // Set up refresh interval
      const refreshTime = settingsStore.settings.refresh_interval * 1000;
      refreshInterval = setInterval(async () => {
        await minersStore.fetchMiner(props.id);
      }, refreshTime);
    });

    onUnmounted(() => {
      // Clear refresh interval
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
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

    return {
      // State
      miner,
      loading,
      error,
      activeTab,
      loadingMetrics,
      hashrateData,
      temperatureData,
      powerData,

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

      // Computed
      supportedFeatures,
      supportsFanControl,
      supportsFrequencyControl,

      // Methods
      formatHashrate,
      formatTemperature,
      formatUptime,
      formatDate,
      getStatusColor,
      getTemperatureColor,
      calculateEfficiency,
      getDeviceInfo,
      formatFeatureName,
      openEditDialog,
      saveMinerEdit,
      confirmRestart,
      restartMiner,
      confirmRemove,
      removeMiner,
      updatePoolConfig,
      updateMinerSettings,
    };
  },
};
</script>
