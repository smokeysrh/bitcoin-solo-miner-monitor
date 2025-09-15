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
      miners.value = response.data;
    } catch (err) {
      error.value = err.message || "Failed to fetch miners";
      console.error("Error fetching miners:", err);
    } finally {
      loading.value = false;
    }
  };

  const fetchMiner = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.get(`${API_BASE_URL}/miners/${id}`);

      // Update miner in the list
      const index = miners.value.findIndex((m) => m.id === id);
      if (index !== -1) {
        miners.value[index] = response.data;
      } else {
        miners.value.push(response.data);
      }

      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to fetch miner ${id}`;
      console.error(`Error fetching miner ${id}:`, err);
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

  const connectWebSocket = () => {
    // Only initialize if not already connected or connecting
    if (
      connectionStatus.value === "disconnected" ||
      connectionStatus.value === "error"
    ) {
      console.log("Miners store: Initializing WebSocket connection");
      initWebSocket();
    } else {
      console.log(
        "Miners store: WebSocket already connected/connecting, status:",
        connectionStatus.value,
      );
    }

    // Subscribe to miners topic when connection is ready
    const subscribeWhenReady = () => {
      if (connectionStatus.value === "connected") {
        console.log(
          "Miners store: WebSocket connected, subscribing to miners topic",
        );
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
      miners.value = data;
    }
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
    fetchMinerMetrics,
    fetchLatestMetrics,
    startDiscovery,
    getDiscoveryStatus,
    connectWebSocket,
    updateMiners,
  };
});
