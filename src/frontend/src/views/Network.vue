<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Network Topology</h1>
      </v-col>
    </v-row>

    <!-- Network Controls -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Network Controls</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6">
                <v-select
                  v-model="layoutType"
                  :items="layoutOptions"
                  item-title="text"
                  item-value="value"
                  label="Layout Type"
                  @change="updateNetworkLayout"
                ></v-select>
              </v-col>
              <v-col cols="12" sm="6">
                <v-btn-toggle
                  v-model="groupByType"
                  mandatory
                  @change="updateNetworkLayout"
                >
                  <v-btn :value="true"> Group by Type </v-btn>
                  <v-btn :value="false"> No Grouping </v-btn>
                </v-btn-toggle>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-btn
                  color="primary"
                  @click="refreshNetwork"
                  :loading="loading"
                >
                  <v-icon left>mdi-refresh</v-icon>
                  Refresh Network
                </v-btn>
                <v-btn
                  class="ml-2"
                  color="secondary"
                  @click="exportNetworkImage"
                >
                  <v-icon left>mdi-download</v-icon>
                  Export Image
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Network Statistics</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="6">
                <div class="text-subtitle-1">Total Miners:</div>
                <div class="text-h5">{{ miners.length }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-1">Online Miners:</div>
                <div class="text-h5">{{ onlineMiners.length }}</div>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="6">
                <div class="text-subtitle-1">Offline Miners:</div>
                <div class="text-h5">{{ offlineMiners.length }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-1">Total Hashrate:</div>
                <div class="text-h5">{{ formatHashrate(totalHashrate) }}</div>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="6">
                <div class="text-subtitle-1">Unique Pools:</div>
                <div class="text-h5">{{ uniquePools.length }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-subtitle-1">Avg Pool Latency:</div>
                <div class="text-h5" :style="{ color: getPoolLatencyColor(averagePoolLatency) }">
                  {{ averagePoolLatency !== null ? `${averagePoolLatency.toFixed(1)} ms` : 'N/A' }}
                </div>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <div class="text-subtitle-1">Miner Types:</div>
                <v-chip-group>
                  <v-chip
                    v-for="(count, type) in minerTypeCount"
                    :key="type"
                    :color="getMinerTypeColor(type)"
                    text-color="white"
                  >
                    {{ type }}: {{ count }}
                  </v-chip>
                </v-chip-group>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Network Health -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Network Health
            <v-spacer></v-spacer>
            <v-chip
              v-if="networkHealthLoading"
              color="info"
              size="small"
            >
              <v-progress-circular
                indeterminate
                size="16"
                width="2"
                class="mr-2"
              ></v-progress-circular>
              Loading...
            </v-chip>
          </v-card-title>
          <v-card-text>
            <v-row v-if="!networkHealthLoading && networkHealthData && Object.keys(networkHealthData).length > 0">
              <v-col cols="12" md="3">
                <div class="text-subtitle-1 d-flex align-center">
                  Avg Miner Latency:
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon 
                        v-bind="props"
                        size="small" 
                        class="ml-1"
                        color="info"
                      >
                        mdi-information-outline
                      </v-icon>
                    </template>
                    <div class="pa-2" style="max-width: 300px;">
                      <strong>Miner Latency</strong><br>
                      Time it takes to communicate with your miners. Lower is better for solo mining as it reduces the chance of stale shares and improves your ability to quickly submit valid blocks to the network.
                    </div>
                  </v-tooltip>
                </div>
                <div class="text-h5" :style="{ color: getLatencyColor(averageMinerLatency) }">
                  {{ averageMinerLatency !== null ? `${averageMinerLatency.toFixed(1)} ms` : 'N/A' }}
                </div>
              </v-col>
              <v-col cols="12" md="3">
                <div class="text-subtitle-1 d-flex align-center">
                  Avg Pool Latency:
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon 
                        v-bind="props"
                        size="small" 
                        class="ml-1"
                        color="info"
                      >
                        mdi-information-outline
                      </v-icon>
                    </template>
                    <div class="pa-2" style="max-width: 300px;">
                      <strong>Pool Latency</strong><br>
                      Time to reach your mining pool or Bitcoin node. Critical for solo mining - high latency can cause you to mine on stale blocks, wasting hashpower and reducing your chances of finding valid blocks.
                    </div>
                  </v-tooltip>
                </div>
                <div class="text-h5" :style="{ color: getPoolLatencyColor(averagePoolLatency) }">
                  {{ averagePoolLatency !== null ? `${averagePoolLatency.toFixed(1)} ms` : 'N/A' }}
                </div>
                <div v-if="unreachablePoolsCount > 0" class="text-caption" style="color: #E53935">
                  {{ unreachablePoolsCount }} unreachable
                </div>
              </v-col>
              <v-col cols="12" md="3">
                <div class="text-subtitle-1 d-flex align-center">
                  Avg Total Path:
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon 
                        v-bind="props"
                        size="small" 
                        class="ml-1"
                        color="info"
                      >
                        mdi-information-outline
                      </v-icon>
                    </template>
                    <div class="pa-2" style="max-width: 300px;">
                      <strong>Total Path Latency</strong><br>
                      Combined time from your device to miners to pool/node. This represents the complete round-trip time for mining operations. Lower values mean faster block template updates and share submissions.
                    </div>
                  </v-tooltip>
                </div>
                <div class="text-h5" :style="{ color: getLatencyColor(averageTotalPathLatency) }">
                  {{ averageTotalPathLatency !== null ? `${averageTotalPathLatency.toFixed(1)} ms` : 'N/A' }}
                </div>
              </v-col>
              <v-col cols="12" md="3">
                <div class="text-subtitle-1 d-flex align-center">
                  Healthy Miners:
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon 
                        v-bind="props"
                        size="small" 
                        class="ml-1"
                        color="info"
                      >
                        mdi-information-outline
                      </v-icon>
                    </template>
                    <div class="pa-2" style="max-width: 300px;">
                      <strong>Healthy Miners</strong><br>
                      Number of miners with good network performance (low latency, minimal packet loss). Healthy miners maximize your solo mining efficiency by ensuring optimal communication with the Bitcoin network.
                    </div>
                  </v-tooltip>
                </div>
                <div class="text-h5" style="color: #43A047">
                  {{ healthyMinersCount }} / {{ networkHealthData ? Object.keys(networkHealthData).length : 0 }}
                </div>
              </v-col>
            </v-row>
            <v-row v-if="!networkHealthLoading && networkHealthData && Object.keys(networkHealthData).length > 0" class="mt-2">
              <v-col cols="12" md="6">
                <div class="text-subtitle-1 d-flex align-center">
                  Average Packet Loss:
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon 
                        v-bind="props"
                        size="small" 
                        class="ml-1"
                        color="info"
                      >
                        mdi-information-outline
                      </v-icon>
                    </template>
                    <div class="pa-2" style="max-width: 300px;">
                      <strong>Packet Loss</strong><br>
                      Percentage of network packets that fail to reach their destination. Any packet loss can cause missed block templates or failed share submissions, directly impacting your solo mining success rate.
                    </div>
                  </v-tooltip>
                </div>
                <div class="text-h6" :style="{ color: getPacketLossColor(averagePacketLoss) }">
                  {{ averagePacketLoss !== null ? `${averagePacketLoss.toFixed(2)}%` : 'N/A' }}
                </div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-subtitle-1 d-flex align-center">
                  Average Jitter:
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props }">
                      <v-icon 
                        v-bind="props"
                        size="small" 
                        class="ml-1"
                        color="info"
                      >
                        mdi-information-outline
                      </v-icon>
                    </template>
                    <div class="pa-2" style="max-width: 300px;">
                      <strong>Network Jitter</strong><br>
                      Variation in network latency over time. High jitter indicates unstable network conditions that can cause inconsistent mining performance and timing issues with block submissions.
                    </div>
                  </v-tooltip>
                </div>
                <div class="text-h6" :style="{ color: getJitterColor(averageJitter) }">
                  {{ averageJitter !== null ? `${averageJitter.toFixed(1)} ms` : 'N/A' }}
                </div>
              </v-col>
            </v-row>
            <v-row v-if="!networkHealthLoading && uniquePools.length > 0" class="mt-2">
              <v-col cols="12">
                <div class="text-subtitle-2 mb-2">Pool Connections:</div>
                <v-chip-group>
                  <v-chip 
                    v-for="pool in uniquePools" 
                    :key="pool.url"
                    :color="getPoolLatencyChipColor(pool.latency_ms)"
                    text-color="white"
                    size="small"
                  >
                    <v-icon 
                      v-if="pool.status === 'unreachable'" 
                      start 
                      size="small"
                    >
                      mdi-close-network
                    </v-icon>
                    <v-icon 
                      v-else-if="pool.status === 'critical'" 
                      start 
                      size="small"
                    >
                      mdi-alert-circle
                    </v-icon>
                    <v-icon 
                      v-else-if="pool.status === 'warning'" 
                      start 
                      size="small"
                    >
                      mdi-alert
                    </v-icon>
                    {{ pool.url }}{{ pool.port ? `:${pool.port}` : '' }} - 
                    {{ pool.latency_ms !== null ? `${pool.latency_ms.toFixed(1)}ms` : 'Unreachable' }}
                    ({{ pool.minerCount }} {{ pool.minerCount === 1 ? 'miner' : 'miners' }})
                  </v-chip>
                </v-chip-group>
              </v-col>
            </v-row>
            <v-row v-else-if="!networkHealthLoading">
              <v-col cols="12" class="text-center">
                <p class="text-subtitle-1">No network health data available</p>
                <p class="text-caption">Network health monitoring will update automatically</p>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Network Visualization -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Network Visualization</v-card-title>
          <v-card-text>
            <div
              v-if="loading"
              class="d-flex justify-center align-center"
              style="height: 600px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="miners.length === 0"
              class="d-flex justify-center align-center"
              style="height: 600px"
            >
              <p class="text-subtitle-1">No miners found in the network</p>
            </div>
            <div
              v-else
              id="network-container"
              style="height: 600px; border: 1px solid #ccc"
            ></div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Miner Details Dialog -->
    <v-dialog 
      v-model="showMinerDetails" 
      max-width="700px"
      scrollable
      :attach="false"
    >
      <v-card v-if="selectedMiner">
        <v-card-title>
          {{
            selectedMiner.name ||
            `${selectedMiner.type} (${selectedMiner.ip_address})`
          }}
          <v-spacer></v-spacer>
          <v-chip :color="getStatusColor(selectedMiner.status)" dark small>
            {{ selectedMiner.status }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <v-table>
            <tbody>
              <tr>
                <td><strong>ID:</strong></td>
                <td>{{ selectedMiner.id }}</td>
              </tr>
              <tr>
                <td><strong>Type:</strong></td>
                <td>{{ selectedMiner.type }}</td>
              </tr>
              <tr>
                <td><strong>IP Address:</strong></td>
                <td>{{ selectedMiner.ip_address }}</td>
              </tr>
              <tr>
                <td><strong>Port:</strong></td>
                <td>{{ selectedMiner.port || "Default" }}</td>
              </tr>
              <tr>
                <td><strong>Hashrate:</strong></td>
                <td>{{ formatHashrate(selectedMiner.hashrate) }}</td>
              </tr>
              <tr>
                <td><strong>Temperature:</strong></td>
                <td>{{ formatTemperature(selectedMiner.temperature) }}</td>
              </tr>
              <tr>
                <td><strong>Uptime:</strong></td>
                <td>{{ formatUptime(selectedMiner.uptime) }}</td>
              </tr>
              <tr>
                <td><strong>Last Seen:</strong></td>
                <td>{{ formatDate(selectedMiner.last_seen) }}</td>
              </tr>
            </tbody>
          </v-table>
          
          <!-- Network Health Section -->
          <div v-if="getMinerNetworkHealth(selectedMiner.id)" class="mt-4">
            <v-divider class="mb-3"></v-divider>
            <div class="text-subtitle-1 mb-2"><strong>Network Health</strong></div>
            <v-table density="compact">
              <tbody>
                <tr>
                  <td><strong>Miner Latency:</strong></td>
                  <td :style="{ color: getLatencyColor(getMinerNetworkHealth(selectedMiner.id).miner_latency_ms) }">
                    {{ getMinerNetworkHealth(selectedMiner.id).miner_latency_ms !== null 
                       ? `${getMinerNetworkHealth(selectedMiner.id).miner_latency_ms.toFixed(1)} ms` 
                       : 'N/A' }}
                  </td>
                </tr>
                <tr v-if="getMinerNetworkHealth(selectedMiner.id).pool_latency">
                  <td><strong>Pool:</strong></td>
                  <td>
                    {{ getMinerNetworkHealth(selectedMiner.id).pool_latency.url }}{{ getMinerNetworkHealth(selectedMiner.id).pool_latency.port ? `:${getMinerNetworkHealth(selectedMiner.id).pool_latency.port}` : '' }}
                  </td>
                </tr>
                <tr v-if="getMinerNetworkHealth(selectedMiner.id).pool_latency">
                  <td><strong>Pool Latency:</strong></td>
                  <td>
                    <span :style="{ color: getPoolLatencyColor(getMinerNetworkHealth(selectedMiner.id).pool_latency.latency_ms) }">
                      {{ getMinerNetworkHealth(selectedMiner.id).pool_latency.latency_ms !== null 
                         ? `${getMinerNetworkHealth(selectedMiner.id).pool_latency.latency_ms.toFixed(1)} ms` 
                         : 'Unreachable' }}
                    </span>
                    <v-chip 
                      v-if="getMinerNetworkHealth(selectedMiner.id).pool_latency.status === 'unreachable'"
                      color="grey" 
                      size="x-small" 
                      class="ml-2"
                    >
                      <v-icon start size="x-small">mdi-close-network</v-icon>
                      Unreachable
                    </v-chip>
                    <v-chip 
                      v-else-if="getMinerNetworkHealth(selectedMiner.id).pool_latency.status === 'critical'"
                      color="error" 
                      size="x-small" 
                      class="ml-2"
                    >
                      Critical
                    </v-chip>
                    <v-chip 
                      v-else-if="getMinerNetworkHealth(selectedMiner.id).pool_latency.status === 'warning'"
                      color="warning" 
                      size="x-small" 
                      class="ml-2"
                    >
                      Warning
                    </v-chip>
                  </td>
                </tr>
                <tr v-else-if="getMinerNetworkHealth(selectedMiner.id)">
                  <td><strong>Pool Configuration:</strong></td>
                  <td style="color: #9E9E9E">
                    No pool configured
                  </td>
                </tr>
                <tr v-if="getMinerNetworkHealth(selectedMiner.id).total_path_latency_ms">
                  <td><strong>Total Path Latency:</strong></td>
                  <td :style="{ color: getLatencyColor(getMinerNetworkHealth(selectedMiner.id).total_path_latency_ms) }">
                    {{ getMinerNetworkHealth(selectedMiner.id).total_path_latency_ms.toFixed(1) }} ms
                  </td>
                </tr>
                <tr>
                  <td><strong>Packet Loss:</strong></td>
                  <td :style="{ color: getPacketLossColor(getMinerNetworkHealth(selectedMiner.id).packet_loss_percent) }">
                    {{ getMinerNetworkHealth(selectedMiner.id).packet_loss_percent !== null 
                       ? `${getMinerNetworkHealth(selectedMiner.id).packet_loss_percent.toFixed(2)}%` 
                       : 'N/A' }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" :to="`/miners/${selectedMiner.id}`">
            View Details
          </v-btn>
          <v-btn color="error" @click="showMinerDetails = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Pool Details Dialog -->
    <v-dialog 
      v-model="showPoolDetails" 
      max-width="600px"
      scrollable
      :attach="false"
    >
      <v-card v-if="selectedPool">
        <v-card-title>
          Pool Server Details
          <v-spacer></v-spacer>
          <v-chip :color="getPoolStatusChipColor(selectedPool.status)" dark small>
            {{ selectedPool.status || 'unknown' }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <v-table>
            <tbody>
              <tr>
                <td><strong>URL:</strong></td>
                <td>{{ selectedPool.url }}</td>
              </tr>
              <tr>
                <td><strong>Port:</strong></td>
                <td>{{ selectedPool.port || 'N/A' }}</td>
              </tr>
              <tr>
                <td><strong>Latency:</strong></td>
                <td :style="{ color: getPoolLatencyColor(selectedPool.latency) }">
                  {{ selectedPool.latency !== null ? `${selectedPool.latency.toFixed(1)} ms` : 'Unreachable' }}
                </td>
              </tr>
              <tr>
                <td><strong>Connected Miners:</strong></td>
                <td>{{ selectedPool.connectedMiners?.length || 0 }}</td>
              </tr>
            </tbody>
          </v-table>
          
          <div v-if="selectedPool.connectedMiners && selectedPool.connectedMiners.length > 0" class="mt-4">
            <v-divider class="mb-3"></v-divider>
            <div class="text-subtitle-2 mb-2">Miners Using This Pool:</div>
            <v-chip-group column>
              <v-chip 
                v-for="miner in selectedPool.connectedMiners" 
                :key="miner.id"
                :color="getMinerTypeColor(miner.type)"
                text-color="white"
                size="small"
                @click="navigateToMiner(miner.id)"
                style="cursor: pointer"
              >
                {{ miner.name }}
              </v-chip>
            </v-chip-group>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showPoolDetails = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from "vue";
import { useMinersStore } from "../stores/miners";
import { useSettingsStore } from "../stores/settings";
import { usePollingManager } from "../composables/usePollingManager";
import { useGlobalSnackbar } from "../composables/useGlobalSnackbar";
import { formatTemperature } from "../utils/formatters";
import * as d3 from "d3";

export default {
  name: "Network",

  setup() {
    const minersStore = useMinersStore();
    const settingsStore = useSettingsStore();
    const { showSnackbar } = useGlobalSnackbar();

    // Network visualization
    let networkSimulation = null;
    let networkSvg = null;

    // State
    const loading = ref(false);
    const layoutType = ref("force");
    const groupByType = ref(true);
    const showMinerDetails = ref(false);
    const selectedMiner = ref(null);
    const showPoolDetails = ref(false);
    const selectedPool = ref(null);
    const networkHealthData = ref({});
    const networkHealthLoading = ref(false);

    // Layout options
    const layoutOptions = [
      { text: "Force-Directed", value: "force" },
      { text: "Radial", value: "radial" },
      { text: "Grid", value: "grid" },
      { text: "Tree", value: "tree" },
    ];

    // Declare refreshNetwork before usePollingManager to avoid hoisting issues
    const refreshNetwork = async () => {
      loading.value = true;

      try {
        console.log('[Network] Refreshing network data...');
        await minersStore.fetchMiners();
        console.log('[Network] Miners fetched:', miners.value.length);
        
        // Fetch network health data
        await fetchNetworkHealth();
        
        showSnackbar('Network refreshed successfully', 'success');
      } catch (error) {
        console.error("Error refreshing network:", error);
        showSnackbar(`Failed to refresh network: ${error.message}`, 'error');
      } finally {
        loading.value = false;
        
        // Wait for DOM to update after loading is set to false
        await nextTick();
        
        // Only update visualization if we have miners and container exists
        if (miners.value.length > 0) {
          const container = document.getElementById('network-container');
          if (container) {
            updateNetworkVisualization();
            console.log('[Network] Visualization updated');
          } else {
            console.warn('[Network] Container not ready yet, will render on next tick');
          }
        }
      }
    };

    // Set up polling manager
    const { startPolling, stopPolling } = usePollingManager({
      fetchFunction: refreshNetwork,
      intervalKey: "refresh_interval",
      componentName: "Network",
      enabled: true,
    });

    // Computed properties
    const miners = computed(() => minersStore.miners);
    const onlineMiners = computed(() => minersStore.onlineMiners);
    const offlineMiners = computed(() => minersStore.offlineMiners);
    const totalHashrate = computed(() => minersStore.totalHashrate);

    const minerTypeCount = computed(() => {
      const counts = {};
      miners.value.forEach((miner) => {
        counts[miner.type] = (counts[miner.type] || 0) + 1;
      });
      return counts;
    });

    const averageMinerLatency = computed(() => {
      const healthValues = Object.values(networkHealthData.value);
      if (healthValues.length === 0) return null;
      
      const validLatencies = healthValues
        .filter(h => h && h.miner_latency_ms !== null && h.miner_latency_ms !== undefined)
        .map(h => h.miner_latency_ms);
      
      if (validLatencies.length === 0) return null;
      
      return validLatencies.reduce((sum, val) => sum + val, 0) / validLatencies.length;
    });

    const averagePoolLatency = computed(() => {
      const healthValues = Object.values(networkHealthData.value);
      if (healthValues.length === 0) return null;
      
      const validPoolLatencies = healthValues
        .filter(h => h && h.pool_latency && h.pool_latency.latency_ms !== null && h.pool_latency.latency_ms !== undefined)
        .map(h => h.pool_latency.latency_ms);
      
      if (validPoolLatencies.length === 0) return null;
      
      return validPoolLatencies.reduce((sum, val) => sum + val, 0) / validPoolLatencies.length;
    });

    const averageTotalPathLatency = computed(() => {
      const healthValues = Object.values(networkHealthData.value);
      if (healthValues.length === 0) return null;
      
      const validTotalLatencies = healthValues
        .filter(h => h && h.total_path_latency_ms !== null && h.total_path_latency_ms !== undefined)
        .map(h => h.total_path_latency_ms);
      
      if (validTotalLatencies.length === 0) return null;
      
      return validTotalLatencies.reduce((sum, val) => sum + val, 0) / validTotalLatencies.length;
    });

    const uniquePools = computed(() => {
      const healthValues = Object.values(networkHealthData.value);
      const poolMap = new Map();
      
      healthValues.forEach(health => {
        if (health && health.pool_latency && health.pool_latency.url) {
          const poolKey = `${health.pool_latency.url}:${health.pool_latency.port || ''}`;
          
          if (!poolMap.has(poolKey)) {
            poolMap.set(poolKey, {
              url: health.pool_latency.url,
              port: health.pool_latency.port,
              latency_ms: health.pool_latency.latency_ms,
              status: health.pool_latency.status,
              minerCount: 1
            });
          } else {
            const pool = poolMap.get(poolKey);
            pool.minerCount++;
            // Update latency to average if we have multiple miners
            if (health.pool_latency.latency_ms !== null) {
              if (pool.latency_ms !== null) {
                pool.latency_ms = (pool.latency_ms * (pool.minerCount - 1) + health.pool_latency.latency_ms) / pool.minerCount;
              } else {
                pool.latency_ms = health.pool_latency.latency_ms;
              }
            }
          }
        }
      });
      
      return Array.from(poolMap.values());
    });

    const averagePacketLoss = computed(() => {
      const healthValues = Object.values(networkHealthData.value);
      if (healthValues.length === 0) return null;
      
      const validPacketLoss = healthValues
        .filter(h => h && h.packet_loss_percent !== null && h.packet_loss_percent !== undefined)
        .map(h => h.packet_loss_percent);
      
      if (validPacketLoss.length === 0) return null;
      
      return validPacketLoss.reduce((sum, val) => sum + val, 0) / validPacketLoss.length;
    });

    const averageJitter = computed(() => {
      const healthValues = Object.values(networkHealthData.value);
      if (healthValues.length === 0) return null;
      
      const validJitter = healthValues
        .filter(h => h && h.jitter_ms !== null && h.jitter_ms !== undefined)
        .map(h => h.jitter_ms);
      
      if (validJitter.length === 0) return null;
      
      return validJitter.reduce((sum, val) => sum + val, 0) / validJitter.length;
    });

    const healthyMinersCount = computed(() => {
      return Object.values(networkHealthData.value).filter(h => 
        h && h.status === 'healthy'
      ).length;
    });

    const unreachablePoolsCount = computed(() => {
      return uniquePools.value.filter(pool => 
        pool.status === 'unreachable' || pool.latency_ms === null
      ).length;
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

      const date = new Date(dateString);
      return date.toLocaleString();
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

    const getMinerTypeColor = (type) => {
      switch (type.toLowerCase()) {
        case "bitcoin_node":
          return "#F7931A"; // Bitcoin Orange
        case "bitaxe":
          return "#1976D2"; // Blue
        case "avalon_nano":
          return "#43A047"; // Green
        case "magic_miner":
          return "#E53935"; // Red
        default:
          return "#9C27B0"; // Purple
      }
    };

    const fetchNetworkHealth = async () => {
      if (miners.value.length === 0) return;
      
      networkHealthLoading.value = true;
      try {
        const healthData = await minersStore.fetchAllNetworkHealth();
        networkHealthData.value = healthData;
        console.log('[Network] Network health data fetched:', healthData);
      } catch (error) {
        console.error('[Network] Error fetching network health:', error);
      } finally {
        networkHealthLoading.value = false;
      }
    };

    const getNodeHealthColor = (minerId) => {
      const health = networkHealthData.value[minerId];
      if (!health) return '#9E9E9E'; // Grey for unknown
      
      const minerLatency = health.miner_latency_ms;
      const poolLatency = health.pool_latency?.latency_ms;
      const packetLoss = health.packet_loss_percent;
      
      // Consider both miner and pool latency for overall health
      const totalLatency = health.total_path_latency_ms || minerLatency;
      
      // Red: High latency (>200ms) or packet loss (>5%)
      if (totalLatency > 200 || packetLoss > 5) return '#E53935';
      
      // Yellow: Medium latency (>100ms) or packet loss (>2%)
      if (totalLatency > 100 || packetLoss > 2) return '#FFC107';
      
      // Green: Good health
      return '#43A047';
    };

    const getLatencyColor = (latency) => {
      if (latency === null) return '#9E9E9E';
      if (latency > 200) return '#E53935'; // Red
      if (latency > 100) return '#FFC107'; // Yellow
      return '#43A047'; // Green
    };

    const getPacketLossColor = (packetLoss) => {
      if (packetLoss === null) return '#9E9E9E';
      if (packetLoss > 5) return '#E53935'; // Red
      if (packetLoss > 2) return '#FFC107'; // Yellow
      return '#43A047'; // Green
    };

    const getJitterColor = (jitter) => {
      if (jitter === null) return '#9E9E9E';
      if (jitter > 50) return '#E53935'; // Red
      if (jitter > 20) return '#FFC107'; // Yellow
      return '#43A047'; // Green
    };

    const getPoolLatencyColor = (latency) => {
      if (latency === null) return '#9E9E9E';
      if (latency >= 200) return '#E53935'; // Red - Critical
      if (latency >= 100) return '#FFC107'; // Yellow - Warning
      return '#43A047'; // Green - Healthy
    };

    const getPoolLatencyChipColor = (latency) => {
      if (latency === null) return 'grey'; // Unreachable
      if (latency >= 200) return 'error'; // Red - Critical
      if (latency >= 100) return 'warning'; // Yellow - Warning
      return 'success'; // Green - Healthy
    };

    const hasHealthWarning = (minerId) => {
      const health = networkHealthData.value[minerId];
      if (!health) return false;
      
      const minerLatency = health.miner_latency_ms;
      const poolLatency = health.pool_latency?.latency_ms;
      const totalLatency = health.total_path_latency_ms || minerLatency;
      
      // Warning if miner latency > 100ms, pool latency > 100ms, or packet loss > 2%
      return totalLatency > 100 || 
             (poolLatency !== null && poolLatency >= 100) || 
             health.packet_loss_percent > 2;
    };

    const getMinerNetworkHealth = (minerId) => {
      return networkHealthData.value[minerId] || null;
    };

    const getPoolStatusChipColor = (status) => {
      switch (status) {
        case 'healthy':
          return 'success';
        case 'warning':
          return 'warning';
        case 'critical':
          return 'error';
        case 'unreachable':
          return 'grey';
        default:
          return 'grey';
      }
    };

    const navigateToMiner = (minerId) => {
      showPoolDetails.value = false;
      const miner = miners.value.find(m => m.id === minerId);
      if (miner) {
        selectedMiner.value = miner;
        showMinerDetails.value = true;
      }
    };

    // Function to fix dialog positioning for viewport centering
    const fixDialogPositioning = () => {
      nextTick(() => {
        const overlays = document.querySelectorAll('.v-overlay__content');
        overlays.forEach(overlay => {
          const rect = overlay.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) { // Only visible dialogs
            overlay.style.position = 'fixed';
            overlay.style.top = '50%';
            overlay.style.left = '50%';
            overlay.style.transform = 'translate(-50%, -50%)';
            overlay.style.zIndex = '2000';
            overlay.style.maxHeight = '90vh';
          }
        });
      });
    };

    // Watch for dialog state changes and apply positioning fix
    watch(showMinerDetails, (newValue) => {
      if (newValue) {
        // Dialog is opening, apply fix after a short delay
        setTimeout(fixDialogPositioning, 100);
      }
    });

    watch(showPoolDetails, (newValue) => {
      if (newValue) {
        // Dialog is opening, apply fix after a short delay
        setTimeout(fixDialogPositioning, 100);
      }
    });

    const updateNetworkLayout = () => {
      updateNetworkVisualization();
    };

    const updateNetworkVisualization = () => {
      // Clear previous visualization
      if (networkSvg) {
        d3.select("#network-container").selectAll("*").remove();
      }

      // Create network visualization
      createNetworkVisualization();
    };

    // Build network graph with miners and pool nodes
    const buildNetworkGraph = () => {
      const nodes = [];
      const links = [];
      
      // Add router node
      nodes.push({
        id: 'router',
        name: 'Network Router',
        type: 'router',
        status: 'online'
      });
      
      // Track unique pools/nodes
      const poolMap = new Map();
      
      // Add miner nodes and collect pool information
      miners.value.forEach(miner => {
        // Add miner node
        nodes.push({
          id: miner.id,
          name: miner.name || `${miner.type} (${miner.ip_address})`,
          type: miner.type,
          status: miner.status,
          data: miner
        });
        
        // Link miner to router
        const minerHealth = networkHealthData.value[miner.id];
        links.push({
          source: 'router',
          target: miner.id,
          type: 'miner-connection',
          latency: minerHealth?.miner_latency_ms || null
        });
        
        // Get pool information from network health data
        const health = networkHealthData.value[miner.id];
        if (health?.pool_latency && health.pool_latency.url) {
          const poolKey = `${health.pool_latency.url}:${health.pool_latency.port || ''}`;
          
          // Determine if this is a local Bitcoin node or remote pool
          const isLocalNode = miner.type === 'bitcoin_node' || 
                             health.pool_latency.url.includes('localhost') ||
                             health.pool_latency.url.includes('127.0.0.1') ||
                             health.pool_latency.url.startsWith('192.168.') ||
                             health.pool_latency.url.startsWith('10.') ||
                             health.pool_latency.url.startsWith('172.');
          
          // Add pool node if not already added
          if (!poolMap.has(poolKey)) {
            const poolId = `pool_${poolKey.replace(/[.:]/g, '_')}`;
            poolMap.set(poolKey, poolId);
            
            nodes.push({
              id: poolId,
              name: health.pool_latency.url,
              type: isLocalNode ? 'bitcoin_node_pool' : 'pool',
              status: health.pool_latency.status,
              url: health.pool_latency.url,
              port: health.pool_latency.port,
              latency: health.pool_latency.latency_ms,
              connectedMiners: [miner.id]
            });
          } else {
            // Pool already exists, add this miner to connected miners
            const poolId = poolMap.get(poolKey);
            const poolNode = nodes.find(n => n.id === poolId);
            if (poolNode && !poolNode.connectedMiners.includes(miner.id)) {
              poolNode.connectedMiners.push(miner.id);
            }
          }
          
          // Link miner to pool
          const poolId = poolMap.get(poolKey);
          links.push({
            source: miner.id,
            target: poolId,
            type: 'pool-connection',
            latency: health.pool_latency.latency_ms,
            status: health.pool_latency.status
          });
        }
      });
      
      console.log('[Network] Built graph with', nodes.length, 'nodes and', links.length, 'links');
      console.log('[Network] Pool nodes:', nodes.filter(n => n.type === 'pool' || n.type === 'bitcoin_node_pool'));
      
      return { nodes, links };
    };

    // Helper function to add node icons (Bitcoin logo for Bitcoin nodes, emojis for miners/router/pools)
    const addNodeIcons = (nodeSelection) => {
      nodeSelection.each(function(d) {
        const nodeGroup = d3.select(this);
        
        if (d.type === "router") {
          // Router icon (emoji)
          nodeGroup
            .append("text")
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "central")
            .attr("fill", "#fff")
            .attr("font-size", "20px")
            .text("🌐");
        } else if (d.type === "bitcoin_node_pool") {
          // Bitcoin node pool - use Bitcoin logo SVG
          nodeGroup
            .append("image")
            .attr("xlink:href", "/bitcoin-symbol.svg")
            .attr("x", -12)
            .attr("y", -12)
            .attr("width", 24)
            .attr("height", 24)
            .style("pointer-events", "none");
        } else if (d.type === "pool") {
          // Pool server icon (emoji)
          nodeGroup
            .append("text")
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "central")
            .attr("fill", "#fff")
            .attr("font-size", "18px")
            .text("🏊");
        } else if (d.type === "bitcoin_node") {
          // Bitcoin Core Node - use Bitcoin logo SVG
          nodeGroup
            .append("image")
            .attr("xlink:href", "/bitcoin-symbol.svg")
            .attr("x", -12)
            .attr("y", -12)
            .attr("width", 24)
            .attr("height", 24)
            .style("pointer-events", "none")
            .style("filter", d.status !== "online" ? "grayscale(100%)" : "none");
        } else {
          // Miner icons (emojis based on type)
          nodeGroup
            .append("text")
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "central")
            .attr("fill", "#fff")
            .attr("font-size", "18px")
            .text(() => {
              switch (d.type.toLowerCase()) {
                case "bitaxe":
                  return "⛏️";
                case "avalon_nano":
                  return "🔌";
                case "magic_miner":
                  return "✨";
                default:
                  return "💻";
              }
            });
        }
      });
    };

    const createNetworkVisualization = () => {
      console.log('[Network] Creating visualization...');
      
      // Get container dimensions
      const container = document.getElementById("network-container");
      if (!container) {
        console.warn('[Network] Container #network-container not found, skipping visualization');
        return;
      }

      const width = container.clientWidth;
      const height = container.clientHeight;
      console.log('[Network] Container dimensions:', width, 'x', height);

      if (width === 0 || height === 0) {
        console.warn('[Network] Container has zero dimensions, skipping visualization');
        return;
      }

      // Create SVG
      networkSvg = d3
        .select("#network-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

      console.log('[Network] SVG created');

      // Build network graph with miners and pools
      const { nodes, links } = buildNetworkGraph();

      // Create simulation based on layout type
      switch (layoutType.value) {
        case "force":
          createForceLayout(nodes, links, width, height);
          break;
        case "radial":
          createRadialLayout(nodes, links, width, height);
          break;
        case "grid":
          createGridLayout(nodes, links, width, height);
          break;
        case "tree":
          createTreeLayout(nodes, links, width, height);
          break;
        default:
          createForceLayout(nodes, links, width, height);
      }
    };

    // Helper function to get node color based on type and status
    const getNodeColor = (node) => {
      if (node.type === 'router') return '#FFC107'; // Orange
      if (node.type === 'bitcoin_node_pool') return '#F7931A'; // Bitcoin orange
      if (node.type === 'pool') {
        // Color based on pool status
        if (node.status === 'unreachable') return '#9E9E9E'; // Grey
        if (node.status === 'critical') return '#E53935'; // Red
        if (node.status === 'warning') return '#FFC107'; // Yellow
        return '#2196F3'; // Blue for healthy pools
      }
      
      // Miner nodes - use health color if available
      if (node.status !== 'online') return '#9E9E9E'; // Grey for offline
      const healthColor = getNodeHealthColor(node.id);
      return healthColor !== '#9E9E9E' ? healthColor : getMinerTypeColor(node.type);
    };

    // Helper function to get node size based on type
    const getNodeSize = (node) => {
      if (node.type === 'router') return 25;
      if (node.type === 'pool' || node.type === 'bitcoin_node_pool') {
        // Size based on number of connected miners
        const baseSize = 15;
        const connectedCount = node.connectedMiners?.length || 0;
        return baseSize + (connectedCount * 3);
      }
      return 15; // Miner nodes
    };

    // Helper function to get link color based on latency
    const getLinkColor = (link) => {
      if (link.type === 'miner-connection') {
        // Router to miner - use miner health color
        if (!link.latency) return '#999';
        if (link.latency > 50) return '#E53935'; // Red
        if (link.latency > 25) return '#FFC107'; // Yellow
        return '#43A047'; // Green
      }
      
      if (link.type === 'pool-connection') {
        // Miner to pool - use pool health color
        if (!link.latency) return '#999';
        if (link.latency >= 200) return '#E53935'; // Red - Critical
        if (link.latency >= 100) return '#FFC107'; // Yellow - Warning
        return '#43A047'; // Green - Healthy
      }
      
      return '#999';
    };

    // Helper function to get link width based on connection quality
    const getLinkWidth = (link) => {
      if (!link.latency) return 1;
      if (link.latency < 50) return 3; // Excellent
      if (link.latency < 100) return 2; // Good
      return 1; // Poor
    };

    const createForceLayout = (nodes, links, width, height) => {
      // Create simulation
      networkSimulation = d3
        .forceSimulation(nodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(150),
        )
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(50));

      // Create links
      const link = networkSvg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", (d) => getLinkColor(d))
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => getLinkWidth(d));

      // Create nodes
      const node = networkSvg
        .append("g")
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .call(
          d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended),
        )
        .style("cursor", (d) => (d.type !== "router" && d.type !== "group") ? "pointer" : "default")

        .on("click", handleNodeClick)

        .on("mouseenter", function(event, d) {

          if (d.type !== "router" && d.type !== "group") {

            const originalSize = getNodeSize(d);

            d3.select(this).select("circle")

              .transition()

              .duration(200)

              .attr("r", originalSize + 3)

              .attr("stroke-width", 3);

          }

        })

        .on("mouseleave", function(event, d) {

          if (d.type !== "router" && d.type !== "group") {

            const originalSize = getNodeSize(d);

            d3.select(this).select("circle")

              .transition()

              .duration(200)

              .attr("r", originalSize)

              .attr("stroke-width", hasHealthWarning(d.id) ? 3 : 1.5);

          }

        });

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", (d) => getNodeSize(d))
        .attr("fill", (d) => getNodeColor(d))
        .attr("stroke", (d) => {
          // Add warning stroke for miners with health issues
          if (d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
            return "#FF5722"; // Orange warning stroke
          }
          return "#fff";
        })
        .attr("stroke-width", (d) => {
          // Thicker stroke for warning
          if (d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
            return 3;
          }
          return 1.5;
        });

      // Add icons to nodes using helper function
      addNodeIcons(node);

      // Add labels to nodes
      node
        .append("text")
        .attr("dy", 40)
        .attr("text-anchor", "middle")
        .attr("fill", "#ffffff")
        .attr("font-size", "14px")
        .attr("font-weight", "500")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
        .text((d) => {
          if (d.type === "router") return "Router";
          if (d.type === "pool" || d.type === "bitcoin_node_pool") {
            // Show pool URL (shortened if too long)
            const poolName = d.name || d.url || "Pool";
            return poolName.length > 20 ? `${poolName.substring(0, 17)}...` : poolName;
          }
          return d.name.length > 15 ? `${d.name.substring(0, 12)}...` : d.name;
        });

      // Add connected miner count badge for pool nodes
      node
        .filter((d) => (d.type === "pool" || d.type === "bitcoin_node_pool") && d.connectedMiners?.length > 0)
        .append("text")
        .attr("dx", 18)
        .attr("dy", -10)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("fill", "#ffffff")
        .attr("font-weight", "bold")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
        .text((d) => d.connectedMiners.length);

      // Add warning badge for poor health miners
      node
        .filter((d) => d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id))
        .append("text")
        .attr("dx", 18)
        .attr("dy", -10)
        .attr("text-anchor", "middle")
        .attr("font-size", "16px")
        .text("⚠️");

      // Update positions on tick
      networkSimulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    };

    const createRadialLayout = (nodes, links, width, height) => {
      // Group nodes by type if needed
      const groupedNodes = [...nodes];

      if (groupByType.value) {
        // Create hierarchy
        const typeGroups = {};
        nodes.forEach((node) => {
          if (node.type !== "router") {
            if (!typeGroups[node.type]) {
              typeGroups[node.type] = [];
            }
            typeGroups[node.type].push(node);
          }
        });

        // Position nodes in circles around their type
        const radius = Math.min(width, height) / 3;
        const centerX = width / 2;
        const centerY = height / 2;

        // Position router at center
        const router = nodes.find((n) => n.type === "router");
        if (router) {
          router.x = centerX;
          router.y = centerY;
          router.fx = centerX;
          router.fy = centerY;
        }

        // Position type groups in a circle around the router
        const typeKeys = Object.keys(typeGroups);
        typeKeys.forEach((type, i) => {
          const angle = (i / typeKeys.length) * 2 * Math.PI;
          const groupX = centerX + radius * Math.cos(angle);
          const groupY = centerY + radius * Math.sin(angle);

          // Position nodes in a smaller circle around their type center
          const nodesInGroup = typeGroups[type];
          const groupRadius = 50;

          nodesInGroup.forEach((node, j) => {
            const nodeAngle = (j / nodesInGroup.length) * 2 * Math.PI;
            node.x = groupX + groupRadius * Math.cos(nodeAngle);
            node.y = groupY + groupRadius * Math.sin(nodeAngle);
          });
        });
      }

      // Create force simulation
      networkSimulation = d3
        .forceSimulation(groupedNodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(100),
        )
        .force("charge", d3.forceManyBody().strength(-100))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(30));

      if (groupByType.value) {
        // Fix router position
        const router = groupedNodes.find((n) => n.type === "router");
        if (router) {
          router.fx = width / 2;
          router.fy = height / 2;
        }
      }

      // Create links
      const link = networkSvg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", (d) => getLinkColor(d))
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => getLinkWidth(d));

      // Create nodes
      const node = networkSvg
        .append("g")
        .selectAll("g")
        .data(groupedNodes)
        .enter()
        .append("g")
        .call(
          d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended),
        )
        .style("cursor", (d) => (d.type !== "router" && d.type !== "group") ? "pointer" : "default")

        .on("click", handleNodeClick)

        .on("mouseenter", function(event, d) {

          if (d.type !== "router" && d.type !== "group") {

            const originalSize = getNodeSize(d);

            d3.select(this).select("circle")

              .transition()

              .duration(200)

              .attr("r", originalSize + 3)

              .attr("stroke-width", 3);

          }

        })

        .on("mouseleave", function(event, d) {

          if (d.type !== "router" && d.type !== "group") {

            const originalSize = getNodeSize(d);

            d3.select(this).select("circle")

              .transition()

              .duration(200)

              .attr("r", originalSize)

              .attr("stroke-width", hasHealthWarning(d.id) ? 3 : 1.5);

          }

        });

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", (d) => getNodeSize(d))
        .attr("fill", (d) => getNodeColor(d))
        .attr("stroke", (d) => {
          // Add warning stroke for miners with health issues
          if (d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
            return "#FF5722"; // Orange warning stroke
          }
          return "#fff";
        })
        .attr("stroke-width", (d) => {
          // Thicker stroke for warning
          if (d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
            return 3;
          }
          return 1.5;
        });

      // Add icons to nodes using helper function
      addNodeIcons(node);

      // Add labels to nodes
      node
        .append("text")
        .attr("dy", 40)
        .attr("text-anchor", "middle")
        .attr("fill", "#ffffff")
        .attr("font-size", "14px")
        .attr("font-weight", "500")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
        .text((d) => {
          if (d.type === "router") return "Router";
          if (d.type === "pool" || d.type === "bitcoin_node_pool") {
            // Show pool URL (shortened if too long)
            const poolName = d.name || d.url || "Pool";
            return poolName.length > 20 ? `${poolName.substring(0, 17)}...` : poolName;
          }
          return d.name.length > 15 ? `${d.name.substring(0, 12)}...` : d.name;
        });

      // Add connected miner count badge for pool nodes
      node
        .filter((d) => (d.type === "pool" || d.type === "bitcoin_node_pool") && d.connectedMiners?.length > 0)
        .append("text")
        .attr("dx", 18)
        .attr("dy", -10)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("fill", "#ffffff")
        .attr("font-weight", "bold")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
        .text((d) => d.connectedMiners.length);

      // Add warning badge for poor health miners
      node
        .filter((d) => d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id))
        .append("text")
        .attr("dx", 18)
        .attr("dy", -10)
        .attr("text-anchor", "middle")
        .attr("font-size", "16px")
        .text("⚠️");

      // Update positions on tick
      networkSimulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        if (d.type !== "router" || !groupByType.value) {
          d.fx = null;
          d.fy = null;
        }
      }
    };

    const createGridLayout = (nodes, links, width, height) => {
      // Calculate grid dimensions
      const totalNodes = nodes.length;
      const cols = Math.ceil(Math.sqrt(totalNodes));
      const rows = Math.ceil(totalNodes / cols);

      const cellWidth = width / (cols + 1);
      const cellHeight = height / (rows + 1);

      // Position nodes in grid
      nodes.forEach((node, i) => {
        const row = Math.floor(i / cols);
        const col = i % cols;

        node.x = (col + 1) * cellWidth;
        node.y = (row + 1) * cellHeight;

        // Fix router position
        if (node.type === "router") {
          node.x = width / 2;
          node.y = height / 4;
        }
      });

      // Create force simulation with very weak forces
      networkSimulation = d3
        .forceSimulation(nodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(100)
            .strength(0.1),
        )
        .force("charge", d3.forceManyBody().strength(-10))
        .force("center", d3.forceCenter(width / 2, height / 2).strength(0.1))
        .force(
          "x",
          d3
            .forceX()
            .x((d) => d.x)
            .strength(0.7),
        )
        .force(
          "y",
          d3
            .forceY()
            .y((d) => d.y)
            .strength(0.7),
        );

      // Create links
      const link = networkSvg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", (d) => getLinkColor(d))
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => getLinkWidth(d));

      // Create nodes
      const node = networkSvg
        .append("g")
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .call(
          d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended),
        )
        .style("cursor", (d) => (d.type !== "router" && d.type !== "group") ? "pointer" : "default")

        .on("click", handleNodeClick)

        .on("mouseenter", function(event, d) {

          if (d.type !== "router" && d.type !== "group") {

            const originalSize = getNodeSize(d);

            d3.select(this).select("circle")

              .transition()

              .duration(200)

              .attr("r", originalSize + 3)

              .attr("stroke-width", 3);

          }

        })

        .on("mouseleave", function(event, d) {

          if (d.type !== "router" && d.type !== "group") {

            const originalSize = getNodeSize(d);

            d3.select(this).select("circle")

              .transition()

              .duration(200)

              .attr("r", originalSize)

              .attr("stroke-width", hasHealthWarning(d.id) ? 3 : 1.5);

          }

        });

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", (d) => getNodeSize(d))
        .attr("fill", (d) => getNodeColor(d))
        .attr("stroke", (d) => {
          // Add warning stroke for miners with health issues
          if (d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
            return "#FF5722"; // Orange warning stroke
          }
          return "#fff";
        })
        .attr("stroke-width", (d) => {
          // Thicker stroke for warning
          if (d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
            return 3;
          }
          return 1.5;
        });

      // Add icons to nodes using helper function
      addNodeIcons(node);

      // Add labels to nodes
      node
        .append("text")
        .attr("dy", 40)
        .attr("text-anchor", "middle")
        .attr("fill", "#ffffff")
        .attr("font-size", "14px")
        .attr("font-weight", "500")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
        .text((d) => {
          if (d.type === "router") return "Router";
          if (d.type === "pool" || d.type === "bitcoin_node_pool") {
            // Show pool URL (shortened if too long)
            const poolName = d.name || d.url || "Pool";
            return poolName.length > 20 ? `${poolName.substring(0, 17)}...` : poolName;
          }
          return d.name.length > 15 ? `${d.name.substring(0, 12)}...` : d.name;
        });

      // Add connected miner count badge for pool nodes
      node
        .filter((d) => (d.type === "pool" || d.type === "bitcoin_node_pool") && d.connectedMiners?.length > 0)
        .append("text")
        .attr("dx", 18)
        .attr("dy", -10)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("fill", "#ffffff")
        .attr("font-weight", "bold")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
        .text((d) => d.connectedMiners.length);

      // Add warning badge for poor health miners
      node
        .filter((d) => d.type !== "router" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id))
        .append("text")
        .attr("dx", 18)
        .attr("dy", -10)
        .attr("text-anchor", "middle")
        .attr("font-size", "16px")
        .text("⚠️");

      // Update positions on tick
      networkSimulation.on("tick", () => {
        link
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);

        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    };

    const createTreeLayout = (nodes, links, width, height) => {
      // Create hierarchy data
      const routerNode = nodes.find((n) => n.type === "router");
      if (!routerNode) return;

      // Group miners by type if needed
      if (groupByType.value) {
        // Create hierarchy
        const hierarchy = {
          id: "router",
          name: "Network Router",
          type: "router",
          status: "online",
          children: [],
        };

        // Group by type
        const typeGroups = {};
        nodes.forEach((node) => {
          if (node.type !== "router") {
            if (!typeGroups[node.type]) {
              typeGroups[node.type] = [];
            }
            typeGroups[node.type].push(node);
          }
        });

        // Add type groups to hierarchy
        Object.entries(typeGroups).forEach(([type, minerNodes]) => {
          const typeNode = {
            id: `type-${type}`,
            name: type,
            type: "group",
            children: minerNodes.map((miner) => ({
              ...miner,
              children: [],
            })),
          };
          hierarchy.children.push(typeNode);
        });

        // Create tree layout
        const treeLayout = d3.tree().size([width - 100, height - 100]);

        // Create hierarchy
        const root = d3.hierarchy(hierarchy);

        // Apply layout
        const treeData = treeLayout(root);

        // Extract nodes and links
        const treeNodes = [];
        const treeLinks = [];

        // Add nodes
        treeData.descendants().forEach((d) => {
          const node = {
            id: d.data.id,
            name: d.data.name,
            type: d.data.type,
            status: d.data.status,
            data: d.data.data,
            x: d.x + 50,
            y: d.y + 50,
          };
          treeNodes.push(node);
        });

        // Add links
        treeData.links().forEach((d) => {
          treeLinks.push({
            source: d.source.data.id,
            target: d.target.data.id,
            value: 1,
          });
        });

        // Create force simulation with very weak forces
        networkSimulation = d3
          .forceSimulation(treeNodes)
          .force(
            "link",
            d3
              .forceLink(treeLinks)
              .id((d) => d.id)
              .distance(100)
              .strength(0.1),
          )
          .force("charge", d3.forceManyBody().strength(-10))
          .force(
            "x",
            d3
              .forceX()
              .x((d) => d.x)
              .strength(0.9),
          )
          .force(
            "y",
            d3
              .forceY()
              .y((d) => d.y)
              .strength(0.9),
          );

        // Create links
        const link = networkSvg
          .append("g")
          .selectAll("line")
          .data(treeLinks)
          .enter()
          .append("line")
          .attr("stroke", (d) => {
            // For tree layout, use simple grey for hierarchy links
            return "#999";
          })
          .attr("stroke-opacity", 0.6)
          .attr("stroke-width", 1.5);

        // Create nodes
        const node = networkSvg
          .append("g")
          .selectAll("g")
          .data(treeNodes)
          .enter()
          .append("g")
          .call(
            d3
              .drag()
              .on("start", dragstarted)
              .on("drag", dragged)
              .on("end", dragended),
          )
          .style("cursor", (d) => (d.type !== "router" && d.type !== "group") ? "pointer" : "default")

          .on("click", handleNodeClick)

          .on("mouseenter", function(event, d) {

            if (d.type !== "router" && d.type !== "group") {

              const originalSize = d.type === "pool" || d.type === "bitcoin_node_pool" ? getNodeSize(d) : 15;

              d3.select(this).select("circle")

                .transition()

                .duration(200)

                .attr("r", originalSize + 3)

                .attr("stroke-width", 3);

            }

          })

          .on("mouseleave", function(event, d) {

            if (d.type !== "router" && d.type !== "group") {

              const originalSize = d.type === "pool" || d.type === "bitcoin_node_pool" ? getNodeSize(d) : 15;

              d3.select(this).select("circle")

                .transition()

                .duration(200)

                .attr("r", originalSize)

                .attr("stroke-width", hasHealthWarning(d.id) ? 3 : 1.5);

            }

          });

        // Add circles to nodes
        node
          .append("circle")
          .attr("r", (d) => {
            if (d.type === "router") return 25;
            if (d.type === "group") return 20;
            if (d.type === "pool" || d.type === "bitcoin_node_pool") return getNodeSize(d);
            return 15;
          })
          .attr("fill", (d) => {
            if (d.type === "router") return "#FFC107";
            if (d.type === "group") return "#673AB7";
            if (d.type === "pool" || d.type === "bitcoin_node_pool") return getNodeColor(d);
            return d.status === "online"
              ? getMinerTypeColor(d.type)
              : "#9E9E9E";
          })
          .attr("stroke", (d) => {
            // Add warning stroke for miners with health issues
            if (d.type !== "router" && d.type !== "group" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
              return "#FF5722"; // Orange warning stroke
            }
            return "#fff";
          })
          .attr("stroke-width", (d) => {
            // Thicker stroke for warning
            if (d.type !== "router" && d.type !== "group" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id)) {
              return 3;
            }
            return 1.5;
          });

        // Add icons to nodes
        node.each(function(d) {
          const nodeGroup = d3.select(this);
          
          if (d.type === "router") {
            // Router icon (emoji)
            nodeGroup
              .append("text")
              .attr("text-anchor", "middle")
              .attr("dominant-baseline", "central")
              .attr("fill", "#fff")
              .attr("font-size", "20px")
              .text("🌐");
          } else if (d.type === "group") {
            // Group icon (emoji)
            nodeGroup
              .append("text")
              .attr("text-anchor", "middle")
              .attr("dominant-baseline", "central")
              .attr("fill", "#fff")
              .attr("font-size", "18px")
              .text("📁");
          } else if (d.type === "bitcoin_node_pool") {
            // Bitcoin node pool - use Bitcoin logo SVG
            nodeGroup
              .append("image")
              .attr("xlink:href", "/bitcoin-symbol.svg")
              .attr("x", -12)
              .attr("y", -12)
              .attr("width", 24)
              .attr("height", 24)
              .style("pointer-events", "none");
          } else if (d.type === "pool") {
            // Pool server icon (emoji)
            nodeGroup
              .append("text")
              .attr("text-anchor", "middle")
              .attr("dominant-baseline", "central")
              .attr("fill", "#fff")
              .attr("font-size", "18px")
              .text("🏊");
          } else if (d.type === "bitcoin_node") {
            // Bitcoin Core Node - use Bitcoin logo SVG
            nodeGroup
              .append("image")
              .attr("xlink:href", "/bitcoin-symbol.svg")
              .attr("x", -12)
              .attr("y", -12)
              .attr("width", 24)
              .attr("height", 24)
              .style("pointer-events", "none")
              .style("filter", d.status !== "online" ? "grayscale(100%)" : "none");
          } else {
            // Miner icons (emojis based on type)
            nodeGroup
              .append("text")
              .attr("text-anchor", "middle")
              .attr("dominant-baseline", "central")
              .attr("fill", "#fff")
              .attr("font-size", "18px")
              .text(() => {
                switch (d.type.toLowerCase()) {
                  case "bitaxe":
                    return "⛏️";
                  case "avalon_nano":
                    return "🔌";
                  case "magic_miner":
                    return "✨";
                  default:
                    return "💻";
                }
              });
          }
        });

        // Add labels to nodes
        node
          .append("text")
          .attr("dy", 40)
          .attr("text-anchor", "middle")
          .attr("fill", "#ffffff")
          .attr("font-size", "14px")
          .attr("font-weight", "500")
          .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
          .text((d) => {
            if (d.type === "router") return "Router";
            if (d.type === "group") return d.name;
            if (d.type === "pool" || d.type === "bitcoin_node_pool") {
              // Show pool URL (shortened if too long)
              const poolName = d.name || d.url || "Pool";
              return poolName.length > 20 ? `${poolName.substring(0, 17)}...` : poolName;
            }
            return d.name.length > 15
              ? `${d.name.substring(0, 12)}...`
              : d.name;
          });

        // Add connected miner count badge for pool nodes
        node
          .filter((d) => (d.type === "pool" || d.type === "bitcoin_node_pool") && d.connectedMiners?.length > 0)
          .append("text")
          .attr("dx", 18)
          .attr("dy", -10)
          .attr("text-anchor", "middle")
          .attr("font-size", "12px")
          .attr("fill", "#ffffff")
          .attr("font-weight", "bold")
          .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.8)")
          .text((d) => d.connectedMiners.length);

        // Add warning badge for poor health miners
        node
          .filter((d) => d.type !== "router" && d.type !== "group" && d.type !== "pool" && d.type !== "bitcoin_node_pool" && hasHealthWarning(d.id))
          .append("text")
          .attr("dx", 18)
          .attr("dy", -10)
          .attr("text-anchor", "middle")
          .attr("font-size", "16px")
          .text("⚠️");

        // Update positions on tick
        networkSimulation.on("tick", () => {
          link
            .attr("x1", (d) => d.source.x)
            .attr("y1", (d) => d.source.y)
            .attr("x2", (d) => d.target.x)
            .attr("y2", (d) => d.target.y);

          node.attr("transform", (d) => `translate(${d.x},${d.y})`);
        });
      } else {
        // Simple tree without grouping
        createRadialLayout(nodes, links, width, height);
      }

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) networkSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    };

    const handleNodeClick = (event, d) => {
      // Handle pool node clicks
      if (d.type === "pool" || d.type === "bitcoin_node_pool") {
        selectedPool.value = {
          url: d.url,
          port: d.port,
          latency: d.latency,
          status: d.status,
          connectedMiners: d.connectedMiners.map(minerId => {
            const miner = miners.value.find(m => m.id === minerId);
            return {
              id: minerId,
              name: miner?.name || minerId,
              type: miner?.type || 'unknown'
            };
          })
        };
        showPoolDetails.value = true;
      }
      // Handle miner node clicks
      else if (d.type !== "router" && d.type !== "group" && d.data) {
        selectedMiner.value = d.data;
        showMinerDetails.value = true;
      }
    };

    const exportNetworkImage = () => {
      // Get SVG element
      const svgElement = document.querySelector("#network-container svg");
      if (!svgElement) return;

      // Create a canvas element
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");

      // Set canvas dimensions
      canvas.width = svgElement.clientWidth;
      canvas.height = svgElement.clientHeight;

      // Create an image from the SVG
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const img = new Image();

      // Create a Blob from the SVG data
      const svgBlob = new Blob([svgData], {
        type: "image/svg+xml;charset=utf-8",
      });
      const url = URL.createObjectURL(svgBlob);

      // When the image is loaded, draw it on the canvas and download
      img.onload = () => {
        // Fill background
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);

        // Draw SVG on canvas
        context.drawImage(img, 0, 0);

        // Convert canvas to data URL
        const dataUrl = canvas.toDataURL("image/png");

        // Create download link
        const link = document.createElement("a");
        link.download = "network_topology.png";
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Clean up
        URL.revokeObjectURL(url);
      };

      img.src = url;
    };

    // Lifecycle hooks
    onMounted(async () => {
      // Fetch miners
      await minersStore.fetchMiners();

      // Fetch network health
      await fetchNetworkHealth();

      // Wait for DOM to be ready
      await nextTick();

      // Create network visualization if we have miners
      if (miners.value.length > 0) {
        createNetworkVisualization();
      }

      // Start polling
      startPolling();
    });

    onUnmounted(() => {
      // Stop simulation
      if (networkSimulation) {
        networkSimulation.stop();
      }
    });

    return {
      // State
      loading,
      layoutType,
      layoutOptions,
      groupByType,
      showMinerDetails,
      selectedMiner,
      showPoolDetails,
      selectedPool,
      networkHealthData,
      networkHealthLoading,

      // Computed
      miners,
      onlineMiners,
      offlineMiners,
      totalHashrate,
      minerTypeCount,
      averageMinerLatency,
      averagePoolLatency,
      averageTotalPathLatency,
      averagePacketLoss,
      averageJitter,
      healthyMinersCount,
      uniquePools,
      unreachablePoolsCount,

      // Methods
      formatHashrate,
      formatTemperature,
      formatUptime,
      formatDate,
      getStatusColor,
      getMinerTypeColor,
      refreshNetwork,
      updateNetworkLayout,
      exportNetworkImage,
      fetchNetworkHealth,
      getNodeHealthColor,
      getLatencyColor,
      getPacketLossColor,
      getJitterColor,
      getPoolLatencyColor,
      getPoolLatencyChipColor,
      getPoolStatusChipColor,
      hasHealthWarning,
      getMinerNetworkHealth,
      navigateToMiner,
      fixDialogPositioning,
    };
  },
};
</script>

<style scoped>
/* Fix dialog viewport centering - target all dialogs in this component */
:deep(.v-overlay__content) {
  position: fixed !important;
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%) !important;
  max-height: 90vh !important;
  z-index: 2000 !important;
}

/* Ensure dialog cards are properly sized and scrollable */
:deep(.v-dialog .v-card) {
  max-height: 90vh !important;
  display: flex !important;
  flex-direction: column !important;
  margin: 0 !important;
  overflow: hidden !important;
}

/* Make card content scrollable */
:deep(.v-dialog .v-card-text) {
  overflow-y: auto !important;
  flex: 1 1 auto !important;
}

/* Ensure card title and actions stay fixed */
:deep(.v-dialog .v-card-title) {
  flex-shrink: 0 !important;
}

:deep(.v-dialog .v-card-actions) {
  flex-shrink: 0 !important;
}
</style>
