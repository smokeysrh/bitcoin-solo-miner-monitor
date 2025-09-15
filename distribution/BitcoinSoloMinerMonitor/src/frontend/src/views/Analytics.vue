<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Analytics</h1>
      </v-col>
    </v-row>

    <!-- Time Range Selector -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Time Range</v-card-title>
          <v-card-text>
            <v-btn-toggle
              v-model="selectedTimeRange"
              mandatory
              color="primary"
              class="mb-4"
            >
              <v-btn value="1h">1h</v-btn>
              <v-btn value="6h">6h</v-btn>
              <v-btn value="24h">24h</v-btn>
              <v-btn value="7d">7d</v-btn>
              <v-btn value="30d">30d</v-btn>
              <v-btn value="custom">Custom</v-btn>
            </v-btn-toggle>

            <v-row v-if="selectedTimeRange === 'custom'">
              <v-col cols="12" sm="6">
                <v-menu
                  ref="startDateMenu"
                  v-model="startDateMenu"
                  :close-on-content-click="false"
                  transition="scale-transition"
                  offset-y
                  min-width="auto"
                >
                  <template v-slot:activator="{ on, attrs }">
                    <v-text-field
                      v-model="startDate"
                      label="Start Date"
                      prepend-icon="mdi-calendar"
                      readonly
                      v-bind="attrs"
                      v-on="on"
                    ></v-text-field>
                  </template>
                  <v-date-picker
                    v-model="startDate"
                    @input="startDateMenu = false"
                  ></v-date-picker>
                </v-menu>
              </v-col>
              <v-col cols="12" sm="6">
                <v-menu
                  ref="endDateMenu"
                  v-model="endDateMenu"
                  :close-on-content-click="false"
                  transition="scale-transition"
                  offset-y
                  min-width="auto"
                >
                  <template v-slot:activator="{ on, attrs }">
                    <v-text-field
                      v-model="endDate"
                      label="End Date"
                      prepend-icon="mdi-calendar"
                      readonly
                      v-bind="attrs"
                      v-on="on"
                    ></v-text-field>
                  </template>
                  <v-date-picker
                    v-model="endDate"
                    @input="endDateMenu = false"
                  ></v-date-picker>
                </v-menu>
              </v-col>
            </v-row>

            <v-btn
              color="primary"
              @click="applyTimeRange"
              :disabled="loading"
              class="mt-4"
            >
              Apply
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Miner Selection</v-card-title>
          <v-card-text>
            <v-select
              v-model="selectedMiners"
              :items="minerOptions"
              item-text="name"
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
              style="height: 300px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 300px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="hashrateChart" height="300"></canvas>
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
              style="height: 300px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 300px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="temperatureChart" height="300"></canvas>
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
              style="height: 300px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 300px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="sharesChart" height="300"></canvas>
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
              style="height: 300px"
            >
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </div>
            <div
              v-else-if="!hasData"
              class="d-flex justify-center align-center"
              style="height: 300px"
            >
              <p class="text-subtitle-1">
                No data available for the selected time range
              </p>
            </div>
            <div v-else>
              <canvas ref="powerChart" height="300"></canvas>
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
            <v-simple-table>
              <template v-slot:default>
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
                    <td>
                      {{ (stats.hashrate.avg / stats.power.avg).toFixed(2) }}
                      H/W
                    </td>
                    <td>-</td>
                    <td>-</td>
                  </tr>
                </tbody>
              </template>
            </v-simple-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from "vue";
import { useMinersStore } from "../stores/miners";
import Chart from "chart.js/auto";
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

    // Time range
    const selectedTimeRange = ref("24h");
    const startDate = ref(
      new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().substr(0, 10),
    );
    const endDate = ref(new Date().toISOString().substr(0, 10));
    const startDateMenu = ref(false);
    const endDateMenu = ref(false);

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

    const getTimeRange = () => {
      const now = new Date();
      let start, end;

      switch (selectedTimeRange.value) {
        case "1h":
          start = new Date(now.getTime() - 60 * 60 * 1000);
          end = now;
          break;
        case "6h":
          start = new Date(now.getTime() - 6 * 60 * 60 * 1000);
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
        case "custom":
          start = new Date(startDate.value);
          end = new Date(endDate.value);
          end.setHours(23, 59, 59, 999); // End of day
          break;
        default:
          start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          end = now;
      }

      return { start, end };
    };

    const getInterval = () => {
      const { start, end } = getTimeRange();
      const diff = end.getTime() - start.getTime();

      if (diff <= 6 * 60 * 60 * 1000) return "1m"; // 1 minute for <= 6 hours
      if (diff <= 24 * 60 * 60 * 1000) return "5m"; // 5 minutes for <= 24 hours
      if (diff <= 7 * 24 * 60 * 60 * 1000) return "1h"; // 1 hour for <= 7 days
      return "1d"; // 1 day for > 7 days
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

          metricsData.value[minerId] = metrics;
        }

        // Check if we have data
        hasData.value = Object.values(metricsData.value).some(
          (metrics) => metrics && metrics.length > 0,
        );

        if (hasData.value) {
          // Calculate statistics
          calculateStats();

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
          timestamps.push(new Date(metric.timestamp));
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
              type: "time",
              time: {
                unit: getTimeUnit(),
              },
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
              type: "time",
              time: {
                unit: getTimeUnit(),
              },
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
              type: "time",
              time: {
                unit: getTimeUnit(),
              },
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
              type: "time",
              time: {
                unit: getTimeUnit(),
              },
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
    };

    const getTimeUnit = () => {
      const { start, end } = getTimeRange();
      const diff = end.getTime() - start.getTime();

      if (diff <= 6 * 60 * 60 * 1000) return "minute"; // For <= 6 hours
      if (diff <= 24 * 60 * 60 * 1000) return "hour"; // For <= 24 hours
      if (diff <= 7 * 24 * 60 * 60 * 1000) return "day"; // For <= 7 days
      return "week"; // For > 7 days
    };

    const applyTimeRange = () => {
      fetchMetricsData();
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

    // Watch for changes
    watch(selectedMiners, () => {
      if (selectedMiners.value.length > 0) {
        fetchMetricsData();
      }
    });

    // Lifecycle hooks
    onMounted(async () => {
      // Fetch miners
      await minersStore.fetchMiners();

      // Select all miners by default
      selectedMiners.value = miners.value.map((miner) => miner.id);

      // Fetch metrics data
      if (selectedMiners.value.length > 0) {
        fetchMetricsData();
      }
    });

    return {
      // Refs
      hashrateChart,
      temperatureChart,
      sharesChart,
      powerChart,
      selectedTimeRange,
      startDate,
      endDate,
      startDateMenu,
      endDateMenu,
      selectedMiners,
      compareMiners,
      loading,
      hasData,
      stats,

      // Computed
      minerOptions,

      // Methods
      formatHashrate,
      formatTemperature,
      applyTimeRange,
      exportHashrateData,
      exportTemperatureData,
      exportSharesData,
      exportPowerData,
    };
  },
};
</script>
