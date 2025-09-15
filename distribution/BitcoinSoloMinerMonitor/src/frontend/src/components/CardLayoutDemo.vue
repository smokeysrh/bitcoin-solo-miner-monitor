<template>
  <div class="card-layout-demo">
    <div class="demo-section">
      <h2 class="text-h2 mb-lg">Card System Demo</h2>

      <!-- Card Elevation Levels -->
      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Card Elevation Levels</h3>
        <div class="card-grid card-grid-4">
          <div class="card-component card-flat">
            <div class="card-header">
              <h4 class="card-title">Flat Card</h4>
            </div>
            <div class="card-content">
              <p>No shadow, subtle border only.</p>
            </div>
          </div>

          <div class="card-component card-elevated-1">
            <div class="card-header">
              <h4 class="card-title">Elevation 1</h4>
            </div>
            <div class="card-content">
              <p>Basic shadow for subtle depth.</p>
            </div>
          </div>

          <div class="card-component card-elevated-2">
            <div class="card-header">
              <h4 class="card-title">Elevation 2</h4>
            </div>
            <div class="card-content">
              <p>Medium shadow with elevated surface.</p>
            </div>
          </div>

          <div class="card-component card-elevated-3">
            <div class="card-header">
              <h4 class="card-title">Elevation 3</h4>
            </div>
            <div class="card-content">
              <p>Higher shadow for prominent elements.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Card Variants -->
      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Card Variants</h3>
        <div class="card-grid card-grid-3">
          <div class="card-component card-primary card-interactive">
            <div class="card-header">
              <h4 class="card-title">
                Primary Card
              </h4>
            </div>
            <div class="card-content">
              <p>Bitcoin Orange accent with interactive hover effects.</p>
            </div>
            <div class="card-actions">
              <button class="btn btn-primary">Action</button>
            </div>
          </div>

          <div class="card-component card-success">
            <div class="card-header">
              <h4 class="card-title">Success Card</h4>
              <div class="status-indicator status-online">
                <div class="status-indicator-icon online"></div>
                Online
              </div>
            </div>
            <div class="card-content">
              <p>Success state with animated status indicator.</p>
            </div>
          </div>

          <div class="card-component card-warning">
            <div class="card-header">
              <h4 class="card-title">Warning Card</h4>
              <div class="status-indicator status-warning">
                <div class="status-indicator-icon warning"></div>
                Warning
              </div>
            </div>
            <div class="card-content">
              <p>Warning state with pulsing animation.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Bitcoin Card -->
      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Bitcoin Branded Card</h3>
        <div
          class="card-component card-bitcoin card-interactive card-elevated-2"
        >
          <div class="card-header">
            <h4 class="card-title">
              Bitcoin Miner Status
            </h4>
            <div class="status-indicator status-online">
              <div class="status-indicator-icon online"></div>
              Mining
            </div>
          </div>
          <div class="card-content">
            <div class="d-flex justify-between mb-md">
              <div>
                <div class="text-small text-secondary">Hashrate</div>
                <div class="text-h4 text-bitcoin">1.2 TH/s</div>
              </div>
              <div>
                <div class="text-small text-secondary">Temperature</div>
                <div class="text-h4">65°C</div>
              </div>
            </div>
            <p class="text-secondary">
              Bitcoin logo watermark appears on hover with subtle animation.
            </p>
          </div>
          <div class="card-actions card-actions-between">
            <button class="btn btn-secondary">Details</button>
            <button class="btn btn-primary">
              Restart
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Status Indicators Demo -->
    <div class="demo-section">
      <h2 class="text-h2 mb-lg">Status Indicators</h2>

      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Basic Status Indicators</h3>
        <div class="d-flex flex-wrap" style="gap: var(--spacing-md)">
          <div class="status-indicator status-online">
            <div class="status-indicator-icon online"></div>
            Online
          </div>
          <div class="status-indicator status-offline">
            <div class="status-indicator-icon offline"></div>
            Offline
          </div>
          <div class="status-indicator status-warning">
            <div class="status-indicator-icon warning"></div>
            Warning
          </div>
          <div class="status-indicator status-info">
            <div class="status-indicator-icon"></div>
            Info
          </div>
          <div class="status-indicator status-unknown">
            <div class="status-indicator-icon"></div>
            Unknown
          </div>
        </div>
      </div>

      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Large Status Indicators</h3>
        <div class="d-flex flex-wrap" style="gap: var(--spacing-md)">
          <div class="status-indicator status-indicator-lg status-online">
            <div class="status-indicator-icon online"></div>
            Mining Active
          </div>
          <div class="status-indicator status-indicator-lg status-warning">
            <div class="status-indicator-icon warning"></div>
            High Temperature
          </div>
          <div class="status-indicator status-indicator-lg status-offline">
            <div class="status-indicator-icon offline"></div>
            Connection Lost
          </div>
        </div>
      </div>
    </div>

    <!-- Data Table Demo -->
    <div class="demo-section">
      <h2 class="text-h2 mb-lg">Enhanced Data Table</h2>

      <div class="card-component">
        <div class="card-header">
          <h3 class="card-title">Miner Status Table</h3>
          <div class="status-indicator status-info">
            {{ miners.length }} miners
          </div>
        </div>
        <div class="card-content">
          <table class="data-table">
            <thead>
              <tr>
                <th class="sortable">Name</th>
                <th class="sortable">Status</th>
                <th class="sortable numeric">Hashrate</th>
                <th class="sortable numeric">Temperature</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="miner in miners"
                :key="miner.id"
                :class="{ selected: miner.selected }"
              >
                <td>
                  <div
                    class="d-flex align-center"
                    style="gap: var(--spacing-sm)"
                  >
                    {{ miner.name }}
                  </div>
                </td>
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
                <td class="numeric">{{ formatTemperature(miner.temperature) }}</td>
                <td class="actions">
                  <button class="btn btn-ghost btn-small">View</button>
                  <button class="btn btn-ghost btn-small">Restart</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Navigation Demo -->
    <div class="demo-section">
      <h2 class="text-h2 mb-lg">Navigation Components</h2>

      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Navigation Brand</h3>
        <div class="card-component">
          <div class="nav-brand">
            <div class="nav-brand-logo"></div>
            <div>
              <div class="nav-brand-text">Bitcoin Solo Miner Monitor</div>
              <div class="nav-brand-subtitle">Monitor your mining fleet</div>
            </div>
          </div>
        </div>
      </div>

      <div class="demo-subsection">
        <h3 class="text-h3 mb-md">Navigation Items</h3>
        <div class="card-component">
          <div class="nav-menu">
            <div class="nav-menu-section">
              <div class="nav-menu-title">Main Navigation</div>
              <a href="#" class="nav-item active">
                <div class="nav-item-icon">📊</div>
                <div class="nav-item-text">Dashboard</div>
              </a>
              <a href="#" class="nav-item">
                <div class="nav-item-icon">⛏️</div>
                <div class="nav-item-text">Miners</div>
                <div class="nav-item-badge">3</div>
              </a>
              <a href="#" class="nav-item">
                <div class="nav-item-icon">📈</div>
                <div class="nav-item-text">Analytics</div>
              </a>
              <a href="#" class="nav-item">
                <div class="nav-item-icon">🌐</div>
                <div class="nav-item-text">Network</div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from "vue";
import { formatTemperature } from "../utils/formatters";
export default {
  name: "CardLayoutDemo",
  setup() {
    const miners = ref([
      {
        id: 1,
        name: "Bitaxe Ultra #1",
        status: "online",
        hashrate: "1.2 TH/s",
        temperature: 65,
        selected: false,
      },
      {
        id: 2,
        name: "Bitaxe Ultra #2",
        status: "warning",
        hashrate: "1.1 TH/s",
        temperature: 78,
        selected: true,
      },
      {
        id: 3,
        name: "Avalon Nano #1",
        status: "offline",
        hashrate: "0 H/s",
        temperature: 25,
        selected: false,
      },
      {
        id: 4,
        name: "Magic Miner #1",
        status: "online",
        hashrate: "800 GH/s",
        temperature: 62,
        selected: false,
      },
    ]);

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

    return {
      miners,
      getStatusClass,
      formatTemperature,
    };
  },
};
</script>

<style scoped>
.card-layout-demo {
  padding: var(--spacing-lg);
  max-width: 1200px;
  margin: 0 auto;
}

.demo-section {
  margin-bottom: var(--spacing-xxl);
}

.demo-subsection {
  margin-bottom: var(--spacing-xl);
}

/* Demo-specific styles */
.demo-subsection .card-grid {
  margin-bottom: var(--spacing-lg);
}

.demo-subsection .d-flex {
  margin-bottom: var(--spacing-md);
}

/* Responsive adjustments for demo */
@media (max-width: 768px) {
  .card-layout-demo {
    padding: var(--spacing-md);
  }

  .demo-section {
    margin-bottom: var(--spacing-xl);
  }

  .demo-subsection {
    margin-bottom: var(--spacing-lg);
  }
}
</style>
