import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  settingsService,
  SettingsErrorTypes,
} from "../services/settingsService";

export const useSettingsStore = defineStore("settings", () => {
  // State
  const settings = ref({
    polling_interval: 30,
    theme: "dark",
    chart_retention_days: 30,
    refresh_interval: 10,
    temperature_unit: "celsius",
    default_view: "dashboard",
    simple_mode: false,
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
      console.log("Settings store: Fetching settings using enhanced service");

      // Try to load from localStorage first for faster initial load
      const cachedSettings = loadSettingsFromLocalStorage();
      if (cachedSettings) {
        settings.value = { ...settings.value, ...cachedSettings };
        applyTheme(settings.value.theme);
        console.log("Settings store: Using cached settings from localStorage");
      }

      const result = await settingsService.loadSettings();

      if (result.success) {
        settings.value = { ...settings.value, ...result.data };
        console.log(
          "Settings store: Settings loaded successfully:",
          settings.value,
        );

        // Persist to localStorage for future use
        persistSettingsToLocalStorage(result.data);

        // Apply theme
        applyTheme(settings.value.theme);

        return result.data;
      } else {
        error.value = result.error;
        console.error("Settings store: Failed to load settings:", result.error);
        throw result.error;
      }
    } catch (err) {
      const errorMessage =
        err.userMessage || err.message || "Failed to fetch settings";
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

      // Store old value for change detection
      const oldValue = settings.value[key];

      const result = await settingsService.updateSetting(key, value);

      if (result.success) {
        settings.value = { ...settings.value, ...result.data };

        // Emit change event if value actually changed
        if (oldValue !== result.data[key]) {
          emitSettingsChange(key, oldValue, result.data[key]);
        }

        // Persist updated settings to localStorage
        persistSettingsToLocalStorage(result.data);

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
      throw new Error("No retryable operation available");
    }

    console.log("Settings store: Retrying last operation");
    // Re-attempt the last settings update
    return await updateSettings(settings.value, true);
  };

  const clearError = () => {
    error.value = null;
    validationErrors.value = [];
  };

  const resetToDefaults = async () => {
    try {
      console.log("Settings store: Resetting to defaults");
      const result = await settingsService.resetToDefaults();

      if (result.success) {
        settings.value = { ...result.data };

        // Persist reset settings to localStorage
        persistSettingsToLocalStorage(result.data);

        applyTheme(settings.value.theme);
        console.log("Settings store: Reset to defaults successful");
        return result.data;
      } else {
        error.value = result.error;
        throw new Error(result.message || "Failed to reset settings");
      }
    } catch (err) {
      console.error("Settings store: Error resetting to defaults:", err);
      throw err;
    }
  };

  const exportSettings = async () => {
    try {
      const result = await settingsService.exportSettings();
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.message || "Failed to export settings");
      }
    } catch (err) {
      console.error("Settings store: Error exporting settings:", err);
      throw err;
    }
  };

  const importSettings = async (importData) => {
    try {
      const result = await settingsService.importSettings(importData);
      if (result.success) {
        settings.value = { ...result.data };

        // Persist imported settings to localStorage
        persistSettingsToLocalStorage(result.data);

        applyTheme(settings.value.theme);
        return result.data;
      } else {
        error.value = result.error;
        throw new Error(result.message || "Failed to import settings");
      }
    } catch (err) {
      console.error("Settings store: Error importing settings:", err);
      throw err;
    }
  };

  const emitSettingsChange = (key, oldValue, newValue) => {
    // Emit custom event for settings changes
    const event = new CustomEvent("settings-changed", {
      detail: { key, oldValue, newValue },
    });
    window.dispatchEvent(event);

    // Log at info level (not debug)
    console.info(
      `Settings store: Setting changed - ${key}: ${oldValue} → ${newValue}`,
    );
  };

  const getCurrentInterval = (key = "refresh_interval", defaultValue = 10) => {
    // Get current interval with fallback to defaults
    const value = settings.value[key];
    if (value !== undefined && value !== null) {
      return value;
    }
    return defaultValue;
  };

  const updateSettings = async (newSettings, useRetry = true) => {
    loading.value = true;
    error.value = null;
    validationErrors.value = [];
    lastSaveResult.value = null;

    try {
      console.log("Settings store: 🔄 Starting settings update process...");
      console.log("Settings store: 📝 New settings to save:", newSettings);
      console.log(
        "Settings store: 🔧 Current settings before update:",
        settings.value,
      );

      // Store old values for change detection
      const oldSettings = { ...settings.value };

      // Use retry logic by default for better reliability
      const result = useRetry
        ? await settingsService.saveSettingsWithRetry(newSettings, 3, 1000)
        : await settingsService.saveSettings(newSettings);

      if (result.success) {
        console.log("Settings store: 🎉 Backend save successful!");
        console.log(
          "Settings store: 📦 Response data from backend:",
          result.data,
        );

        // Update local settings with response data
        settings.value = { ...settings.value, ...result.data };
        lastSaveResult.value = result;
        console.log(
          "Settings store: 🔄 Local settings updated:",
          settings.value,
        );

        // Emit change events for modified settings
        Object.keys(result.data).forEach((key) => {
          if (oldSettings[key] !== result.data[key]) {
            emitSettingsChange(key, oldSettings[key], result.data[key]);
          }
        });

        // Persist updated settings to localStorage
        console.log("Settings store: 💾 Persisting to localStorage...");
        persistSettingsToLocalStorage(result.data);

        // Apply theme immediately if it changed
        if (newSettings.theme && newSettings.theme !== settings.value.theme) {
          console.log(
            "Settings store: 🎨 Applying new theme:",
            newSettings.theme,
          );
          applyTheme(newSettings.theme);
        } else if (settings.value.theme) {
          console.log(
            "Settings store: 🎨 Applying current theme:",
            settings.value.theme,
          );
          applyTheme(settings.value.theme);
        }

        console.log(
          "Settings store: ✅ Settings update process completed successfully",
        );
        return result.data;
      } else {
        error.value = result.error;
        validationErrors.value = result.validationErrors || [];
        lastSaveResult.value = result;

        console.error(
          "Settings store: Failed to update settings:",
          result.error,
        );

        // Create user-friendly error message
        let errorMessage = result.message || "Failed to update settings";

        if (
          result.errorType === SettingsErrorTypes.VALIDATION_ERROR &&
          result.validationErrors?.length > 0
        ) {
          errorMessage =
            "Settings validation failed: " +
            result.validationErrors.map((e) => e.message).join(", ");
        }

        throw new Error(errorMessage);
      }
    } catch (err) {
      const errorMessage =
        err.userMessage || err.message || "Failed to update settings";
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
    localStorage.setItem("theme", theme);

    // Update Vuetify theme if available
    if (window.$vuetify) {
      window.$vuetify.theme.global.name.value = theme;
    }

    // Force a small delay to ensure theme transition is smooth
    setTimeout(() => {
      document.body.style.transition =
        "background-color 0.3s ease, color 0.3s ease";
    }, 50);
  };

  const persistSettingsToLocalStorage = (settingsData) => {
    try {
      // Store all settings in localStorage for offline access and faster loading
      const settingsJson = JSON.stringify(settingsData);
      localStorage.setItem("appSettings", settingsJson);

      // Verify the save was successful
      const verification = localStorage.getItem("appSettings");
      if (verification === settingsJson) {
        console.log(
          "Settings store: ✓ Settings successfully persisted to localStorage:",
          settingsData,
        );
        console.log("Settings store: ✓ localStorage verification passed");
      } else {
        console.error("Settings store: ✗ localStorage verification failed!");
        console.error("Settings store: Expected:", settingsJson);
        console.error("Settings store: Got:", verification);
      }
    } catch (error) {
      console.error(
        "Settings store: ✗ Failed to persist settings to localStorage:",
        error,
      );
      console.error("Settings store: Error details:", {
        name: error.name,
        message: error.message,
        stack: error.stack,
      });
    }
  };

  const loadSettingsFromLocalStorage = () => {
    try {
      const stored = localStorage.getItem("appSettings");
      if (stored) {
        const parsedSettings = JSON.parse(stored);
        console.log(
          "Settings store: Loaded settings from localStorage:",
          parsedSettings,
        );
        return parsedSettings;
      }
    } catch (error) {
      console.warn(
        "Settings store: Failed to load settings from localStorage:",
        error,
      );
    }
    return null;
  };

  const clearSettingsFromLocalStorage = () => {
    try {
      localStorage.removeItem("appSettings");
      console.log("Settings store: Cleared settings from localStorage");
    } catch (error) {
      console.warn(
        "Settings store: Failed to clear settings from localStorage:",
        error,
      );
    }
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

    // localStorage utilities
    persistSettingsToLocalStorage,
    loadSettingsFromLocalStorage,
    clearSettingsFromLocalStorage,

    // Change event utilities
    emitSettingsChange,
    getCurrentInterval,
  };
});
