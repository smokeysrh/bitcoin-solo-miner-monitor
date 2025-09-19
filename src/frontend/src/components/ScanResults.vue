<template>
  <v-card outlined>
    <v-card-title class="d-flex align-center">
      <v-icon left color="success">mdi-server-network</v-icon>
      Discovered Miners
      <v-spacer></v-spacer>
      <v-chip color="success" small dark>
        {{ results.length }} found
      </v-chip>
    </v-card-title>

    <v-divider></v-divider>

    <v-card-text class="pa-0">
      <div v-if="results.length === 0" class="pa-4 text-center">
        <v-icon size="64" color="grey lighten-1">mdi-server-off</v-icon>
        <h3 class="mt-3">No Miners Found</h3>
        <p class="grey--text">
          No miners were discovered on the scanned network range.
        </p>
      </div>

      <div v-else>
        <!-- Results List -->
        <v-list lines="three">
          <template v-for="(miner, index) in results" :key="index">
            <v-list-item class="pa-4">
              <template v-slot:prepend>
                <v-avatar :color="getMinerTypeColor(miner.type)" size="48">
                  <v-icon color="white" size="24">{{ getMinerTypeIcon(miner.type) }}</v-icon>
                </v-avatar>
              </template>

              <v-list-item-title class="font-weight-medium">
                {{ miner.name || `${miner.type} Miner` }}
              </v-list-item-title>

              <v-list-item-subtitle>
                <div class="d-flex flex-column">
                  <div class="d-flex align-center mb-1">
                    <v-icon size="small" class="mr-1">mdi-ip</v-icon>
                    <span>{{ miner.ip_address }}:{{ miner.port }}</span>
                  </div>
                  <div class="d-flex align-center mb-1">
                    <v-icon size="small" class="mr-1">mdi-chip</v-icon>
                    <span>{{ formatMinerType(miner.type) }}</span>
                  </div>
                  <div v-if="miner.model" class="d-flex align-center">
                    <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
                    <span>{{ miner.model }}</span>
                  </div>
                </div>
              </v-list-item-subtitle>

              <template v-slot:append>
                <div class="d-flex flex-column align-end">
                  <v-btn
                    color="primary"
                    variant="elevated"
                    size="small"
                    @click="addMiner(miner)"
                    :loading="addingMiners[index]"
                    :disabled="isAlreadyAdded(miner)"
                    class="mb-2"
                  >
                    <v-icon left size="small">
                      {{ isAlreadyAdded(miner) ? 'mdi-check' : 'mdi-plus' }}
                    </v-icon>
                    {{ isAlreadyAdded(miner) ? 'Added' : 'Add' }}
                  </v-btn>

                  <v-btn
                    color="secondary"
                    variant="outlined"
                    size="small"
                    @click="showMinerDetails(miner)"
                  >
                    <v-icon left size="small">mdi-information</v-icon>
                    Details
                  </v-btn>
                </div>
              </template>
            </v-list-item>

            <v-divider v-if="index < results.length - 1"></v-divider>
          </template>
        </v-list>

        <!-- Bulk Actions -->
        <v-card-actions class="pa-4 bg-surface-variant">
          <v-btn
            color="primary"
            variant="elevated"
            @click="addAllMiners"
            :loading="addingAll"
            :disabled="allMinersAdded"
          >
            <v-icon left>mdi-plus-box-multiple</v-icon>
            Add All Miners
          </v-btn>

          <v-spacer></v-spacer>

          <v-btn
            color="secondary"
            variant="outlined"
            @click="exportResults"
          >
            <v-icon left>mdi-download</v-icon>
            Export Results
          </v-btn>
        </v-card-actions>
      </div>
    </v-card-text>

    <!-- Miner Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="600px">
      <v-card v-if="selectedMiner">
        <v-card-title class="d-flex align-center">
          <v-avatar :color="getMinerTypeColor(selectedMiner.type)" size="32" class="mr-3">
            <v-icon color="white" size="16">{{ getMinerTypeIcon(selectedMiner.type) }}</v-icon>
          </v-avatar>
          {{ selectedMiner.name || `${selectedMiner.type} Miner` }}
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text class="pa-4">
          <v-simple-table dense>
            <template v-slot:default>
              <tbody>
                <tr>
                  <td><strong>Type:</strong></td>
                  <td>{{ formatMinerType(selectedMiner.type) }}</td>
                </tr>
                <tr>
                  <td><strong>IP Address:</strong></td>
                  <td>{{ selectedMiner.ip_address }}</td>
                </tr>
                <tr>
                  <td><strong>Port:</strong></td>
                  <td>{{ selectedMiner.port }}</td>
                </tr>
                <tr v-if="selectedMiner.model">
                  <td><strong>Model:</strong></td>
                  <td>{{ selectedMiner.model }}</td>
                </tr>
                <tr v-if="selectedMiner.version">
                  <td><strong>Version:</strong></td>
                  <td>{{ selectedMiner.version }}</td>
                </tr>
                <tr v-if="selectedMiner.mac_address">
                  <td><strong>MAC Address:</strong></td>
                  <td>{{ selectedMiner.mac_address }}</td>
                </tr>
                <tr v-if="selectedMiner.response_time">
                  <td><strong>Response Time:</strong></td>
                  <td>{{ selectedMiner.response_time }}ms</td>
                </tr>
              </tbody>
            </template>
          </v-simple-table>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            @click="addMiner(selectedMiner)"
            :loading="addingMiners[results.indexOf(selectedMiner)]"
            :disabled="isAlreadyAdded(selectedMiner)"
          >
            <v-icon left>
              {{ isAlreadyAdded(selectedMiner) ? 'mdi-check' : 'mdi-plus' }}
            </v-icon>
            {{ isAlreadyAdded(selectedMiner) ? 'Added' : 'Add Miner' }}
          </v-btn>
          <v-btn color="grey" @click="detailsDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
import { ref, computed } from 'vue'
import { useMinersStore } from '../stores/miners'
import { useGlobalSnackbar } from '../composables/useGlobalSnackbar'

export default {
  name: 'ScanResults',

  props: {
    results: {
      type: Array,
      required: true
    }
  },

  emits: ['add-miner'],

  setup(props, { emit }) {
    const minersStore = useMinersStore()
    const { showSuccess, showError, showWarning, showInfo } = useGlobalSnackbar()

    // State
    const addingMiners = ref({})
    const addingAll = ref(false)
    const detailsDialog = ref(false)
    const selectedMiner = ref(null)

    // Computed properties
    const existingMiners = computed(() => minersStore.miners)

    const allMinersAdded = computed(() => {
      return props.results.every(miner => isAlreadyAdded(miner))
    })

    // Methods
    const getMinerTypeColor = (type) => {
      switch (type.toLowerCase()) {
        case 'bitaxe':
          return '#1976D2' // Blue
        case 'avalon_nano':
          return '#43A047' // Green
        case 'magic_miner':
          return '#E53935' // Red
        default:
          return '#9C27B0' // Purple
      }
    }

    const getMinerTypeIcon = (type) => {
      switch (type.toLowerCase()) {
        case 'bitaxe':
          return 'mdi-pickaxe'
        case 'avalon_nano':
          return 'mdi-chip'
        case 'magic_miner':
          return 'mdi-lightning-bolt'
        default:
          return 'mdi-server'
      }
    }

    const formatMinerType = (type) => {
      switch (type.toLowerCase()) {
        case 'bitaxe':
          return 'Bitaxe'
        case 'avalon_nano':
          return 'Avalon Nano'
        case 'magic_miner':
          return 'Magic Miner'
        default:
          return type.charAt(0).toUpperCase() + type.slice(1)
      }
    }

    const isAlreadyAdded = (miner) => {
      return existingMiners.value.some(existing => 
        existing.ip_address === miner.ip_address && existing.port === miner.port
      )
    }

    const addMiner = async (miner) => {
      const index = props.results.indexOf(miner)
      
      if (isAlreadyAdded(miner)) {
        return
      }

      addingMiners.value[index] = true

      try {
        const minerData = {
          type: miner.type,
          ip_address: miner.ip_address,
          port: miner.port,
          name: miner.name || `${formatMinerType(miner.type)} (${miner.ip_address})`
        }

        emit('add-miner', minerData)
        
        // Simulate a delay to show loading state
        await new Promise(resolve => setTimeout(resolve, 1000))
        
      } catch (error) {
        console.error('Error adding miner:', error)
      } finally {
        addingMiners.value[index] = false
      }
    }

    const addAllMiners = async () => {
      if (allMinersAdded.value) {
        return
      }

      addingAll.value = true

      try {
        const minersToAdd = props.results.filter(miner => !isAlreadyAdded(miner))
        
        for (const miner of minersToAdd) {
          const minerData = {
            type: miner.type,
            ip_address: miner.ip_address,
            port: miner.port,
            name: miner.name || `${formatMinerType(miner.type)} (${miner.ip_address})`
          }

          emit('add-miner', minerData)
          
          // Small delay between additions
          await new Promise(resolve => setTimeout(resolve, 500))
        }
        
      } catch (error) {
        console.error('Error adding all miners:', error)
      } finally {
        addingAll.value = false
      }
    }

    const showMinerDetails = (miner) => {
      selectedMiner.value = miner
      detailsDialog.value = true
    }

    const exportResults = () => {
      try {
        if (!props.results || props.results.length === 0) {
          showWarning('No scan results to export')
          return
        }

        const exportData = props.results.map(miner => ({
          type: miner.type,
          ip_address: miner.ip_address,
          port: miner.port,
          name: miner.name,
          model: miner.model,
          version: miner.version,
          mac_address: miner.mac_address,
          response_time: miner.response_time
        }))

        const dataStr = JSON.stringify(exportData, null, 2)
        const dataBlob = new Blob([dataStr], { type: 'application/json' })
        
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `network_scan_results_${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        
        showSuccess(`Exported ${props.results.length} scan results`)
        console.log('Scan results exported successfully')
      } catch (error) {
        console.error('Error exporting scan results:', error)
        showError('Failed to export scan results')
      }
    }

    return {
      // State
      addingMiners,
      addingAll,
      detailsDialog,
      selectedMiner,

      // Computed
      allMinersAdded,

      // Methods
      getMinerTypeColor,
      getMinerTypeIcon,
      formatMinerType,
      isAlreadyAdded,
      addMiner,
      addAllMiners,
      showMinerDetails,
      exportResults
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

/* List styling */
:deep(.v-list) {
  background-color: var(--color-surface) !important;
}

:deep(.v-list-item) {
  color: var(--color-text-primary) !important;
  border-bottom: 1px solid var(--color-border-subtle);
}

:deep(.v-list-item:hover) {
  background-color: var(--color-surface-hover) !important;
}

:deep(.v-list-item-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.v-list-item-subtitle) {
  color: var(--color-text-secondary) !important;
}

/* Avatar styling */
:deep(.v-avatar) {
  border: 2px solid var(--color-surface);
  box-shadow: var(--shadow-1);
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

/* Chip styling */
:deep(.v-chip) {
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
}

/* Table styling */
:deep(.v-table) {
  background-color: var(--color-surface) !important;
}

:deep(.v-table tbody tr td) {
  color: var(--color-text-primary) !important;
  border-bottom: 1px solid var(--color-border-subtle) !important;
}

/* Card actions styling */
:deep(.v-card-actions) {
  background-color: var(--color-surface-variant);
  border-top: 1px solid var(--color-border-subtle);
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
}

/* Divider styling */
:deep(.v-divider) {
  border-color: var(--color-border-subtle) !important;
}

/* Icon styling */
:deep(.v-icon) {
  color: inherit;
}

/* Empty state styling */
.text-center h3 {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

.text-center p {
  color: var(--color-text-secondary) !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  :deep(.v-card-title) {
    font-size: var(--font-size-body);
    padding: var(--spacing-md);
  }

  :deep(.v-list-item) {
    padding: var(--spacing-md);
  }

  :deep(.v-card-actions) {
    padding: var(--spacing-md);
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  :deep(.v-card-actions .v-btn) {
    width: 100%;
  }

  :deep(.v-card-actions .v-spacer) {
    display: none;
  }

  /* Stack buttons vertically on mobile */
  .d-flex.flex-column.align-end {
    width: 100%;
  }

  .d-flex.flex-column.align-end .v-btn {
    width: 100%;
    margin-bottom: var(--spacing-xs);
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-btn) {
    transition: none;
    transform: none !important;
  }

  :deep(.v-btn:hover) {
    transform: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-card),
  :deep(.v-dialog .v-card) {
    border-width: 2px;
  }

  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }

  :deep(.v-avatar) {
    border-width: 3px;
  }
}

/* Focus management for keyboard navigation */
:deep(.v-list-item:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

:deep(.v-btn:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>