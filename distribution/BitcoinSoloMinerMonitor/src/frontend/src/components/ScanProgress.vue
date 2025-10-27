<template>
  <v-card outlined>
    <v-card-title class="d-flex align-center">
      <v-icon left :color="statusColor">{{ statusIcon }}</v-icon>
      Scan Progress
      <v-spacer></v-spacer>
      <v-chip :color="statusColor" small dark>
        {{ statusText }}
      </v-chip>
    </v-card-title>

    <v-divider></v-divider>

    <v-card-text class="pa-4">
      <!-- Progress Bar -->
      <div v-if="scanStatus.status === 'scanning' || scanStatus.status === 'in_progress'">
        <div class="d-flex justify-space-between align-center mb-2">
          <span class="text-subtitle-2">Scanning Progress</span>
          <span class="text-caption">{{ progressText }}</span>
        </div>
        
        <v-progress-linear
          :model-value="progressPercentage"
          height="8"
          :color="statusColor"
          rounded
          striped
          :indeterminate="progressPercentage === 0"
        ></v-progress-linear>
      </div>

      <!-- Current IP Being Scanned -->
      <div v-if="scanStatus.current_ip" class="mt-4">
        <div class="d-flex align-center">
          <v-icon left color="primary" size="small">mdi-ip</v-icon>
          <span class="text-subtitle-2 mr-2">Currently scanning:</span>
          <v-chip size="small" color="primary" variant="outlined">
            {{ scanStatus.current_ip }}
          </v-chip>
        </div>
      </div>

      <!-- Scan Statistics -->
      <v-row class="mt-4">
        <v-col cols="6" sm="3">
          <div class="text-center">
            <div class="text-h6 font-weight-bold">{{ scanStatus.total_hosts || 0 }}</div>
            <div class="text-caption text-secondary">Total Hosts</div>
          </div>
        </v-col>
        
        <v-col cols="6" sm="3">
          <div class="text-center">
            <div class="text-h6 font-weight-bold">{{ scanStatus.scanned_hosts || 0 }}</div>
            <div class="text-caption text-secondary">Scanned</div>
          </div>
        </v-col>
        
        <v-col cols="6" sm="3">
          <div class="text-center">
            <div class="text-h6 font-weight-bold text-success">{{ foundMinersCount }}</div>
            <div class="text-caption text-secondary">Found</div>
          </div>
        </v-col>
        
        <v-col cols="6" sm="3">
          <div class="text-center">
            <div class="text-h6 font-weight-bold">{{ elapsedTime }}</div>
            <div class="text-caption text-secondary">Elapsed</div>
          </div>
        </v-col>
      </v-row>

      <!-- Scan Details -->
      <div v-if="scanStatus.network" class="mt-4">
        <v-expansion-panels variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon left>mdi-information-outline</v-icon>
              Scan Details
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-simple-table dense>
                <template v-slot:default>
                  <tbody>
                    <tr>
                      <td><strong>Network Range:</strong></td>
                      <td>{{ scanStatus.network }}</td>
                    </tr>
                    <tr>
                      <td><strong>Ports:</strong></td>
                      <td>{{ (scanStatus.ports || []).join(', ') }}</td>
                    </tr>
                    <tr>
                      <td><strong>Timeout:</strong></td>
                      <td>{{ scanStatus.timeout || 5 }}s</td>
                    </tr>
                    <tr v-if="scanStatus.start_time">
                      <td><strong>Started:</strong></td>
                      <td>{{ formatTime(scanStatus.start_time) }}</td>
                    </tr>
                    <tr v-if="scanStatus.end_time">
                      <td><strong>Completed:</strong></td>
                      <td>{{ formatTime(scanStatus.end_time) }}</td>
                    </tr>
                  </tbody>
                </template>
              </v-simple-table>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>

      <!-- Error Message -->
      <div v-if="scanStatus.status === 'error' && scanStatus.error" class="mt-4">
        <v-alert
          type="error"
          outlined
          class="mb-0"
        >
          <div class="d-flex align-center">
            <v-icon left>mdi-alert-circle</v-icon>
            <div>
              <div class="font-weight-medium">Scan Error</div>
              <div class="text-caption mt-1">{{ scanStatus.error }}</div>
            </div>
          </div>
        </v-alert>
      </div>

      <!-- Completion Message -->
      <div v-if="scanStatus.status === 'completed'" class="mt-4">
        <v-alert
          :type="foundMinersCount > 0 ? 'success' : 'info'"
          outlined
          class="mb-0"
        >
          <div class="d-flex align-center">
            <v-icon left>{{ foundMinersCount > 0 ? 'mdi-check-circle' : 'mdi-information' }}</v-icon>
            <div>
              <div class="font-weight-medium">
                Scan Completed
              </div>
              <div class="text-caption mt-1">
                {{ foundMinersCount > 0 
                  ? `Found ${foundMinersCount} miner${foundMinersCount === 1 ? '' : 's'} on the network` 
                  : 'No miners were found on the specified network range' }}
              </div>
            </div>
          </div>
        </v-alert>
      </div>

      <!-- Cancelled Message -->
      <div v-if="scanStatus.status === 'cancelled'" class="mt-4">
        <v-alert
          type="warning"
          outlined
          class="mb-0"
        >
          <div class="d-flex align-center">
            <v-icon left>mdi-cancel</v-icon>
            <div>
              <div class="font-weight-medium">Scan Cancelled</div>
              <div class="text-caption mt-1">
                The network scan was stopped before completion
              </div>
            </div>
          </div>
        </v-alert>
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
import { computed, ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'ScanProgress',

  props: {
    scanStatus: {
      type: Object,
      required: true
    },
    isScanning: {
      type: Boolean,
      default: false
    }
  },

  setup(props) {
    const currentTime = ref(new Date())
    let timeInterval = null

    // Computed properties
    const statusColor = computed(() => {
      switch (props.scanStatus.status) {
        case 'scanning':
        case 'in_progress':
          return 'primary'
        case 'completed':
          return 'success'
        case 'error':
          return 'error'
        case 'cancelled':
          return 'warning'
        default:
          return 'grey'
      }
    })

    const statusIcon = computed(() => {
      switch (props.scanStatus.status) {
        case 'scanning':
        case 'in_progress':
          return 'mdi-magnify'
        case 'completed':
          return 'mdi-check-circle'
        case 'error':
          return 'mdi-alert-circle'
        case 'cancelled':
          return 'mdi-cancel'
        default:
          return 'mdi-help-circle'
      }
    })

    const statusText = computed(() => {
      switch (props.scanStatus.status) {
        case 'scanning':
        case 'in_progress':
          return 'Scanning'
        case 'completed':
          return 'Completed'
        case 'error':
          return 'Error'
        case 'cancelled':
          return 'Cancelled'
        case 'starting':
          return 'Starting'
        default:
          return 'Unknown'
      }
    })

    const progressPercentage = computed(() => {
      if (!props.scanStatus.total_hosts || props.scanStatus.total_hosts === 0) {
        return 0
      }
      return Math.round((props.scanStatus.scanned_hosts / props.scanStatus.total_hosts) * 100)
    })

    const progressText = computed(() => {
      const scanned = props.scanStatus.scanned_hosts || 0
      const total = props.scanStatus.total_hosts || 0
      return `${scanned} / ${total} hosts (${progressPercentage.value}%)`
    })

    const foundMinersCount = computed(() => {
      return props.scanStatus.found_miners ? props.scanStatus.found_miners.length : 0
    })

    const elapsedTime = computed(() => {
      if (!props.scanStatus.start_time) {
        return '0s'
      }

      const startTime = new Date(props.scanStatus.start_time)
      const endTime = props.scanStatus.end_time ? new Date(props.scanStatus.end_time) : currentTime.value
      const elapsed = Math.floor((endTime - startTime) / 1000)

      if (elapsed < 60) {
        return `${elapsed}s`
      } else if (elapsed < 3600) {
        const minutes = Math.floor(elapsed / 60)
        const seconds = elapsed % 60
        return `${minutes}m ${seconds}s`
      } else {
        const hours = Math.floor(elapsed / 3600)
        const minutes = Math.floor((elapsed % 3600) / 60)
        return `${hours}h ${minutes}m`
      }
    })

    // Methods
    const formatTime = (timeString) => {
      if (!timeString) return 'N/A'
      
      try {
        const date = new Date(timeString)
        return date.toLocaleString()
      } catch (error) {
        return 'Invalid time'
      }
    }

    // Lifecycle hooks
    onMounted(() => {
      // Update current time every second for elapsed time calculation
      timeInterval = setInterval(() => {
        currentTime.value = new Date()
      }, 1000)
    })

    onUnmounted(() => {
      if (timeInterval) {
        clearInterval(timeInterval)
      }
    })

    return {
      // Computed
      statusColor,
      statusIcon,
      statusText,
      progressPercentage,
      progressText,
      foundMinersCount,
      elapsedTime,

      // Methods
      formatTime
    }
  }
}
</script>

<style scoped>
/* Enhanced card styling */
:deep(.v-card) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
}

:deep(.v-card-title) {
  background-color: var(--color-surface-secondary);
  border-bottom: 1px solid var(--color-border-subtle);
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-card-text) {
  color: var(--color-text-primary) !important;
}

/* Progress bar styling */
:deep(.v-progress-linear) {
  border-radius: var(--radius-sm);
  background-color: var(--color-surface-variant) !important;
}

:deep(.v-progress-linear .v-progress-linear__determinate) {
  background-color: var(--color-primary) !important;
}

/* Chip styling */
:deep(.v-chip) {
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
}

/* Statistics styling */
.text-h6 {
  color: var(--color-text-primary) !important;
}

.text-caption {
  color: var(--color-text-secondary) !important;
}

.text-secondary {
  color: var(--color-text-secondary) !important;
}

/* Table styling */
:deep(.v-table) {
  background-color: var(--color-surface) !important;
}

:deep(.v-table tbody tr td) {
  color: var(--color-text-primary) !important;
  border-bottom: 1px solid var(--color-border-subtle) !important;
}

/* Expansion panel styling */
:deep(.v-expansion-panels) {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

:deep(.v-expansion-panel) {
  background-color: var(--color-surface) !important;
}

:deep(.v-expansion-panel-title) {
  background-color: var(--color-surface-secondary) !important;
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.v-expansion-panel-text) {
  background-color: var(--color-surface) !important;
  color: var(--color-text-primary) !important;
}

/* Alert styling */
:deep(.v-alert) {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

:deep(.v-alert.v-alert--type-success) {
  background-color: rgba(var(--color-success), 0.1) !important;
  border-color: var(--color-success);
  color: var(--color-text-primary) !important;
}

:deep(.v-alert.v-alert--type-error) {
  background-color: rgba(var(--color-error), 0.1) !important;
  border-color: var(--color-error);
  color: var(--color-text-primary) !important;
}

:deep(.v-alert.v-alert--type-info) {
  background-color: rgba(var(--color-info), 0.1) !important;
  border-color: var(--color-info);
  color: var(--color-text-primary) !important;
}

:deep(.v-alert.v-alert--type-warning) {
  background-color: rgba(var(--color-warning), 0.1) !important;
  border-color: var(--color-warning);
  color: var(--color-text-primary) !important;
}

/* Divider styling */
:deep(.v-divider) {
  border-color: var(--color-border-subtle) !important;
}

/* Icon styling */
:deep(.v-icon) {
  color: inherit;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  :deep(.v-card-title) {
    font-size: var(--font-size-body);
    padding: var(--spacing-md);
  }

  :deep(.v-card-text) {
    padding: var(--spacing-md);
  }

  .text-h6 {
    font-size: var(--font-size-body) !important;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-progress-linear) {
    animation: none;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-card),
  :deep(.v-expansion-panels),
  :deep(.v-alert) {
    border-width: 2px;
  }

  :deep(.v-progress-linear) {
    border: 1px solid var(--color-text-primary);
  }
}

/* Focus management for keyboard navigation */
:deep(.v-expansion-panel-title:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>