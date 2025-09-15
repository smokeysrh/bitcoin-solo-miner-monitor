import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "axios";

// API base URL
const API_BASE_URL = "/api";

export const useSettingsStore = defineStore("settings", () => {
  // State
  const settings = ref({
    polling_interval: 30,
    theme: "dark",
    chart_retention_days: 30,
    refresh_interval: 10,
  });
  const loading = ref(false);
  const error = ref(null);

  // Actions
  const fetchSettings = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/settings`);
      settings.value = response.data;

      // Apply theme
      applyTheme(settings.value.theme);

      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to fetch settings";
      console.error("Error fetching settings:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateSettings = async (newSettings) => {
    loading.value = true;
    error.value = null;

    try {
      console.log('Settings store: Updating settings with:', newSettings);
      const response = await axios.put(`${API_BASE_URL}/settings`, newSettings);
      
      // Update local settings with response data
      settings.value = { ...settings.value, ...response.data };
      console.log('Settings store: Settings updated successfully:', settings.value);

      // Apply theme immediately if it changed
      if (newSettings.theme && newSettings.theme !== settings.value.theme) {
        applyTheme(newSettings.theme);
      } else if (settings.value.theme) {
        applyTheme(settings.value.theme);
      }

      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || "Failed to update settings";
      error.value = errorMessage;
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

    // Actions
    fetchSettings,
    updateSettings,
  };
});
