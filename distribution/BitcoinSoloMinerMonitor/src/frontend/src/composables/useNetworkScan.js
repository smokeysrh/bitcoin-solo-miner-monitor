/**
 * Network Scan Composable
 * 
 * Provides a Vue composable interface for the universal network scan service,
 * making it easy to integrate network scanning into any component.
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { networkScanService } from '../services/networkScanService'
import { useGlobalSnackbar } from './useGlobalSnackbar'

export function useNetworkScan() {
  const { showSuccess, showError, showWarning, showInfo } = useGlobalSnackbar()

  // Reactive state
  const isScanning = ref(false)
  const scanProgress = ref({
    visible: false,
    percentage: 0,
    statusText: '',
    scannedHosts: 0,
    totalHosts: 0,
    foundCount: 0
  })
  const foundMiners = ref([])
  const scanError = ref('')

  // Handle scan updates from the service
  const handleScanUpdate = (update) => {
    console.log('useNetworkScan received update:', update)
    
    switch (update.type) {
      case 'scan_started':
        isScanning.value = true
        scanProgress.value = {
          visible: true,
          percentage: Math.min(100, Math.max(0, update.data.progress || 0)),
          scannedHosts: update.data.scanned_hosts || 0,
          totalHosts: update.data.total_hosts || 0,
          foundCount: update.data.found_miners?.length || 0,
          statusText: update.data.current_ip 
            ? `Scanning ${update.data.current_ip}...`
            : 'Starting network scan...'
        }
        foundMiners.value = []
        scanError.value = ''
        break
        
      case 'scan_update':
        if (update.data.status === 'scanning' || update.data.status === 'in_progress') {
          // Update progress with proper reactivity by replacing the entire object
          scanProgress.value = {
            visible: true,
            percentage: Math.min(100, Math.max(0, update.data.progress || 0)),
            scannedHosts: update.data.scannedHosts || 0,
            totalHosts: update.data.totalHosts || 0,
            foundCount: update.data.foundMiners?.length || 0,
            statusText: update.data.currentIp 
              ? `Scanning ${update.data.currentIp}...`
              : 'Scanning network...'
          }
          
          // Update found miners
          if (update.data.foundMiners) {
            foundMiners.value = update.data.foundMiners
          }
        } else if (update.data.status === 'completed') {
          isScanning.value = false
          scanProgress.value = {
            ...scanProgress.value,
            visible: false,
            percentage: 100
          }
          
          if (update.data.foundMiners && update.data.foundMiners.length > 0) {
            foundMiners.value = update.data.foundMiners
            showSuccess(`Scan completed! Found ${update.data.foundMiners.length} miner${update.data.foundMiners.length === 1 ? '' : 's'}`)
          } else {
            showInfo('Scan completed. No miners found on the network.')
          }
        } else if (update.data.status === 'error') {
          isScanning.value = false
          scanProgress.value = {
            ...scanProgress.value,
            visible: false
          }
          scanError.value = update.data.error || 'Unknown scan error occurred'
          showError(`Scan failed: ${scanError.value}`)
        }
        break
        
      case 'scan_stopped':
        isScanning.value = false
        scanProgress.value = {
          ...scanProgress.value,
          visible: false
        }
        showWarning('Network scan stopped')
        break
        
      case 'scan_error':
        isScanning.value = false
        scanProgress.value = {
          ...scanProgress.value,
          visible: false
        }
        scanError.value = update.data.error || 'Unknown error occurred'
        showError(`Failed to start scan: ${scanError.value}`)
        break
    }
  }

  /**
   * Start a network scan
   * @param {Object} options - Scan configuration
   * @param {string} options.network - Network range (CIDR or IP range)
   * @param {Array} options.ports - Ports to scan (optional)
   * @param {number} options.timeout - Connection timeout (optional)
   * @returns {Promise<boolean>} - Success status
   */
  const startScan = async (options = {}) => {
    try {
      scanError.value = ''
      return await networkScanService.startScan(options)
    } catch (error) {
      console.error('Error starting network scan:', error)
      scanError.value = error.message
      showError(`Failed to start scan: ${error.message}`)
      return false
    }
  }

  /**
   * Stop the current scan
   * @returns {Promise<boolean>} - Success status
   */
  const stopScan = async () => {
    try {
      return await networkScanService.stopScan()
    } catch (error) {
      console.error('Error stopping network scan:', error)
      showError(`Failed to stop scan: ${error.message}`)
      return false
    }
  }

  /**
   * Get current scan status
   * @returns {Promise<Object>} - Current scan status
   */
  const getScanStatus = async () => {
    try {
      return await networkScanService.getScanStatus()
    } catch (error) {
      console.error('Error getting scan status:', error)
      return { status: 'error', error: error.message }
    }
  }

  /**
   * Quick scan with default settings
   * @param {string} network - Network to scan (defaults to 192.168.1.0/24)
   * @returns {Promise<boolean>} - Success status
   */
  const quickScan = async (network = '192.168.1.0/24') => {
    return await startScan({ network })
  }

  /**
   * Get current scan state
   * @returns {Object} - Current state
   */
  const getCurrentState = () => {
    return {
      isScanning: isScanning.value,
      scanProgress: scanProgress.value,
      foundMiners: foundMiners.value,
      scanError: scanError.value
    }
  }

  // Lifecycle management
  onMounted(() => {
    // Add listener to network scan service
    networkScanService.addListener(handleScanUpdate)
    
    // Get initial state
    const currentState = networkScanService.getCurrentState()
    if (currentState.isScanning) {
      isScanning.value = true
      scanProgress.value.visible = true
    }
    if (currentState.foundMiners && currentState.foundMiners.length > 0) {
      foundMiners.value = currentState.foundMiners
    }
  })

  onUnmounted(() => {
    // Remove listener from network scan service
    networkScanService.removeListener(handleScanUpdate)
  })

  return {
    // Reactive state
    isScanning,
    scanProgress,
    foundMiners,
    scanError,

    // Methods
    startScan,
    stopScan,
    getScanStatus,
    quickScan,
    getCurrentState
  }
}

export default useNetworkScan