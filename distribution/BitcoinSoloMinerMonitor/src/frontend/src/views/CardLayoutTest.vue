<template>
  <div class="card-layout-test">
    <div class="test-header">
      <h1 class="text-h1">Card & Layout Components Test</h1>
      <p class="text-secondary">
        Testing the enhanced card system, navigation components, data tables,
        and status indicators with Bitcoin Orange theming and accessibility
        features.
      </p>
    </div>

    <CardLayoutDemo />

    <!-- Additional Integration Tests -->
    <div class="integration-tests">
      <h2 class="text-h2 mb-lg">Integration Examples</h2>

      <!-- Miner Dashboard Cards -->
      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Miner Dashboard Layout</h3>
        <div class="card-grid">
          <!-- Summary Card -->
          <div class="card-component card-bitcoin card-elevated-2">
            <div class="card-header">
              <h4 class="card-title">
                Fleet Summary
              </h4>
            </div>
            <div class="card-content">
              <div class="summary-stats">
                <div class="stat-item">
                  <div class="stat-value text-h2 text-bitcoin">4</div>
                  <div class="stat-label text-small text-secondary">
                    Total Miners
                  </div>
                </div>
                <div class="stat-item">
                  <div class="stat-value text-h2 text-success">3</div>
                  <div class="stat-label text-small text-secondary">Online</div>
                </div>
                <div class="stat-item">
                  <div class="stat-value text-h2 text-error">1</div>
                  <div class="stat-label text-small text-secondary">
                    Offline
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Performance Card -->
          <div class="card-component card-success card-interactive">
            <div class="card-header">
              <h4 class="card-title">Performance</h4>
              <div class="status-indicator status-online">
                <div class="status-indicator-icon online"></div>
                Optimal
              </div>
            </div>
            <div class="card-content">
              <div class="performance-metrics">
                <div class="metric">
                  <div class="metric-label text-small text-secondary">
                    Total Hashrate
                  </div>
                  <div class="metric-value text-h3">3.1 TH/s</div>
                </div>
                <div class="metric">
                  <div class="metric-label text-small text-secondary">
                    Avg Temperature
                  </div>
                  <div class="metric-value text-h3">67°C</div>
                </div>
              </div>
            </div>
            <div class="card-actions">
              <button class="btn btn-primary">View Details</button>
            </div>
          </div>

          <!-- Alerts Card -->
          <div class="card-component card-warning">
            <div class="card-header">
              <h4 class="card-title">Alerts</h4>
              <div class="status-indicator status-warning">
                <div class="status-indicator-icon warning"></div>
                1 Alert
              </div>
            </div>
            <div class="card-content">
              <div class="alert-item">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                  <div class="alert-title">High Temperature</div>
                  <div class="alert-description text-small text-secondary">
                    Bitaxe Ultra #2 running at 78°C
                  </div>
                </div>
              </div>
            </div>
            <div class="card-actions">
              <button class="btn btn-secondary">View All</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Enhanced Table with Actions -->
      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Advanced Data Table</h3>
        <div class="card-component">
          <div class="card-header">
            <h4 class="card-title">Miner Management</h4>
            <div class="card-actions">
              <button class="btn btn-secondary btn-small">Export</button>
              <button class="btn btn-primary btn-small">
                Add Miner
              </button>
            </div>
          </div>
          <div class="card-content">
            <table class="data-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      @change="toggleSelectAll"
                      :checked="allSelected"
                    />
                  </th>
                  <th class="sortable sorted-desc">Name</th>
                  <th class="sortable">Type</th>
                  <th class="sortable">Status</th>
                  <th class="sortable numeric">Hashrate</th>
                  <th class="sortable numeric">Temperature</th>
                  <th class="sortable">Uptime</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="miner in detailedMiners"
                  :key="miner.id"
                  :class="{ selected: miner.selected }"
                >
                  <td>
                    <input type="checkbox" v-model="miner.selected" />
                  </td>
                  <td>
                    <div
                      class="d-flex align-center"
                      style="gap: var(--spacing-sm)"
                    >

                      <div>
                        <div class="font-medium">{{ miner.name }}</div>
                        <div class="text-small text-secondary">
                          {{ miner.ip }}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>{{ miner.type }}</td>
                  <td>
                    <div
                      class="status-indicator"
                      :class="getStatusClass(miner.status)"
                    >
                      <div
                        class="status-indicator-icon"
                        :class="miner.status"
                      ></div>
                      {{ miner.status }}
                    </div>
                  </td>
                  <td class="numeric">{{ miner.hashrate }}</td>
                  <td class="numeric">
                    <span :class="getTemperatureClass(miner.temperature)">
                      {{ formatTemperature(miner.temperature) }}
                    </span>
                  </td>
                  <td>{{ miner.uptime }}</td>
                  <td class="actions">
                    <button
                      class="btn btn-ghost btn-small"
                      title="View Details"
                    >
                      👁️
                    </button>
                    <button
                      class="btn btn-ghost btn-small"
                      title="Restart"
                      :disabled="miner.status === 'offline'"
                    >
                      🔄
                    </button>
                    <button class="btn btn-ghost btn-small" title="Settings">
                      ⚙️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="card-actions card-actions-between">
            <div class="text-small text-secondary">
              {{ selectedCount }} of {{ detailedMiners.length }} selected
            </div>
            <div class="d-flex" style="gap: var(--spacing-sm)">
              <button
                class="btn btn-secondary btn-small"
                :disabled="selectedCount === 0"
              >
                Restart Selected
              </button>
              <button
                class="btn btn-error btn-small"
                :disabled="selectedCount === 0"
              >
                Remove Selected
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Status Dashboard -->
      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Status Dashboard</h3>
        <div class="status-dashboard">
          <div class="status-section">
            <h4 class="text-h4 mb-md">System Status</h4>
            <div class="status-grid">
              <div class="status-card">
                <div class="status-indicator status-indicator-lg status-online">
                  <div class="status-indicator-icon online"></div>
                  API Server
                </div>
              </div>
              <div class="status-card">
                <div class="status-indicator status-indicator-lg status-online">
                  <div class="status-indicator-icon online"></div>
                  WebSocket
                </div>
              </div>
              <div class="status-card">
                <div
                  class="status-indicator status-indicator-lg status-warning"
                >
                  <div class="status-indicator-icon warning"></div>
                  Database
                </div>
              </div>
              <div class="status-card">
                <div
                  class="status-indicator status-indicator-lg status-offline"
                >
                  <div class="status-indicator-icon offline"></div>
                  Pool Connection
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from "vue";
import CardLayoutDemo from "../components/CardLayoutDemo.vue";
import { formatTemperature } from "../utils/formatters";

export default {
  name: "CardLayoutTest",
  components: {
    CardLayoutDemo,
  },
  setup() {
    const detailedMiners = ref([
      {
        id: 1,
        name: "Bitaxe Ultra #1",
        ip: "192.168.1.100",
        type: "Bitaxe Ultra",
        status: "online",
        hashrate: "1.2 TH/s",
        temperature: 65,
        uptime: "2d 14h",
        selected: false,
      },
      {
        id: 2,
        name: "Bitaxe Ultra #2",
        ip: "192.168.1.101",
        type: "Bitaxe Ultra",
        status: "warning",
        hashrate: "1.1 TH/s",
        temperature: 78,
        uptime: "1d 8h",
        selected: true,
      },
      {
        id: 3,
        name: "Avalon Nano #1",
        ip: "192.168.1.102",
        type: "Avalon Nano",
        status: "offline",
        hashrate: "0 H/s",
        temperature: 25,
        uptime: "0h",
        selected: false,
      },
      {
        id: 4,
        name: "Magic Miner #1",
        ip: "192.168.1.103",
        type: "Magic Miner",
        status: "online",
        hashrate: "800 GH/s",
        temperature: 62,
        uptime: "5d 2h",
        selected: false,
      },
      {
        id: 5,
        name: "Bitaxe Supra #1",
        ip: "192.168.1.104",
        type: "Bitaxe Supra",
        status: "online",
        hashrate: "900 GH/s",
        temperature: 58,
        uptime: "3d 16h",
        selected: false,
      },
    ]);

    const selectedCount = computed(() => {
      return detailedMiners.value.filter((miner) => miner.selected).length;
    });

    const allSelected = computed(() => {
      return (
        detailedMiners.value.length > 0 &&
        selectedCount.value === detailedMiners.value.length
      );
    });

    const getStatusClass = (status) => {
      const statusMap = {
        online: "status-online",
        offline: "status-offline",
        warning: "status-warning",
        error: "status-offline",
        unknown: "status-unknown",
      };
      return statusMap[status] || "status-unknown";
    };

    const getTemperatureClass = (temperature) => {
      if (temperature > 75) return "text-error";
      if (temperature > 65) return "text-warning";
      return "text-success";
    };

    const toggleSelectAll = () => {
      const newState = !allSelected.value;
      detailedMiners.value.forEach((miner) => {
        miner.selected = newState;
      });
    };

    return {
      detailedMiners,
      selectedCount,
      allSelected,
      getStatusClass,
      getTemperatureClass,
      formatTemperature,
      toggleSelectAll,
    };
  },
};
</script>

<style scoped>
.card-layout-test {
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
}

.test-header {
  margin-bottom: var(--spacing-xxl);
  text-align: center;
}

.integration-tests {
  margin-top: var(--spacing-xxl);
}

.demo-subsection {
  margin-bottom: var(--spacing-xl);
}

/* Summary Stats */
.summary-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-lg);
  text-align: center;
}

.stat-item {
  padding: var(--spacing-md);
}

.stat-value {
  margin-bottom: var(--spacing-xs);
}

/* Performance Metrics */
.performance-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-lg);
}

.metric {
  text-align: center;
  padding: var(--spacing-md);
}

.metric-value {
  margin-top: var(--spacing-xs);
}

/* Alert Item */
.alert-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
}

.alert-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--spacing-xs);
}

/* Status Dashboard */
.status-dashboard {
  margin-bottom: var(--spacing-xl);
}

.status-section {
  margin-bottom: var(--spacing-lg);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.status-card {
  padding: var(--spacing-md);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  text-align: center;
}

/* Responsive Design */
@media (max-width: 768px) {
  .card-layout-test {
    padding: var(--spacing-md);
  }

  .summary-stats {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }

  .performance-metrics {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .data-table {
    font-size: var(--font-size-small);
  }

  .data-table th,
  .data-table td {
    padding: var(--spacing-sm);
  }
}

@media (max-width: 480px) {
  .test-header h1 {
    font-size: var(--font-size-h2);
  }

  .card-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
