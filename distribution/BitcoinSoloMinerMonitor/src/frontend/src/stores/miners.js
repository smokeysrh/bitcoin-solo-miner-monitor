import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import {
  initWebSocket,
  connectionStatus,
  updateSubscriptions,
} from "../services/websocket";

// API base URL
const API_BASE_URL = "/api";

// Debug mode flag - only enable verbose logging in development
const DEBUG_MODE =
  import.meta.env.DEV || localStorage.getItem("debug") === "true";

export const useMinersStore = defineStore("miners", () => {
  // State
  const miners = ref([]);
  const loading = ref(false);
  const error = ref(null);
  const websocketStatus = computed(() => connectionStatus.value);

  // Getters
  const getMinerById = computed(() => (id) => {
    return miners.value.find((miner) => miner.id === id) || null;
  });

  const onlineMiners = computed(() => {
    return miners.value.filter((miner) => miner.status === "online");
  });

  const offlineMiners = computed(() => {
    return miners.value.filter(
      (miner) => miner.status === "offline" || miner.status === "error",
    );
  });

  const totalHashrate = computed(() => {
    return onlineMiners.value.reduce((total, miner) => {
      return total + (miner.hashrate || 0);
    }, 0);
  });

  // Actions
  const fetchMiners = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/miners`);

      // Debug: Log raw API response
      console.log("=== RAW API RESPONSE ===");
      console.log("Number of miners:", response.data.length);
      response.data.forEach((miner, index) => {
        console.log(`\nMiner ${index + 1}:`, {
          id: miner.id,
          name: miner.name,
          type: miner.type,
          temperature: miner.temperature,
          hasMetrics: !!miner.metrics,
          metricsTemp: miner.metrics?.temperature || miner.metrics?.temp,
          allKeys: Object.keys(miner),
        });
      });
      console.log("=== END RAW API RESPONSE ===\n");

      // Normalize all miner data to ensure consistent field structure
      miners.value = response.data.map((miner) => normalizeMinerData(miner));

      // Debug: Log normalized data
      console.log("=== NORMALIZED DATA ===");
      miners.value.forEach((miner, index) => {
        console.log(`Normalized Miner ${index + 1}:`, {
          id: miner.id,
          name: miner.name,
          temperature: miner.temperature,
        });
      });
      console.log("=== END NORMALIZED DATA ===\n");
    } catch (err) {
      error.value = err.message || "Failed to fetch miners";
      console.error("Error fetching miners:", err);
    } finally {
      loading.value = false;
    }
  };

  const fetchMiner = async (id) => {
    console.log("=== [STORE] FETCH MINER START ===", {
      timestamp: new Date().toISOString(),
      minerId: id,
      currentStoreData: miners.value.find((m) => m.id === id),
      storeSize: miners.value.length,
    });

    loading.value = true;
    error.value = null;

    try {
      console.log("=== [STORE] FETCH MINER API CALL ===", {
        timestamp: new Date().toISOString(),
        minerId: id,
        url: `${API_BASE_URL}/miners/${id}`,
      });

      const response = await axios.get(`${API_BASE_URL}/miners/${id}`);

      console.log("=== [STORE] FETCH MINER API RESPONSE ===", {
        timestamp: new Date().toISOString(),
        minerId: id,
        responseData: response.data,
        dataAge: response.data.last_updated,
        status: response.status,
      });

      // Normalize miner data
      const normalizedMiner = normalizeMinerData(response.data);

      console.log("=== [STORE] FETCH MINER NORMALIZED ===", {
        timestamp: new Date().toISOString(),
        minerId: id,
        normalizedData: normalizedMiner,
        beforeUpdate: miners.value.find((m) => m.id === id),
      });

      // Update miner in the list
      const index = miners.value.findIndex((m) => m.id === id);
      if (index !== -1) {
        miners.value[index] = normalizedMiner;
        console.log("=== [STORE] FETCH MINER UPDATED ===", {
          timestamp: new Date().toISOString(),
          minerId: id,
          index: index,
          afterUpdate: miners.value[index],
        });
      } else {
        miners.value.push(normalizedMiner);
        console.log("=== [STORE] FETCH MINER ADDED ===", {
          timestamp: new Date().toISOString(),
          minerId: id,
          newIndex: miners.value.length - 1,
        });
      }

      return normalizedMiner;
    } catch (err) {
      error.value = err.message || `Failed to fetch miner ${id}`;
      console.error("=== [STORE] FETCH MINER ERROR ===", {
        timestamp: new Date().toISOString(),
        minerId: id,
        error: err.message,
        errorDetails: err,
      });
      return null;
    } finally {
      loading.value = false;
    }
  };

  const addMiner = async (minerData) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(`${API_BASE_URL}/miners`, minerData);
      miners.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to add miner";
      console.error("Error adding miner:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateMiner = async (id, updates) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.put(`${API_BASE_URL}/miners/${id}`, updates);

      // Update miner in the list
      const index = miners.value.findIndex((m) => m.id === id);
      if (index !== -1) {
        miners.value[index] = response.data;
      }

      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to update miner ${id}`;
      console.error(`Error updating miner ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const removeMiner = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      await axios.delete(`${API_BASE_URL}/miners/${id}`);

      // Remove miner from the list
      miners.value = miners.value.filter((m) => m.id !== id);

      return true;
    } catch (err) {
      error.value = err.message || `Failed to remove miner ${id}`;
      console.error(`Error removing miner ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const restartMiner = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(`${API_BASE_URL}/miners/${id}/restart`);

      // Update miner status
      const index = miners.value.findIndex((m) => m.id === id);
      if (index !== -1) {
        miners.value[index].status = "restarting";
      }

      return response.data.success;
    } catch (err) {
      error.value = err.message || `Failed to restart miner ${id}`;
      console.error(`Error restarting miner ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const restartAllMiners = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(`${API_BASE_URL}/miners/restart-all`);

      // Update all miner statuses to restarting
      miners.value.forEach((miner) => {
        if (miner.status === "online") {
          miner.status = "restarting";
        }
      });

      return response.data.success;
    } catch (err) {
      error.value = err.message || "Failed to restart all miners";
      console.error("Error restarting all miners:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const refreshMiners = async () => {
    loading.value = true;
    error.value = null;

    try {
      console.log("Calling refresh miners endpoint...");
      const response = await axios.post(`${API_BASE_URL}/miners/refresh`);

      console.log("Refresh response:", response.data);

      // Update miners with refreshed data
      if (response.data.miners && Array.isArray(response.data.miners)) {
        miners.value = response.data.miners.map((miner) =>
          normalizeMinerData(miner),
        );
        console.log(`Successfully refreshed ${miners.value.length} miners`);
      }

      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to refresh miners";
      console.error("Error refreshing miners:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchMinerMetrics = async (id, start, end, interval = "1m") => {
    loading.value = true;
    error.value = null;

    try {
      const params = { interval };
      if (start) params.start = start;
      if (end) params.end = end;

      const response = await axios.get(`${API_BASE_URL}/miners/${id}/metrics`, {
        params,
      });
      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to fetch metrics for miner ${id}`;
      console.error(`Error fetching metrics for miner ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchLatestMetrics = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(
        `${API_BASE_URL}/miners/${id}/metrics/latest`,
      );
      return response.data;
    } catch (err) {
      error.value =
        err.message || `Failed to fetch latest metrics for miner ${id}`;
      console.error(`Error fetching latest metrics for miner ${id}:`, err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const startDiscovery = async (network, ports) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(`${API_BASE_URL}/discovery`, {
        network,
        ports,
      });
      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to start discovery";
      console.error("Error starting discovery:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const getDiscoveryStatus = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/discovery/status`);
      return response.data;
    } catch (err) {
      error.value = err.message || "Failed to get discovery status";
      console.error("Error getting discovery status:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchNetworkHealth = async (id) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/miners/${id}/network-health`,
      );
      return response.data;
    } catch (err) {
      console.error(`Error fetching network health for miner ${id}:`, err);
      return null;
    }
  };

  const fetchAllNetworkHealth = async () => {
    try {
      const healthPromises = miners.value.map((miner) =>
        fetchNetworkHealth(miner.id),
      );
      const healthResults = await Promise.all(healthPromises);

      // Create a map of miner_id to health data
      const healthMap = {};
      healthResults.forEach((health, index) => {
        if (health) {
          healthMap[miners.value[index].id] = health;
        }
      });

      return healthMap;
    } catch (err) {
      console.error("Error fetching all network health:", err);
      return {};
    }
  };

  const connectWebSocket = () => {
    // Only initialize if not already connected or connecting
    if (
      connectionStatus.value === "disconnected" ||
      connectionStatus.value === "error"
    ) {
      if (DEBUG_MODE) {
        console.log("Miners store: Initializing WebSocket connection");
      }
      initWebSocket();
    } else {
      if (DEBUG_MODE) {
        console.log(
          "Miners store: WebSocket already connected/connecting, status:",
          connectionStatus.value,
        );
      }
    }

    // Subscribe to miners topic when connection is ready
    const subscribeWhenReady = () => {
      if (connectionStatus.value === "connected") {
        if (DEBUG_MODE) {
          console.log(
            "Miners store: WebSocket connected, subscribing to miners topic",
          );
        }
        updateSubscriptions({
          miners: true,
          alerts: false,
          system: false,
        });
      } else {
        // Wait a bit and try again
        setTimeout(subscribeWhenReady, 100);
      }
    };

    subscribeWhenReady();
  };

  // Method to update miners from WebSocket
  const updateMiners = (data) => {
    if (Array.isArray(data)) {
      // Normalize all miner data from WebSocket updates
      miners.value = data.map((miner) => normalizeMinerData(miner));
    }
  };

  // Temperature extraction function - normalizes temperature field from various sources
  const extractTemperature = (minerData) => {
    if (!minerData) return 0;

    // Try multiple possible temperature field locations
    // 1. Direct temperature field
    if (minerData.temperature !== undefined && minerData.temperature !== null) {
      const temp =
        typeof minerData.temperature === "number"
          ? minerData.temperature
          : parseFloat(minerData.temperature);
      if (!isNaN(temp)) return temp;
    }

    // 2. In metrics object
    if (minerData.metrics) {
      if (
        minerData.metrics.temperature !== undefined &&
        minerData.metrics.temperature !== null
      ) {
        const temp =
          typeof minerData.metrics.temperature === "number"
            ? minerData.metrics.temperature
            : parseFloat(minerData.metrics.temperature);
        if (!isNaN(temp)) return temp;
      }

      // Try 'temp' as alternative field name
      if (
        minerData.metrics.temp !== undefined &&
        minerData.metrics.temp !== null
      ) {
        const temp =
          typeof minerData.metrics.temp === "number"
            ? minerData.metrics.temp
            : parseFloat(minerData.metrics.temp);
        if (!isNaN(temp)) return temp;
      }
    }

    // 3. In device_info object
    if (minerData.device_info) {
      if (
        minerData.device_info.temperature !== undefined &&
        minerData.device_info.temperature !== null
      ) {
        const temp =
          typeof minerData.device_info.temperature === "number"
            ? minerData.device_info.temperature
            : parseFloat(minerData.device_info.temperature);
        if (!isNaN(temp)) return temp;
      }

      if (
        minerData.device_info.temp !== undefined &&
        minerData.device_info.temp !== null
      ) {
        const temp =
          typeof minerData.device_info.temp === "number"
            ? minerData.device_info.temp
            : parseFloat(minerData.device_info.temp);
        if (!isNaN(temp)) return temp;
      }
    }

    // Default to 0 if no temperature found
    return 0;
  };

  // Normalize miner data - ensures all miners have consistent field structure
  const normalizeMinerData = (minerData) => {
    if (!minerData) return minerData;

    // Debug logging to see what data we're receiving
    if (DEBUG_MODE) {
      console.log("Normalizing miner data:", {
        id: minerData.id,
        name: minerData.name,
        rawData: minerData,
        hasMetrics: !!minerData.metrics,
        metricsKeys: minerData.metrics ? Object.keys(minerData.metrics) : [],
        hasDeviceInfo: !!minerData.device_info,
        deviceInfoKeys: minerData.device_info
          ? Object.keys(minerData.device_info)
          : [],
      });
    }

    const extractedTemp = extractTemperature(minerData);

    if (DEBUG_MODE) {
      console.log(
        `Extracted temperature for ${minerData.name}: ${extractedTemp}`,
      );
    }

    return {
      ...minerData,
      // Extract and normalize temperature to top level
      temperature: extractedTemp,
      // Ensure other common fields are accessible
      hashrate: minerData.hashrate || minerData.metrics?.hashrate || 0,
      power: minerData.power || minerData.metrics?.power || 0,
      fan_speed: minerData.fan_speed || minerData.metrics?.fan_speed || 0,
    };
  };

  return {
    // State
    miners,
    loading,
    error,
    websocketStatus,

    // Getters
    getMinerById,
    onlineMiners,
    offlineMiners,
    totalHashrate,

    // Actions
    fetchMiners,
    fetchMiner,
    addMiner,
    updateMiner,
    removeMiner,
    restartMiner,
    restartAllMiners,
    refreshMiners,
    fetchMinerMetrics,
    fetchLatestMetrics,
    startDiscovery,
    getDiscoveryStatus,
    fetchNetworkHealth,
    fetchAllNetworkHealth,
    connectWebSocket,
    updateMiners,

    // Utility functions
    extractTemperature,
    normalizeMinerData,
  };
});
