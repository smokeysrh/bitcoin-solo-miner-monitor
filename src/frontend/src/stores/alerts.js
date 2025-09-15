import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";

// API base URL
const API_BASE_URL = "/api";

export const useAlertsStore = defineStore("alerts", () => {
  // State
  const alerts = ref([]);
  const alertTemplates = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Getters
  const getAlertById = computed(() => (id) => {
    return alerts.value.find((alert) => alert.id === id) || null;
  });

  const activeAlerts = computed(() => {
    return alerts.value.filter((alert) => alert.enabled);
  });

  const inactiveAlerts = computed(() => {
    return alerts.value.filter((alert) => !alert.enabled);
  });

  const alertsByType = computed(() => {
    const result = {
      performance: [],
      connectivity: [],
      temperature: [],
      profitability: [],
      system: [],
    };

    alerts.value.forEach((alert) => {
      if (result[alert.type]) {
        result[alert.type].push(alert);
      }
    });

    return result;
  });

  const alertsBySeverity = computed(() => {
    const result = {
      low: [],
      medium: [],
      high: [],
      critical: [],
    };

    alerts.value.forEach((alert) => {
      if (result[alert.conditions.severity]) {
        result[alert.conditions.severity].push(alert);
      }
    });

    return result;
  });

  // Actions
  const fetchAlerts = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/alerts`);
      alerts.value = response.data;
    } catch (err) {
      error.value = err.message || "Failed to fetch alerts";
      console.error("Error fetching alerts:", err);
    } finally {
      loading.value = false;
    }
  };

  const fetchAlert = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/alerts/${id}`);

      // Update alert in the list
      const index = alerts.value.findIndex((a) => a.id === id);
      if (index !== -1) {
        alerts.value[index] = response.data;
      } else {
        alerts.value.push(response.data);
      }

      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to fetch alert ${id}`;
      console.error(`Error fetching alert ${id}:`, err);
      return null;
    } finally {
      loading.value = false;
    }
  };

  const addAlert = async (alertData) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(`${API_BASE_URL}/alerts`, alertData);
      alerts.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to add alert";
      console.error("Error adding alert:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateAlert = async (id, updates) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.put(`${API_BASE_URL}/alerts/${id}`, updates);

      // Update alert in the list
      const index = alerts.value.findIndex((a) => a.id === id);
      if (index !== -1) {
        alerts.value[index] = response.data;
      }

      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to update alert ${id}`;
      console.error(`Error updating alert ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const removeAlert = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      await axios.delete(`${API_BASE_URL}/alerts/${id}`);

      // Remove alert from the list
      alerts.value = alerts.value.filter((a) => a.id !== id);

      return true;
    } catch (err) {
      error.value = err.message || `Failed to remove alert ${id}`;
      console.error(`Error removing alert ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const toggleAlertStatus = async (id, enabled) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.patch(
        `${API_BASE_URL}/alerts/${id}/status`,
        { enabled },
      );

      // Update alert in the list
      const index = alerts.value.findIndex((a) => a.id === id);
      if (index !== -1) {
        alerts.value[index].enabled = enabled;
      }

      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to update alert status ${id}`;
      console.error(`Error updating alert status ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchAlertTemplates = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/alert-templates`);
      alertTemplates.value = response.data;
    } catch (err) {
      error.value = err.message || "Failed to fetch alert templates";
      console.error("Error fetching alert templates:", err);
    } finally {
      loading.value = false;
    }
  };

  const addAlertTemplate = async (templateData) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(
        `${API_BASE_URL}/alert-templates`,
        templateData,
      );
      alertTemplates.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to add alert template";
      console.error("Error adding alert template:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const removeAlertTemplate = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      await axios.delete(`${API_BASE_URL}/alert-templates/${id}`);

      // Remove template from the list
      alertTemplates.value = alertTemplates.value.filter((t) => t.id !== id);

      return true;
    } catch (err) {
      error.value = err.message || `Failed to remove alert template ${id}`;
      console.error(`Error removing alert template ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    // State
    alerts,
    alertTemplates,
    loading,
    error,

    // Getters
    getAlertById,
    activeAlerts,
    inactiveAlerts,
    alertsByType,
    alertsBySeverity,

    // Actions
    fetchAlerts,
    fetchAlert,
    addAlert,
    updateAlert,
    removeAlert,
    toggleAlertStatus,
    fetchAlertTemplates,
    addAlertTemplate,
    removeAlertTemplate,
  };
});
