<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Analytics</h1>
      </v-col>
    </v-row>

    <!-- Time Range and Increment Selectors -->
    <v-row>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Time Range</v-card-title>
          <v-card-text>
            <v-btn-toggle
              v-model="selectedTimeRange"
              mandatory
              color="primary"
              @update:model-value="onTimeRangeChange"
            >
              <v-btn value="1h">1 Hour</v-btn>
              <v-btn value="24h">24 Hours</v-btn>
              <v-btn value="7d">7 Days</v-btn>
              <v-btn value="30d">30 Days</v-btn>
              <v-btn value="all">All Time</v-btn>
            </v-btn-toggle>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Time Increment</v-card-title>
          <v-card-text>
            <v-btn-toggle
              v-model="selectedIncrement"
              mandatory
              color="primary"
              @update:model-value="onIncrementChange"
            >
              <v-btn value="1m" :disabled="!isIncrementValid('1m')">1 Min</v-btn>
              <v-btn value="15m" :disabled="!isIncrementValid('15m')">15 Min</v-btn>
              <v-btn value="1h" :disabled="!isIncrementValid('1h')">1 Hour</v-btn>
              <v-btn value="1d" :disabled="!isIncrementValid('1d')">1 Day</v-btn>
            </v-btn-toggle>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Miner Selection</v-card-title>
          <v-card-text>
            <v-select
              v-model="selectedMiners"
              :items="minerOptions"
              item-title="name"
              item-value="id"
              label="Select Miners"
              multiple
              chips
              :loading="loading"
            ></v-select>

            <v-checkbox
              v-model="compareMiners"
              label="Compare Miners"
              :disabled="selectedMiners.length < 2"
            ></v-checkbox>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Hashrate Chart -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Hashrate
            <v-spacer></v-spacer>
            <v-btn icon @click="exportHashrateData">
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div
              v-if="loading"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="hashrateChart" height="200"></canvas>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Temperature Chart -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Temperature
            <v-spacer></v-spacer>
            <v-btn icon @click="exportTemperatureData">
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div
              v-if="loading"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="temperatureChart" height="200"></canvas>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Shares Chart -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Shares
            <v-spacer></v-spacer>
            <v-btn icon @click="exportSharesData">
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div
              v-if="loading"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="sharesChart" height="200"></canvas>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Power Consumption Chart -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Power Consumption
            <v-spacer></v-spacer>
            <v-btn icon @click="exportPowerData">
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div
              v-if="loading"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 200px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="powerChart" height="200"></canvas>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Statistics Summary -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Statistics Summary</v-card-title>
          <v-card-text>
            <v-table>
              <thead>
                <tr>
                  <th class="text-left">Metric</th>
                  <th class="text-left">Average</th>
                  <th class="text-left">Minimum</th>
                  <th class="text-left">Maximum</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Hashrate</td>
                  <td>{{ formatHashrate(stats.hashrate.avg) }}</td>
                  <td>{{ formatHashrate(stats.hashrate.min) }}</td>
                  <td>{{ formatHashrate(stats.hashrate.max) }}</td>
                </tr>
                <tr>
                  <td>Temperature</td>
                  <td>{{ formatTemperature(stats.temperature.avg) }}</td>
                  <td>{{ formatTemperature(stats.temperature.min) }}</td>
                  <td>{{ formatTemperature(stats.temperature.max) }}</td>
                </tr>
                <tr>
                  <td>Power Consumption</td>
                  <td>{{ stats.power.avg.toFixed(1) }}W</td>
                  <td>{{ stats.power.min.toFixed(1) }}W</td>
                  <td>{{ stats.power.max.toFixed(1) }}W</td>
                </tr>
                <tr>
                  <td>Accepted Shares</td>
                  <td>{{ stats.shares.accepted }}</td>
                  <td>-</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Rejected Shares</td>
                  <td>{{ stats.shares.rejected }}</td>
                  <td>-</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Efficiency</td>
                  <td>{{ calculateEfficiency(stats.hashrate.avg, stats.power.avg) }}</td>
                  <td>-</td>
                  <td>-</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useMinersStore } from "../stores/miners";
import { addMessageHandler, removeMessageHandler, updateSubscriptions } from "../services/websocket";
import Chart from "chart.js/auto";
import { format } from "date-fns";
import { formatTemperature } from "../utils/formatters";

export default {
  name: "Analytics",

  setup() {
    const minersStore = useMinersStore();

    // Charts
    const hashrateChart = ref(null);
    const temperatureChart = ref(null);
    const sharesChart = ref(null);
    const powerChart = ref(null);

    // Chart instances
    let hashrateChartInstance = null;
    let temperatureChartInstance = null;
    let sharesChartInstance = null;
    let powerChartInstance = null;

    // Throttling for real-time updates
    let lastUpdateTime = 0;
    const UPDATE_THROTTLE_MS = 1000; // Max 1 update per second
    let pendingUpdates = new Map(); // Store pending updates by miner_id

    // Time range and increment
    const selectedTimeRange = ref("24h");
    const selectedIncrement = ref("5m");

    // Miner selection
    const selectedMiners = ref([]);
    const compareMiners = ref(false);

    // Data
    const metricsData = ref({});
    const loading = ref(false);
    const hasData = ref(false);

    // Statistics
    const stats = ref({
      hashrate: { avg: 0, min: 0, max: 0 },
      temperature: { avg: 0, min: 0, max: 0 },
      power: { avg: 0, min: 0, max: 0 },
      shares: { accepted: 0, rejected: 0 },
    });

    // Computed properties
    const miners = computed(() => minersStore.miners);
    const minerOptions = computed(() => {
      return miners.value.map((miner) => ({
        id: miner.id,
        name: miner.name || `${miner.type} (${miner.ip_address})`,
      }));
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

    const calculateEfficiency = (hashrate, power) => {
      // Validate inputs
      if (!hashrate || !power || power === 0) return "N/A";

      // Convert hashrate from H/s to TH/s (1 TH = 10^12 H)
      const hashrateInTH = hashrate / 1000000000000;

      if (hashrateInTH === 0) return "N/A";

      // Calculate efficiency as watts per terahash (W/TH)
      // Lower values indicate better efficiency
      const efficiency = power / hashrateInTH;

      return `${efficiency.toFixed(2)} W/TH`;
    };

    const getTimeRange = () => {
      const now = new Date();
      let start, end;

      switch (selectedTimeRange.value) {
        case "1h":
          start = new Date(now.getTime() - 60 * 60 * 1000);
          end = now;
          break;
        case "24h":
          start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          end = now;
          break;
        case "7d":
          start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          end = now;
          break;
        case "30d":
          start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          end = now;
          break;
        case "all":
          // Get all available data (start from 90 days ago as a reasonable limit)
          start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
          end = now;
          break;
        default:
          start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          end = now;
      }

      return { start, end };
    };

    const getInterval = () => {
      // Use the selected increment directly
      return selectedIncrement.value;
    };

    /**
     * Get valid increments for the current time range
     */
    const getValidIncrementsForRange = () => {
      const rangeIncrementMap = {
        '1h': ['1m', '15m'],
        '24h': ['15m', '1h'],
        '7d': ['1h', '1d'],
        '30d': ['1d'],
        'all': ['1d']
      };
      
      return rangeIncrementMap[selectedTimeRange.value] || ['1h'];
    };

    /**
     * Check if an increment is valid for the current time range
     */
    const isIncrementValid = (increment) => {
      const validIncrements = getValidIncrementsForRange();
      return validIncrements.includes(increment);
    };

    /**
     * Auto-adjust increment when range changes to ensure valid combination
     */
    const adjustIncrementForRange = () => {
      const validIncrements = getValidIncrementsForRange();
      
      // If current increment is not valid for the new range, select the first valid one
      if (!validIncrements.includes(selectedIncrement.value)) {
        selectedIncrement.value = validIncrements[0];
        console.log(`Auto-adjusted increment to ${selectedIncrement.value} for range ${selectedTimeRange.value}`);
      }
    };

    /**
     * Handle time range change - auto-adjust increment and fetch data
     */
    const onTimeRangeChange = async (newRange) => {
      console.log('Time range changed to:', newRange);
      selectedTimeRange.value = newRange;
      
      // Auto-adjust increment if needed
      adjustIncrementForRange();
      
      // Fetch data immediately
      if (selectedMiners.value.length > 0) {
        await fetchMetricsData();
      }
    };

    /**
     * Handle increment change - fetch data immediately
     */
    const onIncrementChange = async (newIncrement) => {
      console.log('Time increment changed to:', newIncrement);
      selectedIncrement.value = newIncrement;
      
      // Fetch data immediately
      if (selectedMiners.value.length > 0) {
        await fetchMetricsData();
      }
    };

    const transformMetricsData = (aggregatedData) => {
      // Transform aggregated API response into time-series format
      // Group by time_bucket first
      const timeSeriesMap = {};

      for (const item of aggregatedData) {
        const timestamp = item.time_bucket;
        if (!timeSeriesMap[timestamp]) {
          timeSeriesMap[timestamp] = { timestamp };
        }

        // Map metric_type to the expected field names
        switch (item.metric_type) {
          case "hashrate":
          case "hashrate_average":  // Backend stores as hashrate_average
          case "hashrate_current":  // Also accept current hashrate
            // Use average hashrate if available, otherwise use current
            if (item.metric_type === "hashrate_average" || item.metric_type === "hashrate") {
              timeSeriesMap[timestamp].hashrate = item.avg_value;
            } else if (!timeSeriesMap[timestamp].hashrate) {
              // Only use current if average not already set
              timeSeriesMap[timestamp].hashrate = item.avg_value;
            }
            break;
          case "temperature":
            timeSeriesMap[timestamp].temperature = item.avg_value;
            break;
          case "power":
            timeSeriesMap[timestamp].power = item.avg_value;
            break;
          case "shares_accepted":
            timeSeriesMap[timestamp].shares_accepted = item.avg_value;
            break;
          case "shares_rejected":
            timeSeriesMap[timestamp].shares_rejected = item.avg_value;
            break;
        }
      }

      // Convert map to sorted array
      return Object.values(timeSeriesMap).sort(
        (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
      );
    };

    const fetchMetricsData = async () => {
      loading.value = true;
      hasData.value = false;

      try {
        const { start, end } = getTimeRange();
        const interval = getInterval();

        // Clear previous data
        metricsData.value = {};

        // Fetch data for each selected miner
        for (const minerId of selectedMiners.value) {
          const metrics = await minersStore.fetchMinerMetrics(
            minerId,
            start.toISOString(),
            end.toISOString(),
            interval,
          );

          // Transform the aggregated data into time-series format
          metricsData.value[minerId] = transformMetricsData(metrics);
          
          // Debug: Log transformed data
          if (metricsData.value[minerId] && metricsData.value[minerId].length > 0) {
            console.log(`Transformed metrics for ${minerId}:`, metricsData.value[minerId][0]);
          }
        }

        // Check if we have data
        hasData.value = Object.values(metricsData.value).some(
          (metrics) => metrics && metrics.length > 0,
        );

        if (hasData.value) {
          // Calculate statistics
          calculateStats();

          // Wait for DOM to update before creating charts
          await nextTick();
          // Wait one more tick to ensure refs are populated
          await nextTick();

          // Update charts
          updateCharts();
        }
      } catch (error) {
        console.error("Error fetching metrics data:", error);
      } finally {
        loading.value = false;
      }
    };

    const calculateStats = () => {
      // Reset stats
      stats.value = {
        hashrate: { avg: 0, min: Infinity, max: 0 },
        temperature: { avg: 0, min: Infinity, max: 0 },
        power: { avg: 0, min: Infinity, max: 0 },
        shares: { accepted: 0, rejected: 0 },
      };

      let totalHashrate = 0;
      let totalTemperature = 0;
      let totalPower = 0;
      let dataPointCount = 0;

      // Process each miner's data
      for (const minerId in metricsData.value) {
        const minerMetrics = metricsData.value[minerId];

        if (!minerMetrics || minerMetrics.length === 0) continue;

        for (const metric of minerMetrics) {
          // Hashrate
          if (metric.hashrate !== undefined) {
            totalHashrate += metric.hashrate;
            stats.value.hashrate.min = Math.min(
              stats.value.hashrate.min,
              metric.hashrate,
            );
            stats.value.hashrate.max = Math.max(
              stats.value.hashrate.max,
              metric.hashrate,
            );
          }

          // Temperature
          if (metric.temperature !== undefined) {
            totalTemperature += metric.temperature;
            stats.value.temperature.min = Math.min(
              stats.value.temperature.min,
              metric.temperature,
            );
            stats.value.temperature.max = Math.max(
              stats.value.temperature.max,
              metric.temperature,
            );
          }

          // Power
          if (metric.power !== undefined) {
            totalPower += metric.power;
            stats.value.power.min = Math.min(
              stats.value.power.min,
              metric.power,
            );
            stats.value.power.max = Math.max(
              stats.value.power.max,
              metric.power,
            );
          }

          // Shares
          if (metric.shares_accepted !== undefined) {
            stats.value.shares.accepted += metric.shares_accepted;
          }
          if (metric.shares_rejected !== undefined) {
            stats.value.shares.rejected += metric.shares_rejected;
          }
        }

        dataPointCount += minerMetrics.length;
      }

      // Calculate averages
      if (dataPointCount > 0) {
        stats.value.hashrate.avg = totalHashrate / dataPointCount;
        stats.value.temperature.avg = totalTemperature / dataPointCount;
        stats.value.power.avg = totalPower / dataPointCount;
      }

      // Handle case where no min was found
      if (stats.value.hashrate.min === Infinity) stats.value.hashrate.min = 0;
      if (stats.value.temperature.min === Infinity)
        stats.value.temperature.min = 0;
      if (stats.value.power.min === Infinity) stats.value.power.min = 0;
    };

    const updateCharts = () => {
      // Debug: Check if refs are available
      console.log("Chart refs:", {
        hashrate: hashrateChart.value,
        temperature: temperatureChart.value,
        shares: sharesChart.value,
        power: powerChart.value,
      });

      // Check if all canvas refs are available
      if (
        !hashrateChart.value ||
        !temperatureChart.value ||
        !sharesChart.value ||
        !powerChart.value
      ) {
        console.error("Canvas refs not available yet, retrying...");
        // Retry after a short delay
        setTimeout(() => {
          updateCharts();
        }, 100);
        return;
      }

      // Destroy previous chart instances
      if (hashrateChartInstance) hashrateChartInstance.destroy();
      if (temperatureChartInstance) temperatureChartInstance.destroy();
      if (sharesChartInstance) sharesChartInstance.destroy();
      if (powerChartInstance) powerChartInstance.destroy();

      // Prepare chart data
      const labels = [];
      const hashrateDatasets = [];
      const temperatureDatasets = [];
      const sharesDatasets = [];
      const powerDatasets = [];

      // Generate a color for each miner
      const colors = [
        "rgba(75, 192, 192, 1)",
        "rgba(255, 99, 132, 1)",
        "rgba(54, 162, 235, 1)",
        "rgba(255, 206, 86, 1)",
        "rgba(153, 102, 255, 1)",
        "rgba(255, 159, 64, 1)",
      ];

      // Process each miner's data
      let minerIndex = 0;
      for (const minerId in metricsData.value) {
        const minerMetrics = metricsData.value[minerId];
        const miner = miners.value.find((m) => m.id === minerId);
        const minerName = miner
          ? miner.name || `${miner.type} (${miner.ip_address})`
          : minerId;
        const color = colors[minerIndex % colors.length];

        if (!minerMetrics || minerMetrics.length === 0) continue;

        // Prepare data arrays
        const hashrateData = [];
        const temperatureData = [];
        const sharesAcceptedData = [];
        const sharesRejectedData = [];
        const powerData = [];
        const timestamps = [];

        // Extract data
        for (const metric of minerMetrics) {
          // Format timestamp as string for display
          const date = new Date(metric.timestamp);
          const formattedTime = format(date, "MMM d, HH:mm");
          timestamps.push(formattedTime);
          hashrateData.push(metric.hashrate || 0);
          temperatureData.push(metric.temperature || 0);
          sharesAcceptedData.push(metric.shares_accepted || 0);
          sharesRejectedData.push(metric.shares_rejected || 0);
          powerData.push(metric.power || 0);
        }

        // Add datasets
        hashrateDatasets.push({
          label: `${minerName} - Hashrate`,
          data: hashrateData,
          borderColor: color,
          backgroundColor: color.replace("1)", "0.2)"),
          fill: false,
          tension: 0.1,
        });

        temperatureDatasets.push({
          label: `${minerName} - Temperature`,
          data: temperatureData,
          borderColor: color,
          backgroundColor: color.replace("1)", "0.2)"),
          fill: false,
          tension: 0.1,
        });

        sharesDatasets.push({
          label: `${minerName} - Accepted Shares`,
          data: sharesAcceptedData,
          borderColor: color,
          backgroundColor: color.replace("1)", "0.2)"),
          fill: false,
          tension: 0.1,
        });

        sharesDatasets.push({
          label: `${minerName} - Rejected Shares`,
          data: sharesRejectedData,
          borderColor: "rgba(255, 99, 132, 1)",
          backgroundColor: "rgba(255, 99, 132, 0.2)",
          fill: false,
          tension: 0.1,
        });

        powerDatasets.push({
          label: `${minerName} - Power`,
          data: powerData,
          borderColor: color,
          backgroundColor: color.replace("1)", "0.2)"),
          fill: false,
          tension: 0.1,
        });

        // Use the timestamps from the first miner as labels
        if (minerIndex === 0) {
          labels.push(...timestamps);
        }

        minerIndex++;
      }

      // Create charts
      try {
        hashrateChartInstance = new Chart(hashrateChart.value, {
        type: "line",
        data: {
          labels,
          datasets: hashrateDatasets,
        },
        options: {
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: "Hashrate Over Time",
            },
            tooltip: {
              callbacks: {
                label(context) {
                  return `${context.dataset.label}: ${formatHashrate(context.parsed.y)}`;
                },
              },
            },
          },
          scales: {
            x: {
              title: {
                display: true,
                text: "Time",
              },
            },
            y: {
              title: {
                display: true,
                text: "Hashrate",
              },
            },
          },
        },
      });
      } catch (error) {
        console.error("Failed to create hashrate chart:", error);
      }

      try {
        temperatureChartInstance = new Chart(temperatureChart.value, {
        type: "line",
        data: {
          labels,
          datasets: temperatureDatasets,
        },
        options: {
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: "Temperature Over Time",
            },
            tooltip: {
              callbacks: {
                label(context) {
                  return `${context.dataset.label}: ${Math.round(context.parsed.y)}°C`;
                },
              },
            },
          },
          scales: {
            x: {
              title: {
                display: true,
                text: "Time",
              },
            },
            y: {
              title: {
                display: true,
                text: "Temperature (°C)",
              },
            },
          },
        },
      });
      } catch (error) {
        console.error("Failed to create temperature chart:", error);
      }

      try {
        sharesChartInstance = new Chart(sharesChart.value, {
        type: "line",
        data: {
          labels,
          datasets: sharesDatasets,
        },
        options: {
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: "Shares Over Time",
            },
          },
          scales: {
            x: {
              title: {
                display: true,
                text: "Time",
              },
            },
            y: {
              title: {
                display: true,
                text: "Shares",
              },
            },
          },
        },
      });
      } catch (error) {
        console.error("Failed to create shares chart:", error);
      }

      try {
        powerChartInstance = new Chart(powerChart.value, {
        type: "line",
        data: {
          labels,
          datasets: powerDatasets,
        },
        options: {
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: "Power Consumption Over Time",
            },
            tooltip: {
              callbacks: {
                label(context) {
                  return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}W`;
                },
              },
            },
          },
          scales: {
            x: {
              title: {
                display: true,
                text: "Time",
              },
            },
            y: {
              title: {
                display: true,
                text: "Power (W)",
              },
            },
          },
        },
      });
      } catch (error) {
        console.error("Failed to create power chart:", error);
      }
    };

    const getTimeUnit = () => {
      const { start, end } = getTimeRange();
      const diff = end.getTime() - start.getTime();

      if (diff <= 60 * 1000) return "second"; // For <= 1 minute
      if (diff <= 15 * 60 * 1000) return "second"; // For <= 15 minutes
      if (diff <= 60 * 60 * 1000) return "minute"; // For <= 1 hour
      if (diff <= 24 * 60 * 60 * 1000) return "hour"; // For <= 24 hours
      if (diff <= 7 * 24 * 60 * 60 * 1000) return "day"; // For <= 7 days
      return "week"; // For > 7 days
    };



    const exportData = (data, filename) => {
      // Convert data to CSV
      const csvContent = `data:text/csv;charset=utf-8,${data}`;

      // Create download link
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", filename);
      document.body.appendChild(link);

      // Trigger download
      link.click();

      // Clean up
      document.body.removeChild(link);
    };

    const exportHashrateData = () => {
      // Prepare CSV header
      let csv = "Timestamp,Miner,Hashrate\n";

      // Add data rows
      for (const minerId in metricsData.value) {
        const minerMetrics = metricsData.value[minerId];
        const miner = miners.value.find((m) => m.id === minerId);
        const minerName = miner
          ? miner.name || `${miner.type} (${miner.ip_address})`
          : minerId;

        if (!minerMetrics) continue;

        for (const metric of minerMetrics) {
          csv += `${metric.timestamp},${minerName},${metric.hashrate || 0}\n`;
        }
      }

      // Export
      exportData(csv, "hashrate_data.csv");
    };

    const exportTemperatureData = () => {
      // Prepare CSV header
      let csv = "Timestamp,Miner,Temperature\n";

      // Add data rows
      for (const minerId in metricsData.value) {
        const minerMetrics = metricsData.value[minerId];
        const miner = miners.value.find((m) => m.id === minerId);
        const minerName = miner
          ? miner.name || `${miner.type} (${miner.ip_address})`
          : minerId;

        if (!minerMetrics) continue;

        for (const metric of minerMetrics) {
          csv += `${metric.timestamp},${minerName},${metric.temperature || 0}\n`;
        }
      }

      // Export
      exportData(csv, "temperature_data.csv");
    };

    const exportSharesData = () => {
      // Prepare CSV header
      let csv = "Timestamp,Miner,Accepted Shares,Rejected Shares\n";

      // Add data rows
      for (const minerId in metricsData.value) {
        const minerMetrics = metricsData.value[minerId];
        const miner = miners.value.find((m) => m.id === minerId);
        const minerName = miner
          ? miner.name || `${miner.type} (${miner.ip_address})`
          : minerId;

        if (!minerMetrics) continue;

        for (const metric of minerMetrics) {
          csv += `${metric.timestamp},${minerName},${metric.shares_accepted || 0},${metric.shares_rejected || 0}\n`;
        }
      }

      // Export
      exportData(csv, "shares_data.csv");
    };

    const exportPowerData = () => {
      // Prepare CSV header
      let csv = "Timestamp,Miner,Power\n";

      // Add data rows
      for (const minerId in metricsData.value) {
        const minerMetrics = metricsData.value[minerId];
        const miner = miners.value.find((m) => m.id === minerId);
        const minerName = miner
          ? miner.name || `${miner.type} (${miner.ip_address})`
          : minerId;

        if (!minerMetrics) continue;

        for (const metric of minerMetrics) {
          csv += `${metric.timestamp},${minerName},${metric.power || 0}\n`;
        }
      }

      // Export
      exportData(csv, "power_data.csv");
    };

    /**
     * Handle real-time metrics updates from WebSocket
     * @param {Object} message - WebSocket message
     */
    const handleMetricsUpdate = (message) => {
      // Only process metrics_update messages
      if (message.type !== 'metrics_update') {
        return;
      }

      const { miner_id, metrics, timestamp } = message.data || {};
      
      // Only update if this miner is currently selected
      if (!selectedMiners.value.includes(miner_id)) {
        return;
      }

      // Store the update for throttled processing
      pendingUpdates.set(miner_id, { metrics, timestamp });

      // Throttle updates to max 1 per second
      const now = Date.now();
      if (now - lastUpdateTime < UPDATE_THROTTLE_MS) {
        return;
      }

      lastUpdateTime = now;
      processPendingUpdates();
    };

    /**
     * Process all pending metrics updates
     */
    const processPendingUpdates = () => {
      if (pendingUpdates.size === 0) {
        return;
      }

      // Process each pending update
      for (const [minerId, update] of pendingUpdates.entries()) {
        appendMetricsToCharts(minerId, update.metrics, update.timestamp);
      }

      // Clear pending updates
      pendingUpdates.clear();
    };

    /**
     * Append new metrics data to existing charts
     * @param {string} minerId - Miner ID
     * @param {Object} metrics - Metrics data
     * @param {string} timestamp - ISO timestamp
     */
    const appendMetricsToCharts = (minerId, metrics, timestamp) => {
      // Check if we have data for this miner
      if (!metricsData.value[minerId]) {
        metricsData.value[minerId] = [];
      }

      // Create new data point
      const newDataPoint = {
        timestamp,
        hashrate: metrics.hashrate || 0,
        temperature: metrics.temperature || 0,
        power: metrics.power || 0,
        shares_accepted: metrics.shares_accepted || 0,
        shares_rejected: metrics.shares_rejected || 0,
      };

      // Append to metrics data
      metricsData.value[minerId].push(newDataPoint);

      // Limit data points based on time range to prevent memory issues
      const maxDataPoints = getMaxDataPoints();
      if (metricsData.value[minerId].length > maxDataPoints) {
        metricsData.value[minerId].shift(); // Remove oldest data point
      }

      // Update charts with new data
      updateChartsWithNewData(minerId, newDataPoint);

      // Recalculate statistics
      calculateStats();
    };

    /**
     * Get maximum data points based on selected time range and increment
     */
    const getMaxDataPoints = () => {
      // Calculate based on range and increment
      const { start, end } = getTimeRange();
      const rangeDuration = end.getTime() - start.getTime();
      
      // Convert increment to milliseconds
      let incrementMs;
      switch (selectedIncrement.value) {
        case '1m': incrementMs = 60 * 1000; break;
        case '15m': incrementMs = 15 * 60 * 1000; break;
        case '1h': incrementMs = 60 * 60 * 1000; break;
        case '1d': incrementMs = 24 * 60 * 60 * 1000; break;
        default: incrementMs = 60 * 60 * 1000;
      }
      
      // Calculate max points (add 10% buffer)
      return Math.ceil((rangeDuration / incrementMs) * 1.1);
    };

    /**
     * Update charts with new data point while preserving view/zoom
     * @param {string} minerId - Miner ID
     * @param {Object} dataPoint - New data point
     */
    const updateChartsWithNewData = (minerId, dataPoint) => {
      if (!hashrateChartInstance || !temperatureChartInstance || 
          !sharesChartInstance || !powerChartInstance) {
        return;
      }

      // Format timestamp for display
      const date = new Date(dataPoint.timestamp);
      const formattedTime = format(date, 'MMM d, HH:mm');

      // Find the dataset index for this miner
      const miner = miners.value.find(m => m.id === minerId);
      if (!miner) return;

      const minerName = miner.name || `${miner.type} (${miner.ip_address})`;

      // Update hashrate chart
      const hashrateDataset = hashrateChartInstance.data.datasets.find(
        ds => ds.label === `${minerName} - Hashrate`
      );
      if (hashrateDataset) {
        hashrateChartInstance.data.labels.push(formattedTime);
        hashrateDataset.data.push(dataPoint.hashrate);
        
        // Remove oldest data point if exceeding max
        const maxPoints = getMaxDataPoints();
        if (hashrateChartInstance.data.labels.length > maxPoints) {
          hashrateChartInstance.data.labels.shift();
          hashrateDataset.data.shift();
        }
        
        hashrateChartInstance.update('none'); // 'none' mode preserves zoom/pan
      }

      // Update temperature chart
      const temperatureDataset = temperatureChartInstance.data.datasets.find(
        ds => ds.label === `${minerName} - Temperature`
      );
      if (temperatureDataset) {
        temperatureChartInstance.data.labels.push(formattedTime);
        temperatureDataset.data.push(dataPoint.temperature);
        
        const maxPoints = getMaxDataPoints();
        if (temperatureChartInstance.data.labels.length > maxPoints) {
          temperatureChartInstance.data.labels.shift();
          temperatureDataset.data.shift();
        }
        
        temperatureChartInstance.update('none');
      }

      // Update shares chart (both accepted and rejected)
      const sharesAcceptedDataset = sharesChartInstance.data.datasets.find(
        ds => ds.label === `${minerName} - Accepted Shares`
      );
      const sharesRejectedDataset = sharesChartInstance.data.datasets.find(
        ds => ds.label === `${minerName} - Rejected Shares`
      );
      
      if (sharesAcceptedDataset || sharesRejectedDataset) {
        sharesChartInstance.data.labels.push(formattedTime);
        
        if (sharesAcceptedDataset) {
          sharesAcceptedDataset.data.push(dataPoint.shares_accepted);
        }
        if (sharesRejectedDataset) {
          sharesRejectedDataset.data.push(dataPoint.shares_rejected);
        }
        
        const maxPoints = getMaxDataPoints();
        if (sharesChartInstance.data.labels.length > maxPoints) {
          sharesChartInstance.data.labels.shift();
          if (sharesAcceptedDataset) sharesAcceptedDataset.data.shift();
          if (sharesRejectedDataset) sharesRejectedDataset.data.shift();
        }
        
        sharesChartInstance.update('none');
      }

      // Update power chart
      const powerDataset = powerChartInstance.data.datasets.find(
        ds => ds.label === `${minerName} - Power`
      );
      if (powerDataset) {
        powerChartInstance.data.labels.push(formattedTime);
        powerDataset.data.push(dataPoint.power);
        
        const maxPoints = getMaxDataPoints();
        if (powerChartInstance.data.labels.length > maxPoints) {
          powerChartInstance.data.labels.shift();
          powerDataset.data.shift();
        }
        
        powerChartInstance.update('none');
      }
    };

    // Watch for changes
    watch(selectedMiners, () => {
      if (selectedMiners.value.length > 0) {
        fetchMetricsData();
      }
    });

    // Lifecycle hooks
    onMounted(async () => {
      // Register WebSocket message handler for real-time updates
      addMessageHandler(handleMetricsUpdate);
      console.log('Analytics view: Registered WebSocket message handler for metrics updates');
      
      // Subscribe to metrics topic to receive real-time updates
      updateSubscriptions({ metrics: true });
      console.log('Analytics view: Subscribed to metrics topic');
      
      // Fetch miners
      await minersStore.fetchMiners();

      // Select all miners by default (this will trigger the watcher which calls fetchMetricsData)
      selectedMiners.value = miners.value.map((miner) => miner.id);
    });

    onUnmounted(() => {
      // Unsubscribe from metrics topic
      updateSubscriptions({ metrics: false });
      console.log('Analytics view: Unsubscribed from metrics topic');
      
      // Unregister WebSocket message handler
      removeMessageHandler(handleMetricsUpdate);
      console.log('Analytics view: Unregistered WebSocket message handler');
      
      // Destroy chart instances
      if (hashrateChartInstance) hashrateChartInstance.destroy();
      if (temperatureChartInstance) temperatureChartInstance.destroy();
      if (sharesChartInstance) sharesChartInstance.destroy();
      if (powerChartInstance) powerChartInstance.destroy();
    });

    return {
      // Refs
      hashrateChart,
      temperatureChart,
      sharesChart,
      powerChart,
      selectedTimeRange,
      selectedIncrement,
      selectedMiners,
      compareMiners,
      loading,
      hasData,
      stats,

      // Computed
      minerOptions,

      // Methods
      formatHashrate,
      calculateEfficiency,
      formatTemperature,
      isIncrementValid,
      onTimeRangeChange,
      onIncrementChange,
      exportHashrateData,
      exportTemperatureData,
      exportSharesData,
      exportPowerData,
    };
  },
};
</script>