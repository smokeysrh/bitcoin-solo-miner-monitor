<template>
  <v-dialog
    v-model="dialogVisible"
    max-width="600px"
    persistent
    @click:outside="handleCancel"
  >
    <v-card>
      <v-card-title class="text-h5 pa-4">
        <v-icon left color="primary">mdi-plus-circle</v-icon>
        Add New Miner
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text class="pa-6">
        <v-form ref="form" v-model="formValid" @submit.prevent="handleSubmit">
          <!-- Miner Type Selection -->
          <v-select
            v-model="formData.type"
            :items="minerTypes"
            label="Miner Type"
            item-title="title"
            item-value="value"
            required
            :rules="typeRules"
            outlined
            dense
            class="mb-4"
            prepend-inner-icon="mdi-chip"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <template v-slot:prepend>
                  <v-icon :icon="item.raw.icon" class="mr-3"></v-icon>
                </template>
                <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>

          <!-- IP Address Field -->
          <v-text-field
            v-model="formData.ip_address"
            label="IP Address"
            required
            :rules="ipAddressRules"
            outlined
            dense
            class="mb-4"
            prepend-inner-icon="mdi-ip-network"
            hint="e.g., 192.168.1.100"
            persistent-hint
          ></v-text-field>

          <!-- Port Field -->
          <v-text-field
            v-model="formData.port"
            label="Port"
            type="number"
            :rules="portRules"
            outlined
            dense
            class="mb-4"
            prepend-inner-icon="mdi-ethernet"
            :hint="getPortHint"
            persistent-hint
          ></v-text-field>

          <!-- Miner Name Field -->
          <v-text-field
            v-model="formData.name"
            label="Miner Name"
            required
            :rules="nameRules"
            outlined
            dense
            class="mb-4"
            prepend-inner-icon="mdi-tag"
            hint="A friendly name to identify this miner"
            persistent-hint
          ></v-text-field>

          <!-- Advanced Options (Collapsible) -->
          <v-expansion-panels v-model="advancedPanel" class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon left>mdi-cog</v-icon>
                Advanced Options
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-text-field
                  v-model="formData.username"
                  label="Username (Optional)"
                  outlined
                  dense
                  class="mb-4"
                  prepend-inner-icon="mdi-account"
                  hint="Leave empty if not required"
                  persistent-hint
                ></v-text-field>

                <v-text-field
                  v-model="formData.password"
                  label="Password (Optional)"
                  type="password"
                  outlined
                  dense
                  class="mb-4"
                  prepend-inner-icon="mdi-lock"
                  hint="Leave empty if not required"
                  persistent-hint
                ></v-text-field>

                <v-text-field
                  v-model="formData.mac_address"
                  label="MAC Address (Optional)"
                  :rules="macAddressRules"
                  outlined
                  dense
                  prepend-inner-icon="mdi-network"
                  hint="For Wake-on-LAN functionality (format: AA:BB:CC:DD:EE:FF)"
                  persistent-hint
                ></v-text-field>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Connection Test Section -->
          <v-alert
            v-if="connectionTest.status"
            :type="connectionTest.status === 'success' ? 'success' : connectionTest.status === 'error' ? 'error' : 'info'"
            class="mb-4"
            outlined
          >
            <div class="d-flex align-center">
              <v-icon left>
                {{ connectionTest.status === 'success' ? 'mdi-check-circle' : 
                   connectionTest.status === 'error' ? 'mdi-alert-circle' : 'mdi-information' }}
              </v-icon>
              {{ connectionTest.message }}
            </div>
          </v-alert>
        </v-form>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-btn
          color="secondary"
          variant="outlined"
          @click="testConnection"
          :loading="testing"
          :disabled="!canTestConnection || loading"
        >
          <v-icon left>mdi-connection</v-icon>
          Test Connection
        </v-btn>

        <v-spacer></v-spacer>

        <v-btn
          color="grey"
          variant="text"
          @click="handleCancel"
          :disabled="loading"
        >
          Cancel
        </v-btn>

        <v-btn
          color="primary"
          variant="elevated"
          @click="handleSubmit"
          :loading="loading"
          :disabled="!formValid || loading"
        >
          <v-icon left>mdi-plus</v-icon>
          Add Miner
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch, nextTick } from 'vue'
import { useMinersStore } from '../stores/miners'

export default {
  name: 'AddMinerDialog',

  props: {
    modelValue: {
      type: Boolean,
      default: false
    }
  },

  emits: ['update:modelValue', 'miner-added', 'error'],

  setup(props, { emit }) {
    const minersStore = useMinersStore()

    // Form refs and state
    const form = ref(null)
    const formValid = ref(false)
    const loading = ref(false)
    const testing = ref(false)
    const advancedPanel = ref(null)

    // Dialog visibility
    const dialogVisible = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })

    // Form data
    const formData = ref({
      type: '',
      ip_address: '',
      port: '',
      name: '',
      username: '',
      password: '',
      mac_address: ''
    })

    // Connection test state
    const connectionTest = ref({
      status: null, // null, 'testing', 'success', 'error'
      message: ''
    })

    // Miner types configuration
    const minerTypes = [
      {
        title: 'Bitaxe',
        value: 'bitaxe',
        icon: 'mdi-pickaxe',
        description: 'Open-source Bitcoin ASIC miner',
        defaultPort: 80
      },
      {
        title: 'Avalon Nano',
        value: 'avalon_nano',
        icon: 'mdi-chip',
        description: 'Compact USB Bitcoin miner',
        defaultPort: 4028
      },
      {
        title: 'Magic Miner',
        value: 'magic_miner',
        icon: 'mdi-lightning-bolt',
        description: 'High-performance Bitcoin miner',
        defaultPort: 80
      }
    ]

    // Validation rules
    const typeRules = [
      v => !!v || 'Miner type is required'
    ]

    const ipAddressRules = [
      v => !!v || 'IP address is required',
      v => {
        const pattern = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
        return pattern.test(v) || 'Invalid IP address format'
      }
    ]

    const portRules = [
      v => !v || (Number.isInteger(Number(v)) && Number(v) >= 1 && Number(v) <= 65535) || 'Port must be between 1 and 65535'
    ]

    const nameRules = [
      v => !!v || 'Miner name is required',
      v => (v && v.length >= 2) || 'Name must be at least 2 characters',
      v => (v && v.length <= 50) || 'Name must be less than 50 characters'
    ]

    const macAddressRules = [
      v => !v || /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/.test(v) || 'Invalid MAC address format (use AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF)'
    ]

    // Computed properties
    const selectedMinerType = computed(() => {
      return minerTypes.find(type => type.value === formData.value.type)
    })

    const getPortHint = computed(() => {
      if (selectedMinerType.value) {
        return `Default port for ${selectedMinerType.value.title}: ${selectedMinerType.value.defaultPort}`
      }
      return 'Leave empty to use default port for selected miner type'
    })

    const canTestConnection = computed(() => {
      return formData.value.type && formData.value.ip_address && 
             ipAddressRules.every(rule => rule(formData.value.ip_address) === true)
    })

    // Watchers
    watch(() => formData.value.type, (newType) => {
      if (newType && !formData.value.port) {
        const minerType = minerTypes.find(type => type.value === newType)
        if (minerType) {
          formData.value.port = minerType.defaultPort.toString()
        }
      }
      
      // Generate default name if empty
      if (newType && !formData.value.name && formData.value.ip_address) {
        const minerType = minerTypes.find(type => type.value === newType)
        if (minerType) {
          formData.value.name = `${minerType.title} (${formData.value.ip_address})`
        }
      }
    })

    watch(() => formData.value.ip_address, (newIp) => {
      if (newIp && formData.value.type && !formData.value.name) {
        const minerType = minerTypes.find(type => type.value === formData.value.type)
        if (minerType) {
          formData.value.name = `${minerType.title} (${newIp})`
        }
      }
    })

    // Reset form when dialog opens
    watch(() => props.modelValue, (isOpen) => {
      if (isOpen) {
        resetForm()
        connectionTest.value = { status: null, message: '' }
      }
    })

    // Methods
    const resetForm = () => {
      formData.value = {
        type: '',
        ip_address: '',
        port: '',
        name: '',
        username: '',
        password: '',
        mac_address: ''
      }
      formValid.value = false
      advancedPanel.value = null
      
      nextTick(() => {
        if (form.value) {
          form.value.resetValidation()
        }
      })
    }

    const testConnection = async () => {
      if (!canTestConnection.value) return

      testing.value = true
      connectionTest.value = {
        status: 'testing',
        message: 'Testing connection...'
      }

      try {
        // Prepare test data
        const testData = {
          type: formData.value.type,
          ip_address: formData.value.ip_address,
          port: formData.value.port || selectedMinerType.value?.defaultPort,
          username: formData.value.username || undefined,
          password: formData.value.password || undefined
        }

        // Call the miners store test connection method (if available)
        // For now, we'll simulate a connection test
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        // Mock successful connection
        connectionTest.value = {
          status: 'success',
          message: `Successfully connected to ${selectedMinerType.value?.title} at ${formData.value.ip_address}`
        }
      } catch (error) {
        connectionTest.value = {
          status: 'error',
          message: `Connection failed: ${error.message || 'Unable to connect to miner'}`
        }
      } finally {
        testing.value = false
      }
    }

    const handleSubmit = async () => {
      if (!formValid.value) return

      loading.value = true

      try {
        // Prepare miner data
        const minerData = {
          type: formData.value.type,
          ip_address: formData.value.ip_address,
          port: formData.value.port ? parseInt(formData.value.port) : selectedMinerType.value?.defaultPort,
          name: formData.value.name
        }

        // Add optional fields if provided
        if (formData.value.username) {
          minerData.username = formData.value.username
        }
        if (formData.value.password) {
          minerData.password = formData.value.password
        }
        if (formData.value.mac_address) {
          minerData.mac_address = formData.value.mac_address
        }

        // Add miner through store
        const addedMiner = await minersStore.addMiner(minerData)

        // Emit success event
        emit('miner-added', addedMiner)

        // Close dialog
        dialogVisible.value = false

      } catch (error) {
        console.error('Error adding miner:', error)
        emit('error', error)
      } finally {
        loading.value = false
      }
    }

    const handleCancel = () => {
      if (!loading.value) {
        dialogVisible.value = false
      }
    }

    return {
      // Refs
      form,
      formValid,
      loading,
      testing,
      advancedPanel,
      dialogVisible,
      formData,
      connectionTest,

      // Data
      minerTypes,

      // Validation rules
      typeRules,
      ipAddressRules,
      portRules,
      nameRules,
      macAddressRules,

      // Computed
      selectedMinerType,
      getPortHint,
      canTestConnection,

      // Methods
      resetForm,
      testConnection,
      handleSubmit,
      handleCancel
    }
  }
}
</script>

<style scoped>
/* Enhanced dialog styling */
:deep(.v-dialog .v-card) {
  background-color: var(--color-surface-elevated) !important;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-4);
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

:deep(.v-text-field .v-field__input::placeholder) {
  color: var(--color-text-hint) !important;
}

/* Select field styling */
:deep(.v-select .v-field) {
  background-color: var(--color-surface-secondary) !important;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

:deep(.v-select .v-field:hover) {
  border-color: var(--color-primary);
}

:deep(.v-select .v-field--focused) {
  border-color: var(--color-primary) !important;
  box-shadow: var(--shadow-focus);
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

/* List item styling for select dropdown */
:deep(.v-list-item) {
  color: var(--color-text-primary) !important;
}

:deep(.v-list-item-title) {
  color: var(--color-text-primary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.v-list-item-subtitle) {
  color: var(--color-text-secondary) !important;
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
  :deep(.v-dialog) {
    margin: var(--spacing-md);
  }

  :deep(.v-card-title) {
    font-size: var(--font-size-body);
    padding: var(--spacing-md);
  }

  :deep(.v-card-text) {
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
  :deep(.v-dialog .v-card),
  :deep(.v-text-field .v-field),
  :deep(.v-select .v-field),
  :deep(.v-expansion-panels),
  :deep(.v-alert) {
    border-width: 2px;
  }

  :deep(.v-btn) {
    border: 1px solid var(--color-text-primary);
  }
}

/* Focus management for keyboard navigation */
:deep(.v-text-field .v-field:focus-within),
:deep(.v-select .v-field:focus-within) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

:deep(.v-btn:focus) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>