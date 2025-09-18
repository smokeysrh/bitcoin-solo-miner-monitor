import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { settingsService, SettingsErrorTypes } from "../services/settingsService";

export const useSettingsStore = defineStore("settings", () => {
  // State
  const settings = ref({
    polling_interval: 30,
    theme: "dark",
    chart_retention_days: 30,
    refresh_interval: 10,
    temperature_unit: "celsius",
    default_view: "dashboard",
    simple_mode: false
  });
  const loading = ref(false);
  const error = ref(null);
  const lastSaveResult = ref(null);
  const validationErrors = ref([]);

  // Computed properties for enhanced error handling
  const isLoading = computed(() => {
    return loading.value || settingsService.isAnyOperationLoading();
  });

  const hasError = computed(() => {
    return error.value !== null;
  });

  const errorType = computed(() => {
    return error.value?.type || null;
  });

  const canRetry = computed(() => {
    return error.value?.retryable === true;
  });

  const loadingStates = computed(() => {
    return settingsService.getAllLoadingStates();
  });

  // Actions
  const fetchSettings = async () => {
    loading.value = true;
    error.value = null;
    validationErrors.value = [];

    try {
      console.log('Settings store: Fetching settings using enhanced service');
      const result = await settingsService.loadSettings();
      
      if (result.success) {
        settings.value = { ...settings.value, ...result.data };
        console.log('Settings store: Settings loaded successfully:', settings.value);
        
        // Apply theme
        applyTheme(settings.value.theme);
        
        return result.data;
      } else {
        error.value = result.error;
        console.error('Settings store: Failed to load settings:', result.error);
        throw result.error;
      }
    } catch (err) {
      const errorMessage = err.userMessage || err.message || "Failed to fetch settings";
      error.value = err;
      console.error("Settings store: Error fetching settings:", err);
      throw new Error(errorMessage);
    } finally {
      loading.value = false;
    }
  };

  // Additional helper methods for enhanced functionality
  const updateSingleSetting = async (key, value) => {
    try {
      console.log(`Settings store: Updating single setting ${key}:`, value);
      const result = await settingsService.updateSetting(key, value);
      
      if (result.success) {
        settings.value = { ...settings.value, ...result.data };
        console.log(`Settings store: Successfully updated ${key}`);
        return result.data;
      } else {
        error.value = result.error;
        validationErrors.value = result.validationErrors || [];
        throw new Error(result.message || `Failed to update ${key}`);
      }
    } catch (err) {
      console.error(`Settings store: Error updating ${key}:`, err);
      throw err;
    }
  };

  const retryLastOperation = async () => {
    if (!lastSaveResult.value || !canRetry.value) {
      throw new Error('No retryable operation available');
    }
    
    console.log('Settings store: Retrying last operation');
    // Re-attempt the last settings update
    return await updateSettings(settings.value, true);
  };

  const clearError = () => {
    error.value = null;
    validationErrors.value = [];
  };

  const resetToDefaults = async () => {
    try {
      console.log('Settings store: Resetting to defaults');
      const result = await settingsService.resetToDefaults();
      
      if (result.success) {
        settings.value = { ...result.data };
        applyTheme(settings.value.theme);
        console.log('Settings store: Reset to defaults successful');
        return result.data;
      } else {
        error.value = result.error;
        throw new Error(result.message || 'Failed to reset settings');
      }
    } catch (err) {
      console.error('Settings store: Error resetting to defaults:', err);
      throw err;
    }
  };

  const exportSettings = async () => {
    try {
      const result = await settingsService.exportSettings();
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.message || 'Failed to export settings');
      }
    } catch (err) {
      console.error('Settings store: Error exporting settings:', err);
      throw err;
    }
  };

  const importSettings = async (importData) => {
    try {
      const result = await settingsService.importSettings(importData);
      if (result.success) {
        settings.value = { ...result.data };
        applyTheme(settings.value.theme);
        return result.data;
      } else {
        error.value = result.error;
        throw new Error(result.message || 'Failed to import settings');
      }
    } catch (err) {
      console.error('Settings store: Error importing settings:', err);
      throw err;
    }
  };

  const updateSettings = async (newSettings, useRetry = true) => {
    loading.value = true;
    error.value = null;
    validationErrors.value = [];
    lastSaveResult.value = null;

    try {
      console.log('Settings store: Updating settings with enhanced service:', newSettings);
      
      // Use retry logic by default for better reliability
      const result = useRetry 
        ? await settingsService.saveSettingsWithRetry(newSettings, 3, 1000)
        : await settingsService.saveSettings(newSettings);
      
      if (result.success) {
        // Update local settings with response data
        settings.value = { ...settings.value, ...result.data };
        lastSaveResult.value = result;
        console.log('Settings store: Settings updated successfully:', settings.value);

        // Apply theme immediately if it changed
        if (newSettings.theme && newSettings.theme !== settings.value.theme) {
          applyTheme(newSettings.theme);
        } else if (settings.value.theme) {
          applyTheme(settings.value.theme);
        }

        return result.data;
      } else {
        error.value = result.error;
        validationErrors.value = result.validationErrors || [];
        lastSaveResult.value = result;
        
        console.error('Settings store: Failed to update settings:', result.error);
        
        // Create user-friendly error message
        let errorMessage = result.message || 'Failed to update settings';
        
        if (result.errorType === SettingsErrorTypes.VALIDATION_ERROR && result.validationErrors?.length > 0) {
          errorMessage = 'Settings validation failed: ' + result.validationErrors.map(e => e.message).join(', ');
        }
        
        throw new Error(errorMessage);
      }
    } catch (err) {
      const errorMessage = err.userMessage || err.message || "Failed to update settings";
      error.value = err;
      console.error("Settings store: Error updating settings:", err);
      throw new Error(errorMessage);
    } finally {
      loading.value = false;
    }
  };

  const applyTheme = (theme) => {
    // Apply theme to document
    document.documentElement.setAttribute("data-theme", theme);
    
    // Persist theme choice in localStorage
    localStorage.setItem('theme', theme);

    // Update Vuetify theme if available
    if (window.$vuetify) {
      window.$vuetify.theme.global.name.value = theme;
    }
    
    // Force a small delay to ensure theme transition is smooth
    setTimeout(() => {
      document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    }, 50);
  };

  return {
    // State
    settings,
    loading,
    error,
    lastSaveResult,
    validationErrors,

    // Computed properties
    isLoading,
    hasError,
    errorType,
    canRetry,
    loadingStates,

    // Actions
    fetchSettings,
    updateSettings,
    updateSingleSetting,
    retryLastOperation,
    clearError,
    resetToDefaults,
    exportSettings,
    importSettings,
  };
});
