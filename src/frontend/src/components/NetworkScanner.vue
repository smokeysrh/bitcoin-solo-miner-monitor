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
              placeholder="80, 4028"
              :rules="portsRules"
              outlined
              dense
              prepend-inner-icon="mdi-ethernet"
              hint="Comma-separated list of ports (default: 80, 4028)"
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
      <div v-if="scanStatus && scanStatus.status !== 'not_started'" class="mt-6">
        <ScanProgress 
          :scan-status="scanStatus"
          :is-scanning="isScanning"
        />
      </div>

      <!-- Scan Results -->
      <div v-if="scanResults.length > 0" class="mt-6">
        <ScanResults 
          :results="scanResults"
          @add-miner="handleAddMiner"
        />
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useMinersStore } from '../stores/miners'
import { useGlobalSnackbar } from '../composables/useGlobalSnackbar'
import ScanProgress from './ScanProgress.vue'
import ScanResults from './ScanResults.vue'
import AddMinerDialog from './AddMinerDialog.vue'

export default {
  name: 'NetworkScanner',

  components: {
    ScanProgress,
    ScanResults,
    AddMinerDialog
  },

  emits: ['close'],

  setup() {
    const minersStore = useMinersStore()
    const { showSuccess, showError, showWarning, showInfo } = useGlobalSnackbar()

    // Form state
    const scanForm = ref(null)
    const formValid = ref(false)
    const networkRange = ref('192.168.1.0/24')
    const portsInput = ref('80, 4028')
    const timeout = ref(5)

    // Scan state
    const isScanning = ref(false)
    const isStarting = ref(false)
    const isStopping = ref(false)
    const scanStatus = ref(null)
    const scanResults = ref([])
    const addMinerDialog = ref(false)

    // WebSocket connection for real-time updates
    let websocket = null
    let reconnectTimer = null
    let connectionAttempts = 0
    const maxConnectionAttempts = 5

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
          return [80, 4028] // Default ports
        }
        
        const ports = portsInput.value
          .split(',')
          .map(p => p.trim())
          .filter(p => p !== '')
          .map(p => parseInt(p))
          .filter(p => !isNaN(p) && p >= 1 && p <= 65535)
        
        return ports.length > 0 ? ports : [80, 4028]
      } catch (error) {
        console.error('Error parsing ports:', error)
        return [80, 4028]
      }
    })

    const showNoResults = computed(() => {
      try {
        return scanStatus.value && 
               scanStatus.value.status === 'completed' && 
               (!scanResults.value || scanResults.value.length === 0)
      } catch (error) {
        console.error('Error computing showNoResults:', error)
        return false
      }
    })

    // WebSocket methods
    const connectWebSocket = () => {
      try {
        // Don't attempt to connect if we've exceeded max attempts
        if (connectionAttempts >= maxConnectionAttempts) {
          console.warn('Max WebSocket connection attempts reached, giving up')
          showWarning('Real-time updates unavailable. Scan will still work but progress updates may be delayed.')
          return
        }

        connectionAttempts++
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws`
        
        console.log(`Attempting WebSocket connection (${connectionAttempts}/${maxConnectionAttempts})`)
        websocket = new WebSocket(wsUrl)

        websocket.onopen = () => {
          console.log('WebSocket connected for network scanner')
          connectionAttempts = 0 // Reset on successful connection
          
          try {
            // Subscribe to discovery updates
            websocket.send(JSON.stringify({
              type: 'subscribe',
              topic: 'discovery'
            }))
            
            if (connectionAttempts > 1) {
              showSuccess('Real-time updates reconnected')
            }
          } catch (error) {
            console.error('Error subscribing to discovery updates:', error)
            showWarning('Connected but failed to subscribe to updates')
          }
        }

        websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            
            if (message.type === 'discovery_update' && message.data) {
              scanStatus.value = message.data
              
              // Update results if scan completed
              if (message.data.status === 'completed') {
                if (message.data.found_miners && message.data.found_miners.length > 0) {
                  scanResults.value = message.data.found_miners
                  showSuccess(`Scan completed! Found ${message.data.found_miners.length} miner${message.data.found_miners.length === 1 ? '' : 's'}`)
                } else {
                  showInfo('Scan completed. No miners found on the network.')
                }
                isScanning.value = false
              } else if (message.data.status === 'cancelled') {
                showWarning('Network scan was stopped')
                isScanning.value = false
              } else if (message.data.status === 'error') {
                const errorMsg = message.data.error || 'Unknown scan error occurred'
                showError(`Scan failed: ${errorMsg}`)
                isScanning.value = false
              }
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
            showWarning('Received invalid update message')
          }
        }

        websocket.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          websocket = null
          
          // Only attempt to reconnect if it wasn't a clean close and we haven't exceeded attempts
          if (event.code !== 1000 && connectionAttempts < maxConnectionAttempts) {
            if (!reconnectTimer) {
              const delay = Math.min(3000 * connectionAttempts, 15000) // Exponential backoff, max 15s
              console.log(`Attempting to reconnect in ${delay}ms`)
              
              reconnectTimer = setTimeout(() => {
                reconnectTimer = null
                connectWebSocket()
              }, delay)
            }
          } else if (connectionAttempts >= maxConnectionAttempts) {
            showError('Real-time updates unavailable. Please refresh the page to retry.')
          }
        }

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error)
          if (connectionAttempts === 1) {
            showWarning('Connection issue detected. Retrying...')
          }
        }
      } catch (error) {
        console.error('Error connecting WebSocket:', error)
        showError('Failed to establish real-time connection')
      }
    }

    const disconnectWebSocket = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      
      if (websocket) {
        websocket.close()
        websocket = null
      }
    }

    // Scan methods
    const startScan = async () => {
      if (!formValid.value) {
        showError('Please fix form validation errors before starting scan')
        return
      }

      isStarting.value = true
      
      try {
        // Validate network range more thoroughly
        const networkPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
        if (!networkPattern.test(networkRange.value)) {
          throw new Error('Invalid network range format. Use CIDR notation (e.g., 192.168.1.0/24)')
        }

        // Validate ports
        if (parsedPorts.value.length === 0) {
          throw new Error('At least one port must be specified')
        }

        const invalidPorts = parsedPorts.value.filter(port => port < 1 || port > 65535)
        if (invalidPorts.length > 0) {
          throw new Error(`Invalid port numbers: ${invalidPorts.join(', ')}`)
        }

        console.log(`Starting network scan: ${networkRange.value}, ports: ${parsedPorts.value.join(', ')}, timeout: ${timeout.value}s`)

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout

        const response = await fetch('/api/discovery', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            network: networkRange.value,
            ports: parsedPorts.value,
            timeout: timeout.value
          }),
          signal: controller.signal
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          const errorMessage = errorData.detail || errorData.message || `Server error: ${response.status}`
          
          if (response.status === 400) {
            throw new Error(`Invalid request: ${errorMessage}`)
          } else if (response.status === 422) {
            throw new Error(`Validation error: ${errorMessage}`)
          } else if (response.status >= 500) {
            throw new Error(`Server error: ${errorMessage}`)
          } else {
            throw new Error(errorMessage)
          }
        }

        const result = await response.json()

        isScanning.value = true
        scanResults.value = []
        showSuccess(`Network scan started for ${networkRange.value}`)
        console.log('Network scan started successfully:', result)

      } catch (error) {
        console.error('Error starting network scan:', error)
        
        if (error.name === 'AbortError') {
          showError('Scan request timed out. Please try again.')
        } else if (error.message.includes('fetch')) {
          showError('Network error: Unable to connect to server. Please check your connection.')
        } else {
          showError(`Failed to start scan: ${error.message}`)
        }
      } finally {
        isStarting.value = false
      }
    }

    const stopScan = async () => {
      isStopping.value = true
      
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout

        const response = await fetch('/api/discovery/stop', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          signal: controller.signal
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          const errorMessage = errorData.detail || errorData.message || `Server error: ${response.status}`
          throw new Error(errorMessage)
        }

        const result = await response.json()
        isScanning.value = false
        showWarning('Network scan stopped')
        console.log('Network scan stopped successfully:', result)

      } catch (error) {
        console.error('Error stopping network scan:', error)
        
        if (error.name === 'AbortError') {
          showError('Stop request timed out. Scan may still be running.')
        } else if (error.message.includes('fetch')) {
          showError('Network error: Unable to connect to server.')
        } else {
          showError(`Failed to stop scan: ${error.message}`)
        }
        
        // Force stop the UI state even if server request failed
        isScanning.value = false
      } finally {
        isStopping.value = false
      }
    }

    const getScanStatus = async () => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout

        const response = await fetch('/api/discovery/status', {
          signal: controller.signal
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          throw new Error(`Status check failed: ${response.status}`)
        }

        const result = await response.json()
        scanStatus.value = result
        
        // Update scanning state based on status
        if (result.status === 'in_progress' || result.status === 'scanning') {
          isScanning.value = true
        } else {
          isScanning.value = false
        }
        
        // Update results if available
        if (result.found_miners) {
          scanResults.value = result.found_miners
        }

        console.log('Scan status updated:', result.status)

      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Error getting scan status:', error)
          // Don't show error notification for status checks as they happen in background
        }
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

    // Lifecycle hooks
    onMounted(async () => {
      try {
        // Get initial scan status
        await getScanStatus()
        
        // Connect WebSocket for real-time updates
        connectWebSocket()
        
        console.log('Network scanner initialized successfully')
      } catch (error) {
        console.error('Error initializing network scanner:', error)
        showWarning('Scanner initialized with limited functionality')
      }
    })

    onUnmounted(() => {
      try {
        // Disconnect WebSocket
        disconnectWebSocket()
        
        // Clear any pending timers
        if (reconnectTimer) {
          clearTimeout(reconnectTimer)
          reconnectTimer = null
        }
        
        console.log('Network scanner cleanup completed')
      } catch (error) {
        console.error('Error during network scanner cleanup:', error)
      }
    })

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
      scanStatus,
      scanResults,
      addMinerDialog,

      // Validation rules
      networkRules,
      portsRules,

      // Computed
      parsedPorts,
      showNoResults,

      // Methods
      startScan,
      stopScan,
      handleAddMiner,
      openAddMinerDialog,
      handleMinerAdded,
      handleMinerError
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