<template>
  <v-app>
    <v-navigation-drawer
      v-if="!isSetupRoute"
      v-model="drawer"
      app
    >
      <v-list-item>
        <template v-slot:prepend>
          <BitcoinLogo 
            size="md" 
            variant="default" 
            :animated="false"
            aria-label="Bitcoin Solo Miner Monitor Logo"
            alt-text="Bitcoin Logo"
            class="mr-3"
          />
        </template>
        <v-list-item-title class="text-h6">
          Bitcoin Solo Miner Monitor
        </v-list-item-title>
        <v-list-item-subtitle>
          Monitor your mining fleet
        </v-list-item-subtitle>
      </v-list-item>

      <v-divider></v-divider>

      <v-list
        dense
        nav
      >
        <v-list-item
          v-for="item in menuItems"
          :key="item.title"
          :to="item.to"
          link
        >
          <template v-slot:prepend>
            <v-icon>{{ item.icon }}</v-icon>
          </template>
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list>
      
      <template v-slot:append>
        <div class="pa-2">
          <v-btn
            block
            color="primary"
            @click="navigateToMinersPage"
          >
            <v-icon left>mdi-plus</v-icon>
            Add Miner
          </v-btn>
        </div>
      </template>
    </v-navigation-drawer>

    <v-app-bar v-if="!isSetupRoute" app>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <BitcoinLogo 
        size="sm" 
        variant="default" 
        :animated="false"
        aria-label="Bitcoin Solo Miner Monitor Logo"
        alt-text="Bitcoin Logo"
        class="ml-4 mr-3"
      />
      <v-toolbar-title>{{ currentPageTitle }}</v-toolbar-title>
      <v-spacer></v-spacer>
      
      <!-- WebSocket Connection Status -->
      <v-chip
        :color="connectionStatusColor"
        size="small"
        class="mr-2"
      >
        <v-icon start size="small">{{ connectionStatusIcon }}</v-icon>
        {{ connectionStatusText }}
      </v-chip>
      
      <v-btn 
        icon 
        @click="refreshData"
        :loading="refreshing"
        :disabled="refreshing"
        :title="refreshing ? 'Refreshing data...' : 'Refresh all data'"
      >
        <v-icon :class="{ 'refresh-spinning': refreshing }">mdi-refresh</v-icon>
      </v-btn>
      <v-btn 
        icon 
        @click="checkForUpdates"
        :loading="checkingUpdates"
        :disabled="checkingUpdates"
        :title="checkingUpdates ? 'Checking for updates...' : 'Check for updates'"
      >
        <v-icon>mdi-download</v-icon>
      </v-btn>
      <v-btn icon @click="openSettingsDialog">
        <v-icon>mdi-cog</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main :class="{ 'setup-main': isSetupRoute }">
      <v-container v-if="!isSetupRoute" fluid>
        <router-view />
      </v-container>
      <router-view v-else />
    </v-main>



    <!-- Settings Dialog -->
    <v-dialog
      v-model="settingsDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title>
          Settings
        </v-card-title>
        <v-card-text>
          <v-form ref="settingsForm" v-model="settingsFormValid">
            <v-text-field
              v-model="settings.polling_interval"
              label="Polling Interval (seconds)"
              type="number"
              required
              :rules="[
                v => !!v || 'Polling interval is required',
                v => v >= 5 || 'Polling interval must be at least 5 seconds'
              ]"
            ></v-text-field>
            <v-text-field
              v-model="settings.refresh_interval"
              label="UI Refresh Interval (seconds)"
              type="number"
              required
              :rules="[
                v => !!v || 'Refresh interval is required',
                v => v >= 1 || 'Refresh interval must be at least 1 second'
              ]"
            ></v-text-field>
            <v-text-field
              v-model="settings.chart_retention_days"
              label="Chart Data Retention (days)"
              type="number"
              required
              :rules="[
                v => !!v || 'Chart retention is required',
                v => v >= 1 || 'Chart retention must be at least 1 day'
              ]"
            ></v-text-field>
            <v-select
              v-model="settings.theme"
              :items="[{title: 'Dark', value: 'dark'}, {title: 'Light', value: 'light'}]"
              label="Theme"
              item-title="title"
              item-value="value"
            ></v-select>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="settingsDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="text"
            @click="saveSettings"
            :disabled="!settingsFormValid"
            :loading="settingsLoading"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
      location="bottom"
      :multi-line="false"
    >
      {{ snackbar.text }}
      <template v-slot:action="{ attrs }">
        <v-btn
          text
          v-bind="attrs"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>

    <!-- Update Notification -->
    <UpdateNotification />

    <!-- Footer with donation address -->
    <v-footer v-if="!isSetupRoute" class="pa-2 footer-fixed">
      <v-container fluid>
        <v-row align="center" justify="space-between">
          <v-col cols="auto">
            <span class="text-caption text-medium-emphasis">
              Bitcoin Solo Miner Monitor
            </span>
          </v-col>
          <v-col cols="auto" class="text-center">
            <span class="text-caption text-medium-emphasis">
              If you find value in this app, please consider leaving a tip! 
              <span 
                class="donation-address" 
                @click="copyDonationAddress"
                title="Click to copy address to clipboard"
              >
                bc1qnce06pg2gqewjvjmfavwrjt5f4zc37k5d26c6e
              </span>
            </span>
          </v-col>
          <v-col cols="auto">
            <span class="text-caption text-medium-emphasis">
              Est. 1986
              <span class="gaming-hint easter-egg-hint" title="Patterns from gaming's golden age still hold power">🎮</span>
            </span>
          </v-col>
        </v-row>
      </v-container>
    </v-footer>
  </v-app>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMinersStore } from './stores/miners'
import { useSettingsStore } from './stores/settings'
import { useAlertsStore } from './stores/alerts'
import { isFirstRun, getDiscoveredMiners, getInitialRoute } from './services/firstRunService'
import { connectionStatus, forceReconnect } from './services/websocket'
import { useEasterEgg } from './composables/useEasterEgg'
import { useUpdateChecker } from './composables/useUpdateChecker'
import BitcoinLogo from './components/BitcoinLogo.vue'
import UpdateNotification from './components/UpdateNotification.vue'


export default {
  name: 'App',
  
  components: {
    BitcoinLogo,
    UpdateNotification
  },
  
  setup() {
    const route = useRoute()
    const router = useRouter()
    const minersStore = useMinersStore()
    const settingsStore = useSettingsStore()
    const alertsStore = useAlertsStore()
    
    // Initialize easter egg
    const easterEgg = useEasterEgg()
    
    // Initialize update checker
    let checkUpdates, checkingUpdates
    try {
      const updateChecker = useUpdateChecker()
      checkUpdates = updateChecker.checkForUpdates
      checkingUpdates = updateChecker.isChecking
    } catch (error) {
      console.error('Failed to initialize update checker:', error)
      // Provide fallback values
      checkUpdates = async () => { console.warn('Update checker not available') }
      checkingUpdates = ref(false)
    }
    
    // Navigation drawer state
    const drawer = ref(true)
    
    // Check for UI mode preference
    const uiMode = ref(localStorage.getItem('uiMode') || 'advanced')
    
    // Watch for localStorage changes to uiMode
    const updateUIMode = () => {
      const newMode = localStorage.getItem('uiMode') || 'advanced'
      if (uiMode.value !== newMode) {
        uiMode.value = newMode
      }
    }
    
    // Listen for storage events (when localStorage is changed from other tabs/components)
    window.addEventListener('storage', updateUIMode)
    
    // Also watch for route changes to update UI mode if needed
    watch(() => route.path, () => {
      updateUIMode()
    })
    
    // Menu items
    const menuItems = computed(() => {
      const items = [
        { 
          title: 'Dashboard', 
          icon: 'mdi-view-dashboard', 
          to: uiMode.value === 'simple' ? '/dashboard-simple' : '/' 
        },
        { title: 'Miners', icon: 'mdi-server', to: '/miners' },
        { title: 'Analytics', icon: 'mdi-chart-line', to: '/analytics' },
        { title: 'Network', icon: 'mdi-network', to: '/network' },
        { title: 'Settings', icon: 'mdi-cog', to: '/settings' },
        { title: 'About', icon: 'mdi-information', to: '/about' },
      ]
      
      return items
    })
    
    // Current page title
    const currentPageTitle = computed(() => {
      const currentRoute = route.path
      const items = menuItems.value
      if (!Array.isArray(items)) return 'Bitcoin Solo Miner Monitor'
      const currentMenuItem = items.find(item => item.to === currentRoute)
      return currentMenuItem ? currentMenuItem.title : 'Bitcoin Solo Miner Monitor'
    })
    
    // Check if current route is setup
    const isSetupRoute = computed(() => {
      return route.path === '/setup'
    })
    

    
    // Settings dialog
    const settingsDialog = ref(false)
    const settingsFormValid = ref(true) // Initialize as true since we load valid settings
    const settingsForm = ref(null)
    const settings = ref({
      polling_interval: 30,
      refresh_interval: 10,
      chart_retention_days: 30
    })
    
    // Computed property for settings loading state
    const settingsLoading = computed(() => {
      return settingsStore?.loading || false
    })
    

    
    // Refresh state
    const refreshing = ref(false)
    
    // Snackbar for notifications
    const snackbar = ref({
      show: false,
      text: '',
      color: 'info',
      timeout: 3000
    })
    
    // Methods
    const navigateToMinersPage = () => {
      router.push('/miners')
    }
    
    const openSettingsDialog = () => {
      // Load current settings from store
      settings.value = {
        polling_interval: settingsStore.settings.polling_interval || 30,
        refresh_interval: settingsStore.settings.refresh_interval || 10,
        chart_retention_days: settingsStore.settings.chart_retention_days || 30,
        theme: settingsStore.settings.theme || 'dark'
      }
      console.log('Opening settings dialog with current settings:', settings.value)
      settingsDialog.value = true
      
      // Ensure form validation is triggered after dialog opens
      setTimeout(() => {
        if (settingsForm.value) {
          settingsForm.value.validate()
        }
      }, 100)
    }
    
    const saveSettings = async () => {
      console.log('saveSettings method called!')
      console.log('settingsFormValid:', settingsFormValid.value)
      console.log('settingsStore.loading:', settingsStore?.loading)
      
      if (settingsStore?.loading) {
        console.log('Settings save already in progress, skipping...')
        return
      }
      
      try {
        // Convert string values to appropriate types before saving
        const settingsToSave = {
          ...settings.value,
          polling_interval: parseInt(settings.value.polling_interval) || 30,
          refresh_interval: parseInt(settings.value.refresh_interval) || 10,
          chart_retention_days: parseInt(settings.value.chart_retention_days) || 30
        }
        
        console.log('Saving settings:', settingsToSave)
        await settingsStore.updateSettings(settingsToSave)
        
        // Auto-close dialog on successful save
        settingsDialog.value = false
        
        // Show success notification
        showSnackbar('Settings saved successfully', 'success')
        
        console.log('Settings saved and applied successfully')
      } catch (error) {
        console.error('Error saving settings:', error)
        showSnackbar(`Error saving settings: ${error.message}`, 'error')
      }
    }
    
    const refreshData = async () => {
      if (refreshing.value) {
        console.log('Refresh already in progress, skipping...')
        return
      }
      
      try {
        refreshing.value = true
        console.log('Starting data refresh...')
        
        // Handle WebSocket reconnection for disconnected states
        if (connectionStatus.value === 'disconnected' || connectionStatus.value === 'error') {
          console.log('Refresh: WebSocket disconnected, forcing reconnection...')
          showSnackbar('Reconnecting...', 'warning')
          
          try {
            forceReconnect()
            
            // Wait for reconnection to start with timeout
            let reconnectTimeout = 0
            const maxReconnectWait = 2000 // 2 seconds max wait
            
            while (connectionStatus.value === 'disconnected' && reconnectTimeout < maxReconnectWait) {
              await new Promise(resolve => setTimeout(resolve, 100))
              reconnectTimeout += 100
            }
            
            if (connectionStatus.value === 'connecting' || connectionStatus.value === 'reconnecting') {
              console.log('WebSocket reconnection initiated successfully')
            } else {
              console.warn('WebSocket reconnection may have failed, continuing with data refresh')
            }
          } catch (reconnectError) {
            console.error('Error during WebSocket reconnection:', reconnectError)
            showSnackbar('Reconnection failed, refreshing data only', 'warning')
          }
        }
        
        // Refresh all relevant data sources
        const refreshPromises = []
        
        // 1. Refresh miners data
        console.log('Refreshing miners data...')
        refreshPromises.push(
          minersStore.fetchMiners().catch(error => {
            console.error('Failed to refresh miners:', error)
            throw new Error(`Miners: ${error.message}`)
          })
        )
        
        // 2. Refresh settings data
        console.log('Refreshing settings data...')
        refreshPromises.push(
          settingsStore.fetchSettings().catch(error => {
            console.error('Failed to refresh settings:', error)
            // Don't throw for settings errors, just log them
            console.warn('Settings refresh failed, continuing with other data')
          })
        )
        
        // 3. Refresh alerts data
        console.log('Refreshing alerts data...')
        refreshPromises.push(
          alertsStore.fetchAlerts().catch(error => {
            console.error('Failed to refresh alerts:', error)
            // Don't throw for alerts errors, just log them
            console.warn('Alerts refresh failed, continuing with other data')
          })
        )
        
        // Execute all refresh operations with timeout
        const refreshTimeout = 10000 // 10 seconds timeout
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Refresh operation timed out')), refreshTimeout)
        })
        
        let refreshResults
        try {
          refreshResults = await Promise.race([
            Promise.allSettled(refreshPromises),
            timeoutPromise
          ])
        } catch (timeoutError) {
          console.error('Refresh operation timed out:', timeoutError)
          throw new Error('Refresh timed out - please try again')
        }
        
        // Check for any critical failures (miners data is critical)
        const minersResult = refreshResults[0]
        if (minersResult && minersResult.status === 'rejected') {
          console.error('Critical: Miners data refresh failed:', minersResult.reason)
          throw new Error(`Failed to refresh miners data: ${minersResult.reason.message}`)
        }
        
        // Log any non-critical failures
        refreshResults.forEach((result, index) => {
          if (result.status === 'rejected') {
            const dataType = index === 0 ? 'miners' : index === 1 ? 'settings' : 'alerts'
            console.warn(`Non-critical: ${dataType} refresh failed:`, result.reason)
          }
        })
        
        // Check if WebSocket reconnection was successful
        if (connectionStatus.value === 'connected') {
          console.log('Refresh completed successfully with WebSocket connected')
          showSnackbar('Data refreshed successfully', 'success')
        } else if (connectionStatus.value === 'connecting' || connectionStatus.value === 'reconnecting') {
          console.log('Refresh completed, WebSocket still reconnecting')
          showSnackbar('Data refreshed, reconnecting...', 'info')
        } else {
          console.log('Refresh completed but WebSocket connection failed')
          showSnackbar('Data refreshed (offline mode)', 'warning')
        }
        
      } catch (error) {
        console.error('Error during data refresh:', error)
        showSnackbar(`Refresh failed: ${error.message}`, 'error')
      } finally {
        refreshing.value = false
        console.log('Data refresh completed')
      }
    }
    
    const showSnackbar = (text, color = 'info') => {
      snackbar.value = {
        show: true,
        text,
        color,
        timeout: 3000
      }
    }
    
    const copyDonationAddress = async () => {
      const donationAddress = 'bc1qnce06pg2gqewjvjmfavwrjt5f4zc37k5d26c6e'
      try {
        await navigator.clipboard.writeText(donationAddress)
        showSnackbar('Donation address copied to clipboard! Thank you for your support! 🧡', 'success')
      } catch (error) {
        // Fallback for older browsers or when clipboard API is not available
        const textArea = document.createElement('textarea')
        textArea.value = donationAddress
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        showSnackbar('Donation address copied to clipboard! Thank you for your support! 🧡', 'success')
      }
    }
    
    const checkForUpdates = async () => {
      try {
        await checkUpdates(true) // Force refresh
        showSnackbar('Update check completed', 'info')
      } catch (error) {
        showSnackbar(`Update check failed: ${error.message}`, 'error')
      }
    }
    
    const addDiscoveredMiners = async () => {
      // Temporarily disabled to prevent connection timeouts during testing phase
      console.log('addDiscoveredMiners disabled during testing phase to prevent unresponsiveness')
      
      // Clear any existing discovered miners to prevent future issues
      localStorage.removeItem('discoveredMiners')
      console.log('Cleared discovered miners from localStorage')
      
      return
      
      /* Original implementation - re-enable after testing phase
      try {
        const discoveredMiners = getDiscoveredMiners()
        console.log('Discovered miners from installer:', discoveredMiners)
        
        if (discoveredMiners && discoveredMiners.length > 0) {
          // Check if these miners are already added
          // const currentMiners = minersStore.miners // TEMPORARILY DISABLED - PINIA ISSUE
          
          for (const discoveredMiner of discoveredMiners) {
            // Check if miner already exists (by IP address)
            const existingMiner = currentMiners.find(m => m.ip_address === discoveredMiner.ip)
            
            if (!existingMiner) {
              console.log(`Adding discovered miner: ${discoveredMiner.name} (${discoveredMiner.ip})`)
              
              try {
                // await minersStore.addMiner({ // TEMPORARILY DISABLED - PINIA ISSUE
                  type: discoveredMiner.type,
                  ip_address: discoveredMiner.ip,
                  // Don't include port field to use default port
                  name: discoveredMiner.name
                })
                
                console.log(`Successfully added miner: ${discoveredMiner.name}`)
              } catch (error) {
                console.warn(`Failed to add miner ${discoveredMiner.name}:`, error.message)
              }
            } else {
              console.log(`Miner ${discoveredMiner.name} already exists, skipping`)
            }
          }
          
          // Clear discovered miners from localStorage after adding them
          localStorage.removeItem('discoveredMiners')
          console.log('Cleared discovered miners from localStorage')
          
          // Show success message
          showSnackbar(`Added ${discoveredMiners.length} miners from installer`, 'success')
        }
      } catch (error) {
        console.error('Error adding discovered miners:', error)
        showSnackbar('Error adding discovered miners', 'error')
      }
      */
    }
    
    // Lifecycle hooks - MINIMAL FOR PHASE 1 TESTING
    onMounted(async () => {
      // Check if this is the first run and redirect accordingly
      console.log('=== APP MOUNTED - FIRST RUN CHECK ===')
      console.log('localStorage firstRunComplete:', localStorage.getItem('firstRunComplete'))
      console.log('Current route path:', route.path)
      
      try {
        console.log('About to call isFirstRun()...')
        const firstRun = await isFirstRun()
        console.log('isFirstRun() returned:', firstRun, 'type:', typeof firstRun)
        
        if (firstRun === true) {
          console.log('First run detected, redirecting to setup')
          await router.push('/setup')
        } else {
          console.log('Not a first run, current path:', route.path)
          // Not a first run, ensure we're not on the setup page
          if (route.path === '/setup') {
            console.log('On setup page but first run is complete, redirecting...')
            // Redirect to appropriate dashboard based on user preferences
            const initialRoute = getInitialRoute()
            console.log('Initial route determined:', initialRoute)
            await router.push(initialRoute)
            console.log('Redirect completed to:', initialRoute)
          } else {
            console.log('Not on setup page, staying on current route:', route.path)
          }
        }
      } catch (error) {
        console.error('Error in first run check:', error)
      }
      

      
      console.log('=== APP MOUNTED COMPLETE ===')
    })
    
    // Cleanup event listeners
    onUnmounted(() => {
      window.removeEventListener('storage', updateUIMode)
    })
    
    // Original complex onMounted logic (disabled for Phase 1):
    /*
    onMounted(async () => {
      console.log('=== APP MOUNTED - FIRST RUN CHECK ===')
      console.log('localStorage firstRunComplete:', localStorage.getItem('firstRunComplete'))
      console.log('Current route path:', route.path)
      
      console.log('✅ DOM ready, starting first run check...')
      
      try {
        console.log('✅ About to call isFirstRun()...')
        const firstRun = await isFirstRun()
        console.log('✅ isFirstRun() completed, returned:', firstRun, 'type:', typeof firstRun)
        
        if (firstRun === true) {
          console.log('✅ First run detected, redirecting to setup')
          console.log('Current route before redirect:', route.path)
          
          try {
            console.log('✅ About to call router.push("/setup")...')
            await router.push('/setup')
            console.log('✅ Router push completed successfully')
            console.log('New route after redirect:', route.path)
          } catch (routerError) {
            console.error('❌ Router push failed:', routerError)
          }
          console.log('✅ Setup redirect complete, exiting onMounted')
          return
        } else {
          console.log('❌ Not a first run, will initialize normal app')
        }
      } catch (error) {
        console.error('❌ Error checking first run status:', error)
        console.log('Falling back to normal app initialization')
      }
      
      console.log('=== INITIALIZING NORMAL APP ===')
      console.log('Final route path:', route.path)
      
      console.log('API calls disabled during Phase 1 testing')
      console.log('This prevents hanging on backend connections during setup wizard testing')
      
      console.log('WebSocket connection disabled during Phase 1 testing to prevent browser unresponsiveness')
      
      console.log('✅ App initialization complete - onMounted finished')
      console.log('=== END APP MOUNTED ===')
      
      setTimeout(() => {
        console.log('✅ 5 seconds after mount - page should be responsive')
      }, 5000)
    })
    */
    
    // WebSocket connection status
    const connectionStatusColor = computed(() => {
      switch (connectionStatus.value) {
        case 'connected': return 'success'
        case 'connecting': 
        case 'reconnecting': return 'warning'
        case 'disconnected': return 'error'
        case 'error': return 'error'
        default: return 'info'
      }
    })
    
    const connectionStatusIcon = computed(() => {
      switch (connectionStatus.value) {
        case 'connected': return 'mdi-wifi'
        case 'connecting': 
        case 'reconnecting': return 'mdi-wifi-sync'
        case 'disconnected': return 'mdi-wifi-off'
        case 'error': return 'mdi-wifi-alert'
        default: return 'mdi-wifi-off'
      }
    })
    
    const connectionStatusText = computed(() => {
      switch (connectionStatus.value) {
        case 'connected': return 'Connected'
        case 'connecting': return 'Connecting'
        case 'reconnecting': return 'Reconnecting'
        case 'disconnected': return 'Disconnected'
        case 'error': return 'Connection Error'
        default: return 'Unknown'
      }
    })


    
    return {
      drawer,
      menuItems,
      currentPageTitle,
      isSetupRoute,
      settingsDialog,
      settingsFormValid,
      settingsForm,
      settings,
      settingsStore, // Add settingsStore to fix the loading state access
      settingsLoading, // Add computed loading state
      refreshing,
      snackbar,
      navigateToMinersPage,
      openSettingsDialog,
      saveSettings,
      refreshData,
      copyDonationAddress,
      checkForUpdates,
      connectionStatusColor,
      connectionStatusIcon,
      connectionStatusText,
      checkingUpdates,
      
      // Easter egg (for development debugging)
      easterEgg
    }
  }
}
</script>

<style scoped>
/* Setup route styling - remove all padding and margins for fullscreen wizard */
.setup-main {
  padding: 0 !important;
}

.setup-main :deep(.v-container) {
  padding: 0 !important;
  margin: 0 !important;
  max-width: none !important;
}

/* Navigation drawer styling */
:deep(.v-navigation-drawer) {
  background-color: var(--color-surface) !important;
  border-right: 1px solid var(--color-border-subtle);
}

:deep(.v-navigation-drawer .v-list-item) {
  color: var(--color-text-primary) !important;
}

:deep(.v-navigation-drawer .v-list-item-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-navigation-drawer .v-list-item-subtitle) {
  color: var(--color-text-secondary) !important;
}

:deep(.v-navigation-drawer .v-list-item--active) {
  background-color: var(--color-primary-alpha-10) !important;
  color: var(--color-primary) !important;
}

:deep(.v-navigation-drawer .v-list-item--active .v-list-item-title) {
  color: var(--color-primary) !important;
}

:deep(.v-navigation-drawer .v-list-item:hover) {
  background-color: var(--color-surface-hover) !important;
}

:deep(.v-navigation-drawer .v-divider) {
  border-color: var(--color-border-subtle) !important;
}

/* App bar styling */
:deep(.v-app-bar) {
  background-color: var(--color-surface) !important;
  border-bottom: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
}

:deep(.v-app-bar .v-toolbar-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-app-bar .v-btn) {
  color: var(--color-text-primary) !important;
}

/* Main content area */
:deep(.v-main) {
  background-color: var(--color-background) !important;
}

:deep(.v-container) {
  background-color: transparent;
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
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-semibold);
}

:deep(.v-dialog .v-card-text) {
  color: var(--color-text-primary) !important;
}

/* Form styling */
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

:deep(.v-text-field .v-field__input::placeholder) {
  color: var(--color-text-hint) !important;
}

:deep(.v-select .v-field) {
  background-color: var(--color-surface-secondary) !important;
  border: 1px solid var(--color-border);
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

/* Snackbar styling */
:deep(.v-snackbar .v-snackbar__wrapper) {
  background-color: var(--color-surface-elevated) !important;
  color: var(--color-text-primary) !important;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-3);
}

/* Footer styling */
:deep(.v-footer) {
  background-color: var(--color-surface) !important;
  border-top: 1px solid var(--color-border-subtle);
  color: var(--color-text-secondary) !important;
  height: 64px !important;
  min-height: 64px !important;
  max-height: 64px !important;
  padding: 12px 16px !important;
  display: flex !important;
  align-items: center !important;
  box-sizing: border-box !important;
}

/* Ensure footer text sizing is consistent */
:deep(.v-footer .text-caption) {
  font-size: 12px !important;
  line-height: 1.4 !important;
}

/* Responsive footer adjustments */
@media (max-width: 768px) {
  :deep(.v-footer) {
    height: 64px !important;
    min-height: 64px !important;
    max-height: 64px !important;
    padding: 12px 16px !important;
  }
}

@media (max-width: 480px) {
  :deep(.v-footer) {
    height: 64px !important;
    min-height: 64px !important;
    max-height: 64px !important;
    padding: 8px 12px !important;
  }
  
  :deep(.v-footer .text-caption) {
    font-size: 11px !important;
  }
}

/* Standardized footer positioning and sizing */
.footer-fixed {
  position: relative !important;
  bottom: auto !important;
  left: auto !important;
  right: auto !important;
  width: 100% !important;
  z-index: auto !important;
  height: 64px !important;
  min-height: 64px !important;
  max-height: 64px !important;
  padding: 12px 16px !important;
  display: flex !important;
  align-items: center !important;
  box-sizing: border-box !important;
}

/* Ensure footer consistency across all screen sizes */
@media (max-width: 768px) {
  .footer-fixed {
    height: 64px !important;
    min-height: 64px !important;
    max-height: 64px !important;
    padding: 12px 16px !important;
  }
}

@media (max-width: 480px) {
  .footer-fixed {
    height: 64px !important;
    min-height: 64px !important;
    max-height: 64px !important;
    padding: 8px 12px !important;
  }
}

/* Easter egg hint styling */
.easter-egg-hint {
  cursor: help;
  transition: all var(--transition-fast);
  opacity: 0.7;
}

.easter-egg-hint:hover {
  opacity: 1;
  transform: scale(1.1);
}

.gaming-hint {
  font-size: var(--font-size-small);
  margin-left: var(--spacing-xs);
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  :deep(.v-btn),
  .easter-egg-hint {
    transition: none;
    transform: none !important;
  }
  
  :deep(.v-btn:hover),
  .easter-egg-hint:hover {
    transform: none !important;
  }
}

/* Refresh button animation */
.refresh-spinning {
  animation: refresh-spin 1s linear infinite;
}

@keyframes refresh-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :deep(.v-navigation-drawer),
  :deep(.v-app-bar),
  :deep(.v-dialog .v-card) {
    border-width: 2px;
  }
  
  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .refresh-spinning {
    animation: none;
  }
  
  :deep(.v-btn),
  .easter-egg-hint {
    transition: none;
    transform: none !important;
  }
  
  :deep(.v-btn:hover),
  .easter-egg-hint:hover {
    transform: none !important;
  }
}

/* Donation address styling */
.donation-address {
  color: #F7931A !important; /* Bitcoin orange */
  text-decoration: underline;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.donation-address:hover {
  color: #FF8C00 !important; /* Slightly brighter orange on hover */
  text-decoration: underline;
  opacity: 0.8;
}

.donation-address:active {
  transform: scale(0.98);
}

/* Ensure donation address is accessible */
@media (prefers-reduced-motion: reduce) {
  .donation-address {
    transition: none;
  }
  
  .donation-address:active {
    transform: none;
  }
}

/* Settings dialog actions visibility fix */
:deep(.settings-dialog-actions) {
  display: flex !important;
  justify-content: flex-end !important;
  align-items: center !important;
  padding: 16px 24px !important;
  min-height: 64px !important;
  border-top: 1px solid rgba(var(--v-border-color), 0.12);
  background-color: rgba(var(--v-theme-surface), 1) !important;
}

:deep(.settings-dialog-actions .v-btn) {
  margin-left: 8px !important;
  min-width: 80px !important;
}
</style>