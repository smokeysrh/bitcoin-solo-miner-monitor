/**
 * Update Checker Composable
 * 
 * Provides functionality for checking application updates from GitHub releases.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

export function useUpdateChecker() {
  // Reactive state
  const updateInfo = ref(null)
  const isChecking = ref(false)
  const lastChecked = ref(null)
  const error = ref(null)
  const checkInterval = ref(null)
  
  // Auto-check interval (24 hours)
  const AUTO_CHECK_INTERVAL = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
  
  // Computed properties
  const hasUpdate = computed(() => {
    return updateInfo.value && updateInfo.value.update_available === true
  })
  
  const currentVersion = computed(() => {
    return updateInfo.value ? updateInfo.value.current_version : 'Unknown'
  })
  
  const latestVersion = computed(() => {
    return updateInfo.value ? updateInfo.value.latest_version : 'Unknown'
  })
  
  const releaseNotes = computed(() => {
    return updateInfo.value ? updateInfo.value.release_notes : ''
  })
  
  const downloadUrl = computed(() => {
    return updateInfo.value ? updateInfo.value.download_url : ''
  })
  
  const releaseAssets = computed(() => {
    return updateInfo.value ? updateInfo.value.assets || [] : []
  })
  
  const isUpdateAvailable = computed(() => {
    return hasUpdate.value && !error.value
  })
  
  // Methods
  const checkForUpdates = async (forceRefresh = false) => {
    if (isChecking.value) {
      console.log('Update check already in progress')
      return
    }
    
    try {
      isChecking.value = true
      error.value = null
      
      console.log('Checking for updates...', forceRefresh ? '(forced refresh)' : '')
      
      const response = await axios.get('/api/updates/check', {
        params: { force_refresh: forceRefresh },
        timeout: 30000 // 30 second timeout
      })
      
      if (response.data.status === 'success') {
        updateInfo.value = response.data.data
        lastChecked.value = new Date()
        
        console.log('Update check completed:', {
          current: updateInfo.value.current_version,
          latest: updateInfo.value.latest_version,
          updateAvailable: updateInfo.value.update_available
        })
        
        // Store last check time in localStorage
        localStorage.setItem('lastUpdateCheck', lastChecked.value.toISOString())
        
        return updateInfo.value
      } else {
        throw new Error(response.data.message || 'Failed to check for updates')
      }
      
    } catch (err) {
      console.error('Error checking for updates:', err)
      error.value = err.response?.data?.message || err.message || 'Failed to check for updates'
      
      // If we have cached update info, keep it
      if (!updateInfo.value) {
        updateInfo.value = {
          update_available: false,
          current_version: 'Unknown',
          error: error.value
        }
      }
      
      throw err
    } finally {
      isChecking.value = false
    }
  }
  
  const getUpdateStatus = async () => {
    try {
      const response = await axios.get('/api/updates/status', {
        timeout: 10000 // 10 second timeout
      })
      
      if (response.data.status === 'success') {
        updateInfo.value = response.data.data
        return updateInfo.value
      } else {
        throw new Error(response.data.message || 'Failed to get update status')
      }
      
    } catch (err) {
      console.error('Error getting update status:', err)
      error.value = err.response?.data?.message || err.message || 'Failed to get update status'
      throw err
    }
  }
  
  const getUpdateInstructions = async (platform = null) => {
    try {
      const params = platform ? { platform } : {}
      const response = await axios.get('/api/updates/instructions', {
        params,
        timeout: 10000
      })
      
      if (response.data.status === 'success') {
        return response.data.data
      } else {
        throw new Error(response.data.message || 'Failed to get update instructions')
      }
      
    } catch (err) {
      console.error('Error getting update instructions:', err)
      throw err
    }
  }
  
  const dismissUpdate = () => {
    // Store dismissed version in localStorage
    if (updateInfo.value && updateInfo.value.latest_version) {
      const dismissedVersions = JSON.parse(localStorage.getItem('dismissedUpdates') || '[]')
      if (!dismissedVersions.includes(updateInfo.value.latest_version)) {
        dismissedVersions.push(updateInfo.value.latest_version)
        localStorage.setItem('dismissedUpdates', JSON.stringify(dismissedVersions))
      }
    }
  }
  
  const isDismissed = computed(() => {
    if (!updateInfo.value || !updateInfo.value.latest_version) return false
    
    const dismissedVersions = JSON.parse(localStorage.getItem('dismissedUpdates') || '[]')
    return dismissedVersions.includes(updateInfo.value.latest_version)
  })
  
  const shouldShowNotification = computed(() => {
    return hasUpdate.value && !isDismissed.value && !error.value
  })
  
  const startAutoCheck = () => {
    // Clear any existing interval
    stopAutoCheck()
    
    // Set up periodic checking
    checkInterval.value = setInterval(async () => {
      try {
        console.log('Performing automatic update check...')
        await checkForUpdates(false) // Don't force refresh for auto-checks
      } catch (err) {
        console.warn('Automatic update check failed:', err.message)
      }
    }, AUTO_CHECK_INTERVAL)
    
    console.log('Automatic update checking started (every 24 hours)')
  }
  
  const stopAutoCheck = () => {
    if (checkInterval.value) {
      clearInterval(checkInterval.value)
      checkInterval.value = null
      console.log('Automatic update checking stopped')
    }
  }
  
  const shouldPerformAutoCheck = () => {
    const lastCheckStr = localStorage.getItem('lastUpdateCheck')
    if (!lastCheckStr) return true
    
    const lastCheck = new Date(lastCheckStr)
    const now = new Date()
    const timeSinceLastCheck = now - lastCheck
    
    return timeSinceLastCheck >= AUTO_CHECK_INTERVAL
  }
  
  const initializeUpdateChecker = async () => {
    try {
      // Load last check time from localStorage
      const lastCheckStr = localStorage.getItem('lastUpdateCheck')
      if (lastCheckStr) {
        lastChecked.value = new Date(lastCheckStr)
      }
      
      // Try to get cached update status first
      await getUpdateStatus()
      
      // Perform auto-check if needed
      if (shouldPerformAutoCheck()) {
        console.log('Performing initial update check...')
        await checkForUpdates(false)
      }
      
      // Start automatic checking
      startAutoCheck()
      
    } catch (err) {
      console.warn('Failed to initialize update checker:', err.message)
      // Don't throw - this is not critical for app functionality
    }
  }
  
  // Lifecycle hooks
  onMounted(() => {
    initializeUpdateChecker()
  })
  
  onUnmounted(() => {
    stopAutoCheck()
  })
  
  // Return public API
  return {
    // State
    updateInfo,
    isChecking,
    lastChecked,
    error,
    
    // Computed
    hasUpdate,
    currentVersion,
    latestVersion,
    releaseNotes,
    downloadUrl,
    releaseAssets,
    isUpdateAvailable,
    shouldShowNotification,
    isDismissed,
    
    // Methods
    checkForUpdates,
    getUpdateStatus,
    getUpdateInstructions,
    dismissUpdate,
    startAutoCheck,
    stopAutoCheck
  }
}