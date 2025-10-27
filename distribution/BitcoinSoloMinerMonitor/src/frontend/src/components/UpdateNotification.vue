<template>
  <v-snackbar
    v-model="showNotification"
    :timeout="-1"
    location="top"
    color="info"
    elevation="6"
    class="update-notification"
  >
    <div class="d-flex align-center">
      <v-icon class="mr-3" color="white">mdi-download</v-icon>
      <div class="flex-grow-1">
        <div class="text-subtitle-2 font-weight-medium">
          Update Available
        </div>
        <div class="text-caption">
          Version {{ latestVersion }} is now available (current: {{ currentVersion }})
        </div>
      </div>
    </div>
    
    <template v-slot:actions>
      <v-btn
        variant="text"
        size="small"
        @click="openUpdateDialog"
        class="text-white"
      >
        View Details
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        @click="dismissNotification"
        class="text-white"
      >
        Dismiss
      </v-btn>
    </template>
  </v-snackbar>

  <!-- Update Details Dialog -->
  <v-dialog
    v-model="updateDialog"
    max-width="600px"
    persistent
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-3" color="primary">mdi-download</v-icon>
        Update Available
      </v-card-title>
      
      <v-card-text>
        <div class="mb-4">
          <v-chip
            color="success"
            size="small"
            class="mr-2"
          >
            Current: {{ currentVersion }}
          </v-chip>
          <v-icon small class="mx-2">mdi-arrow-right</v-icon>
          <v-chip
            color="primary"
            size="small"
          >
            Latest: {{ latestVersion }}
          </v-chip>
        </div>
        
        <div v-if="releaseNotes" class="mb-4">
          <h4 class="text-h6 mb-2">Release Notes</h4>
          <div class="release-notes">
            <pre class="text-body-2">{{ releaseNotes }}</pre>
          </div>
        </div>
        
        <div v-if="releaseAssets.length > 0" class="mb-4">
          <h4 class="text-h6 mb-2">Downloads</h4>
          <v-list density="compact">
            <v-list-item
              v-for="asset in releaseAssets"
              :key="asset.name"
              :href="asset.download_url"
              target="_blank"
              class="download-item"
            >
              <template v-slot:prepend>
                <v-icon :color="getPlatformColor(asset.platform)">
                  {{ getPlatformIcon(asset.platform) }}
                </v-icon>
              </template>
              
              <v-list-item-title>{{ asset.name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatFileSize(asset.size) }} • {{ asset.platform }} • Downloaded {{ asset.download_count }} times
              </v-list-item-subtitle>
              
              <template v-slot:append>
                <v-btn
                  icon="mdi-download"
                  size="small"
                  variant="text"
                  :href="asset.download_url"
                  target="_blank"
                />
              </template>
            </v-list-item>
          </v-list>
        </div>
        
        <v-alert
          type="info"
          variant="tonal"
          class="mb-4"
        >
          <div class="text-body-2">
            <strong>Installation Instructions:</strong>
            <ol class="mt-2">
              <li>Download the appropriate installer for your platform</li>
              <li>Close the Bitcoin Solo Miner Monitor application</li>
              <li>Run the downloaded installer</li>
              <li>Follow the installation prompts</li>
              <li>Your settings and miner configurations will be preserved</li>
            </ol>
          </div>
        </v-alert>
        
        <v-alert
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          <div class="text-body-2">
            <strong>Security Notice:</strong>
            This is open-source software without expensive code signing certificates. 
            Your operating system may show security warnings - this is normal. 
            You can verify the download integrity using the SHA256 checksums available on GitHub.
          </div>
        </v-alert>
      </v-card-text>
      
      <v-card-actions>
        <v-btn
          color="primary"
          :href="downloadUrl"
          target="_blank"
          prepend-icon="mdi-open-in-new"
        >
          View on GitHub
        </v-btn>
        
        <v-spacer />
        
        <v-btn
          variant="text"
          @click="dismissAndClose"
        >
          Dismiss This Version
        </v-btn>
        
        <v-btn
          variant="text"
          @click="updateDialog = false"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useUpdateChecker } from '../composables/useUpdateChecker'

export default {
  name: 'UpdateNotification',
  
  setup() {
    const updateDialog = ref(false)
    
    // Use the update checker composable
    const {
      updateInfo,
      hasUpdate,
      currentVersion,
      latestVersion,
      releaseNotes,
      downloadUrl,
      releaseAssets,
      shouldShowNotification,
      dismissUpdate
    } = useUpdateChecker()
    
    // Local state for notification visibility
    const showNotification = ref(false)
    
    // Watch for update availability
    watch(shouldShowNotification, (newValue) => {
      showNotification.value = newValue
    }, { immediate: true })
    
    // Methods
    const openUpdateDialog = () => {
      updateDialog.value = true
      showNotification.value = false
    }
    
    const dismissNotification = () => {
      dismissUpdate()
      showNotification.value = false
    }
    
    const dismissAndClose = () => {
      dismissUpdate()
      showNotification.value = false
      updateDialog.value = false
    }
    
    const getPlatformIcon = (platform) => {
      switch (platform) {
        case 'windows': return 'mdi-microsoft-windows'
        case 'macos': return 'mdi-apple'
        case 'linux': return 'mdi-linux'
        default: return 'mdi-file-download'
      }
    }
    
    const getPlatformColor = (platform) => {
      switch (platform) {
        case 'windows': return 'blue'
        case 'macos': return 'grey'
        case 'linux': return 'orange'
        default: return 'primary'
      }
    }
    
    const formatFileSize = (bytes) => {
      if (!bytes) return 'Unknown size'
      
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      if (bytes === 0) return '0 Bytes'
      
      const i = Math.floor(Math.log(bytes) / Math.log(1024))
      return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
    }
    
    return {
      // State
      updateDialog,
      showNotification,
      
      // From composable
      updateInfo,
      hasUpdate,
      currentVersion,
      latestVersion,
      releaseNotes,
      downloadUrl,
      releaseAssets,
      shouldShowNotification,
      
      // Methods
      openUpdateDialog,
      dismissNotification,
      dismissAndClose,
      getPlatformIcon,
      getPlatformColor,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.update-notification {
  z-index: 9999;
}

.release-notes {
  max-height: 200px;
  overflow-y: auto;
  background-color: var(--v-theme-surface-variant);
  border-radius: 4px;
  padding: 12px;
}

.release-notes pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: inherit;
}

.download-item:hover {
  background-color: var(--v-theme-surface-variant);
}

:deep(.v-snackbar__wrapper) {
  min-width: 400px;
}

@media (max-width: 600px) {
  :deep(.v-snackbar__wrapper) {
    min-width: 300px;
  }
}
</style>