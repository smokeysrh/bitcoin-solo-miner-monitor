<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Analytics</h1>
        <p>Analytics charts are temporarily disabled while we fix some issues. The statistics summary below shows current data.</p>
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

    <!-- Charts Placeholder -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Charts</v-card-title>
          <v-card-text>
            <div class="d-flex justify-center align-center" style="height: 200px">
              <p class="text-subtitle-1">
                Charts are temporarily disabled. Please check back later.
              </p>
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
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useMinersStore } from "../stores/miners";
import { formatTemperature } from "../utils/formatters";

export default {
  name: "Analytics",

  setup() {
    const minersStore = useMinersStore();

    // Time range and increment
    const selectedTimeRange = ref("24h");
    const selectedIncrement = ref("15m");

    // Miner selection
    const selectedMiners = ref([]);
    const compareMiners = ref(false);

    // Data
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
    };

    /**
     * Handle increment change - fetch data immediately
     */
    const onIncrementChange = async (newIncrement) => {
      console.log('Time increment changed to:', newIncrement);
      selectedIncrement.value = newIncrement;
    };

    const calculateStats = () => {
      // Use current miner data to calculate basic stats
      const currentMiners = miners.value;
      
      if (!currentMiners || currentMiners.length === 0) {
        return;
      }

      let totalHashrate = 0;
      let totalTemperature = 0;
      let totalPower = 0;
      let minHashrate = Infinity;
      let maxHashrate = 0;
      let minTemperature = Infinity;
      let maxTemperature = 0;
      let minPower = Infinity;
      let maxPower = 0;
      let totalAcceptedShares = 0;
      let totalRejectedShares = 0;
      let validMiners = 0;

      for (const miner of currentMiners) {
        if (miner.status === 'online') {
          validMiners++;
          
          // Hashrate
          const hashrate = miner.hashrate || 0;
          totalHashrate += hashrate;
          minHashrate = Math.min(minHashrate, hashrate);
          maxHashrate = Math.max(maxHashrate, hashrate);
          
          // Temperature
          const temperature = miner.temperature || 0;
          totalTemperature += temperature;
          minTemperature = Math.min(minTemperature, temperature);
          maxTemperature = Math.max(maxTemperature, temperature);
          
          // Power
          const power = miner.power || 0;
          totalPower += power;
          minPower = Math.min(minPower, power);
          maxPower = Math.max(maxPower, power);
          
          // Shares (if available in miner data)
          if (miner.metrics) {
            totalAcceptedShares += miner.metrics.shares_accepted || 0;
            totalRejectedShares += miner.metrics.shares_rejected || 0;
          }
        }
      }

      // Update stats
      stats.value = {
        hashrate: {
          avg: validMiners > 0 ? totalHashrate / validMiners : 0,
          min: minHashrate === Infinity ? 0 : minHashrate,
          max: maxHashrate
        },
        temperature: {
          avg: validMiners > 0 ? totalTemperature / validMiners : 0,
          min: minTemperature === Infinity ? 0 : minTemperature,
          max: maxTemperature
        },
        power: {
          avg: validMiners > 0 ? totalPower / validMiners : 0,
          min: minPower === Infinity ? 0 : minPower,
          max: maxPower
        },
        shares: {
          accepted: totalAcceptedShares,
          rejected: totalRejectedShares
        }
      };
    };

    // Lifecycle hooks
    onMounted(async () => {
      // Fetch miners
      await minersStore.fetchMiners();

      // Select all miners by default
      selectedMiners.value = miners.value.map((miner) => miner.id);
      
      // Calculate initial stats
      calculateStats();
    });

    onUnmounted(() => {
      // Cleanup if needed
    });

    // Watch for miner changes to update stats
    watch(miners, () => {
      calculateStats();
    }, { deep: true });

    return {
      // Refs
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
    };
  },
};
</script>