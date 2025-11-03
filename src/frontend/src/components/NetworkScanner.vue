<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon left color="primary">mdi-network-outline</v-icon>
      Network Scanner
      <v-spacer></v-spacer>
      <v-btn
        icon
        @click="$emit('close')"
        :disabled="isScanning"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-title>

    <v-divider></v-divider>

    <v-card-text class="pa-6">
      <!-- Network Configuration -->
      <v-form ref="scanForm" v-model="formValid" @submit.prevent="startScan">
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="networkRange"
              label="Network Range"
              placeholder="192.168.1.0/24"
              :rules="networkRules"
              outlined
              dense
              prepend-inner-icon="mdi-ip-network"
              hint="Enter network in CIDR notation (e.g., 192.168.1.0/24)"
              persistent-hint
              :disabled="isScanning"
            ></v-text-field>
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model="portsInput"
              label="Ports to Scan"
              :placeholder="formatPortList(DEFAULT_SCAN_PORTS)"
              :rules="portsRules"
              outlined
              dense
              prepend-inner-icon="mdi-ethernet"
              :hint="`Comma-separated list of ports (default: ${formatPortList(DEFAULT_SCAN_PORTS)})`"
              persistent-hint
              :disabled="isScanning"
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" md="6">
            <v-slider
              v-model="timeout"
              label="Connection Timeout"
              min="1"
              max="30"
              step="1"
              thumb-label
              :disabled="isScanning"
            >
              <template v-slot:append>
                <v-text-field
                  v-model="timeout"
                  type="number"
                  style="width: 80px"
                  dense
                  outlined
                  hide-details
                  suffix="s"
                  :disabled="isScanning"
                ></v-text-field>
              </template>
            </v-slider>
          </v-col>
        </v-row>
      </v-form>

      <!-- Scan Controls -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-btn
            v-if="!isScanning"
            color="primary"
            size="large"
            @click="startScan"
            :disabled="!formValid || isScanning"
            :loading="isStarting"
          >
            <v-icon left>mdi-magnify</v-icon>
            Start Network Scan
          </v-btn>

          <v-btn
            v-else
            color="error"
            size="large"
            @click="stopScan"
            :loading="isStopping"
          >
            <v-icon left>mdi-stop</v-icon>
            Stop Scan
          </v-btn>
        </v-col>
      </v-row>

      <!-- Scan Progress -->
      <div v-if="scanProgress.visible" class="mt-6">
        <v-card outlined>
          <v-card-text>
            <div class="d-flex align-center mb-3">
              <v-icon color="primary" class="mr-2">mdi-radar</v-icon>
              <div>
                <div class="font-weight-medium">Network Scan in Progress</div>
                <div class="text-caption">{{ scanProgress.statusText }}</div>
              </div>
            </div>
            
            <v-progress-linear
              :model-value="scanProgress.percentage"
              color="primary"
              bg-color="surface-variant"
              height="20"
              class="mb-2 scan-progress-bar"
            >
              <template v-slot:default="{ value }">
                <strong>{{ Math.ceil(value) }}%</strong>
              </template>
            </v-progress-linear>
            
            <div class="d-flex justify-space-between text-caption">
              <span>{{ scanProgress.scannedHosts }}/{{ scanProgress.totalHosts }} hosts scanned</span>
              <span>{{ scanProgress.foundCount }} miners found</span>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Scan Results -->
      <div v-if="scanResults.length > 0" class="mt-6">
        <v-card outlined>
          <v-card-title class="pb-2">
            <v-icon left color="success">mdi-check-circle</v-icon>
            Found {{ scanResults.length }} Miner{{ scanResults.length === 1 ? '' : 's' }}
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              variant="outlined"
              @click="handleAddAllMiners"
              :disabled="isAddingAll || scanResults.every(miner => miner.adding)"
              :loading="isAddingAll"
            >
              <v-icon left>mdi-plus-box-multiple</v-icon>
              Add All
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="resultHeaders"
              :items="scanResults"
              :items-per-page="10"
              class="elevation-0"
            >
              <template v-slot:item.type="{ item }">
                <v-chip size="small" :color="getMinerTypeColor(item.type)">
                  {{ item.type }}
                </v-chip>
              </template>
              
              <template v-slot:item.actions="{ item }">
                <v-btn
                  color="primary"
                  size="small"
                  @click="handleAddMiner(item)"
                  :disabled="item.adding"
                  :loading="item.adding"
                >
                  Add
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </div>

      <!-- No Results Message -->
      <div v-if="showNoResults" class="mt-6">
        <v-alert
          type="info"
          outlined
          class="mb-4"
        >
          <div class="d-flex align-center">
            <v-icon left>mdi-information</v-icon>
            <div>
              <div class="font-weight-medium">No miners found</div>
              <div class="text-caption mt-1">
                Try scanning a different network range or check that miners are powered on and connected to the network.
              </div>
            </div>
          </div>
        </v-alert>

        <v-card outlined>
          <v-card-text class="pa-4">
            <div class="text-subtitle-2 mb-3">Troubleshooting Tips:</div>
            <ul class="text-body-2">
              <li>Ensure miners are powered on and connected to the network</li>
              <li>Check that you're scanning the correct network range</li>
              <li>Verify that miners are accessible from this device</li>
              <li>Try adding miners manually if you know their IP addresses</li>
            </ul>
            
            <v-btn
              color="primary"
              variant="outlined"
              class="mt-3"
              @click="openAddMinerDialog"
            >
              <v-icon left>mdi-plus</v-icon>
              Add Miner Manually
            </v-btn>
          </v-card-text>
        </v-card>
      </div>

      <!-- Error Messages -->
      <div v-if="errorMessage" class="mt-6">
        <v-alert type="error" outlined>
          {{ errorMessage }}
        </v-alert>
      </div>
    </v-card-text>

    <!-- Add Miner Dialog -->
    <AddMinerDialog
      v-model="addMinerDialog"
      @miner-added="handleMinerAdded"
      @error="handleMinerError"
    />
  </v-card>
</template>

<script>
import { ref, computed } from 'vue'
import { useMinersStore } from '../stores/miners'
import { useGlobalSnackbar } from '../composables/useGlobalSnackbar'
import { useNetworkScan } from '../composables/useNetworkScan'
import AddMinerDialog from './AddMinerDialog.vue'
import { DEFAULT_SCAN_PORTS, formatPortList } from '../config/ports.config'

export default {
  name: 'NetworkScanner',

  components: {
    AddMinerDialog
  },

  emits: ['close'],

  setup() {
    const minersStore = useMinersStore()
    const { showSuccess, showError, showWarning } = useGlobalSnackbar()
    const { 
      isScanning, 
      scanProgress, 
      foundMiners, 
      scanError,
      startScan: startNetworkScan,
      stopScan: stopNetworkScan
    } = useNetworkScan()

    // Form state
    const scanForm = ref(null)
    const formValid = ref(false)
    const networkRange = ref('192.168.1.0/24')
    const portsInput = ref(formatPortList(DEFAULT_SCAN_PORTS))
    const timeout = ref(5)

    // UI state
    const isStarting = ref(false)
    const isStopping = ref(false)
    const addMinerDialog = ref(false)
    const isAddingAll = ref(false)

    // Use foundMiners from composable as scanResults
    const scanResults = foundMiners
    const errorMessage = scanError

    // Table headers for results
    const resultHeaders = [
      { title: 'Name', key: 'name' },
      { title: 'IP Address', key: 'ip_address' },
      { title: 'Port', key: 'port' },
      { title: 'Type', key: 'type' },
      { title: 'Actions', key: 'actions', sortable: false }
    ]

    // Validation rules
    const networkRules = [
      v => !!v || 'Network range is required',
      v => {
        const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
        if (!cidrPattern.test(v)) {
          return 'Invalid CIDR notation (e.g., 192.168.1.0/24)'
        }
        
        // Validate IP address parts
        const [ip, subnet] = v.split('/')
        const parts = ip.split('.')
        for (const part of parts) {
          const num = parseInt(part)
          if (num < 0 || num > 255) {
            return 'Invalid IP address range (0-255 for each octet)'
          }
        }
        
        // Validate subnet mask
        const subnetNum = parseInt(subnet)
        if (subnetNum < 8 || subnetNum > 30) {
          return 'Subnet mask must be between /8 and /30'
        }
        
        return true
      }
    ]

    const portsRules = [
      v => {
        if (!v) return true // Optional field
        
        const ports = v.split(',').map(p => p.trim()).filter(p => p)
        
        if (ports.length === 0) {
          return true // Allow empty
        }
        
        if (ports.length > 10) {
          return 'Maximum 10 ports allowed'
        }
        
        for (const port of ports) {
          const portNum = parseInt(port)
          if (isNaN(portNum)) {
            return `"${port}" is not a valid port number`
          }
          if (portNum < 1 || portNum > 65535) {
            return `Port ${portNum} must be between 1 and 65535`
          }
        }
        
        // Check for duplicates
        const uniquePorts = [...new Set(ports.map(p => parseInt(p)))]
        if (uniquePorts.length !== ports.length) {
          return 'Duplicate ports are not allowed'
        }
        
        return true
      }
    ]

    // Computed properties
    const parsedPorts = computed(() => {
      try {
        if (!portsInput.value || portsInput.value.trim() === '') {
          return DEFAULT_SCAN_PORTS
        }
        
        const ports = portsInput.value
          .split(',')
          .map(p => p.trim())
          .filter(p => p !== '')
          .map(p => parseInt(p))
          .filter(p => !isNaN(p) && p >= 1 && p <= 65535)
        
        return ports.length > 0 ? ports : DEFAULT_SCAN_PORTS
      } catch (error) {
        console.error('Error parsing ports:', error)
        return DEFAULT_SCAN_PORTS
      }
    })

    const showNoResults = computed(() => {
      return !isScanning.value && 
             !scanProgress.value.visible && 
             scanResults.value.length === 0 && 
             !errorMessage.value
    })

    // Scan methods using universal service via composable
    const startScan = async () => {
      if (!formValid.value) {
        showError('Please fix form validation errors before starting scan')
        return
      }

      isStarting.value = true
      
      try {
        const scanOptions = {
          network: networkRange.value,
          ports: parsedPorts.value,
          timeout: timeout.value
        }

        await startNetworkScan(scanOptions)

      } catch (error) {
        console.error('Error starting network scan:', error)
        showError(`Failed to start scan: ${error.message}`)
      } finally {
        isStarting.value = false
      }
    }

    const stopScan = async () => {
      isStopping.value = true
      
      try {
        await stopNetworkScan()
      } catch (error) {
        console.error('Error stopping network scan:', error)
        showError(`Failed to stop scan: ${error.message}`)
      } finally {
        isStopping.value = false
      }
    }

    // Miner management methods
    const handleAddMiner = async (minerInfo) => {
      try {
        // Validate miner info
        if (!minerInfo.type || !minerInfo.ip_address || !minerInfo.port) {
          throw new Error('Missing required miner information')
        }

        // Check if miner already exists
        const existingMiner = minersStore.miners.find(m => 
          m.ip_address === minerInfo.ip_address && m.port === minerInfo.port
        )

        if (existingMiner) {
          showWarning(`Miner at ${minerInfo.ip_address}:${minerInfo.port} already exists`)
          return
        }

        const minerData = {
          type: minerInfo.type,
          ip_address: minerInfo.ip_address,
          port: minerInfo.port,
          name: minerInfo.name || `${minerInfo.type} (${minerInfo.ip_address})`
        }

        console.log('Adding miner:', minerData)
        await minersStore.addMiner(minerData)
        showSuccess(`Miner "${minerData.name}" added successfully`)
        console.log('Miner added successfully:', minerData.name)

      } catch (error) {
        console.error('Error adding miner:', error)
        
        let errorMessage = 'Failed to add miner'
        if (error.message.includes('already exists')) {
          errorMessage = 'Miner already exists'
        } else if (error.message.includes('connection')) {
          errorMessage = 'Cannot connect to miner. Check IP address and port'
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Connection timeout. Check if miner is online'
        } else if (error.message.includes('validation')) {
          errorMessage = 'Invalid miner configuration'
        } else if (error.message) {
          errorMessage = error.message
        }

        showError(errorMessage)
      }
    }

    const handleAddAllMiners = async () => {
      if (scanResults.value.length === 0) {
        showWarning('No miners to add')
        return
      }

      isAddingAll.value = true
      let addedCount = 0
      let skippedCount = 0
      let errorCount = 0

      try {
        // Process miners sequentially to avoid overwhelming the system
        for (const minerInfo of scanResults.value) {
          try {
            // Check if miner already exists
            const existingMiner = minersStore.miners.find(m => 
              m.ip_address === minerInfo.ip_address && m.port === minerInfo.port
            )

            if (existingMiner) {
              console.log(`Skipping existing miner: ${minerInfo.ip_address}:${minerInfo.port}`)
              skippedCount++
              continue
            }

            // Validate miner info
            if (!minerInfo.type || !minerInfo.ip_address || !minerInfo.port) {
              console.error('Invalid miner info:', minerInfo)
              errorCount++
              continue
            }

            const minerData = {
              type: minerInfo.type,
              ip_address: minerInfo.ip_address,
              port: minerInfo.port,
              name: minerInfo.name || `${minerInfo.type} (${minerInfo.ip_address})`
            }

            console.log('Adding miner:', minerData)
            await minersStore.addMiner(minerData)
            addedCount++
            console.log('Miner added successfully:', minerData.name)

          } catch (error) {
            console.error('Error adding individual miner:', error)
            errorCount++
          }
        }

        // Show summary message
        let message = ''
        if (addedCount > 0) {
          message += `${addedCount} miner${addedCount === 1 ? '' : 's'} added successfully`
        }
        if (skippedCount > 0) {
          if (message) message += ', '
          message += `${skippedCount} already existed`
        }
        if (errorCount > 0) {
          if (message) message += ', '
          message += `${errorCount} failed to add`
        }

        if (addedCount > 0) {
          showSuccess(message)
        } else if (skippedCount > 0 && errorCount === 0) {
          showWarning(message)
        } else {
          showError(message || 'Failed to add miners')
        }

      } catch (error) {
        console.error('Error in handleAddAllMiners:', error)
        showError(`Failed to add miners: ${error.message}`)
      } finally {
        isAddingAll.value = false
      }
    }

    const openAddMinerDialog = () => {
      addMinerDialog.value = true
    }

    const handleMinerAdded = (miner) => {
      console.log('Miner added manually:', miner.name)
      showSuccess(`Miner "${miner.name}" added successfully`)
    }

    const handleMinerError = (error) => {
      console.error('Error adding miner manually:', error)
      showError(`Failed to add miner: ${error.message || 'Unknown error'}`)
    }

    // Utility methods
    const getMinerTypeColor = (type) => {
      const colorMap = {
        'Bitaxe': 'orange',
        'Magic Miner': 'purple',
        'Avalon Nano': 'green',
        'Bitcoin Node': 'blue'
      }
      return colorMap[type] || 'grey'
    }

    // Lifecycle is handled by the useNetworkScan composable

    return {
      // Form refs
      scanForm,
      formValid,
      networkRange,
      portsInput,
      timeout,

      // Scan state
      isScanning,
      isStarting,
      isStopping,
      scanProgress,
      scanResults,
      addMinerDialog,
      errorMessage,
      isAddingAll,

      // Table headers
      resultHeaders,

      // Validation rules
      networkRules,
      portsRules,

      // Computed
      parsedPorts,
      showNoResults,

      // Constants
      DEFAULT_SCAN_PORTS,
      formatPortList,

      // Methods
      startScan,
      stopScan,
      handleAddMiner,
      handleAddAllMiners,
      openAddMinerDialog,
      handleMinerAdded,
      handleMinerError,
      getMinerTypeColor
    }
  }
}
</script>

<style scoped>
/* Enhanced card styling */
:deep(.v-card) {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
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

/* Form field styling */
:deep(.v-text-field .v-field) {
  background-color: var(--color-surface-secondary) !important;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

:deep(.v-text-field .v-field:hover) {
  border-color: var(--color-primary);
}

:deep(.v-text-field .v-field--focused) {
  border-color: var(--color-primary) !important;
  box-shadow: var(--shadow-focus);
}

:deep(.v-text-field input) {
  color: var(--color-text-primary) !important;
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

/* Slider styling */
:deep(.v-slider) {
  color: var(--color-primary) !important;
}

:deep(.v-slider .v-slider-track__fill) {
  background-color: var(--color-primary) !important;
}

:deep(.v-slider .v-slider-thumb) {
  background-color: var(--color-primary) !important;
}

/* Alert styling */
:deep(.v-alert) {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

:deep(.v-alert.v-alert--type-info) {
  background-color: rgba(var(--color-info), 0.1) !important;
  border-color: var(--color-info);
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

/* Hint text styling */
:deep(.v-messages) {
  color: var(--color-text-secondary) !important;
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

  :deep(.v-btn) {
    width: 100%;
    margin-bottom: var(--spacing-sm);
  }
}

/* Progress bar styling - ensure color fill is visible */
.scan-progress-bar {
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.scan-progress-bar :deep(.v-progress-linear__background) {
  background-color: var(--color-surface-variant) !important;
  opacity: 1 !important;
}

.scan-progress-bar :deep(.v-progress-linear__determinate) {
  background-color: var(--color-primary) !important;
  transition: width 0.3s ease !important;
}

.scan-progress-bar :deep(.v-progress-linear__content) {
  color: var(--color-text-primary) !important;
  z-index: 2;
  position: relative;
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
  
  .scan-progress-bar :deep(.v-progress-linear__determinate) {
    transition: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-card),
  :deep(.v-text-field .v-field),
  :deep(.v-alert) {
    border-width: 2px;
  }

  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }
}

/* Focus management for keyboard navigation */
:deep(.v-text-field .v-field:focus-within) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

:deep(.v-btn:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>