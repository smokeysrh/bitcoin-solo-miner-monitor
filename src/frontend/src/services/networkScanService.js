/**
 * Universal Network Scanner Service
 *
 * This service provides a standardized interface for network scanning
 * across the entire application, ensuring consistent behavior and
 * user experience regardless of where the scan is initiated.
 *
 * Uses the global WebSocket service for real-time updates.
 */

import { DEFAULT_SCAN_PORTS } from "../config/ports.config";
import {
  updateSubscriptions,
  addMessageHandler,
  removeMessageHandler,
} from "./websocket";

export class NetworkScanService {
  constructor() {
    this.isScanning = false;
    this.scanStatus = null;
    this.foundMiners = [];
    this.listeners = new Set();
    this.messageHandler = null;
  }

  /**
   * Add a listener for scan updates
   * @param {Function} listener - Callback function to receive updates
   */
  addListener(listener) {
    this.listeners.add(listener);
  }

  /**
   * Remove a listener
   * @param {Function} listener - Callback function to remove
   */
  removeListener(listener) {
    this.listeners.delete(listener);
  }

  /**
   * Notify all listeners of updates
   * @param {Object} data - Update data to send to listeners
   */
  notifyListeners(data) {
    this.listeners.forEach((listener) => {
      try {
        listener(data);
      } catch (error) {
        console.error("Error in scan listener:", error);
      }
    });
  }

  /**
   * Start a network scan
   * @param {Object} options - Scan configuration
   * @param {string} options.network - Network range (CIDR or IP range)
   * @param {Array} options.ports - Ports to scan (optional)
   * @param {number} options.timeout - Connection timeout (optional)
   * @returns {Promise<boolean>} - Success status
   */
  async startScan(options = {}) {
    if (this.isScanning) {
      console.warn("Scan already in progress");
      return false;
    }

    try {
      // Validate and prepare scan options
      const scanConfig = this.prepareScanConfig(options);

      console.log("Starting network scan with config:", scanConfig);

      // Reset state
      this.isScanning = true;
      this.scanStatus = null;
      this.foundMiners = [];

      // Subscribe to discovery updates using global WebSocket
      this.setupDiscoverySubscription();

      // Start the scan via API
      const response = await this.makeDiscoveryRequest(scanConfig);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.detail ||
          errorData.message ||
          `Server error: ${response.status}`;
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log("Network scan started successfully:", result);

      // Store initial scan status
      this.scanStatus = result;

      // Notify listeners that scan has started with initial data
      this.notifyListeners({
        type: "scan_started",
        data: result,
      });

      return true;
    } catch (error) {
      console.error("Error starting network scan:", error);
      this.isScanning = false;
      this.cleanupDiscoverySubscription();

      // Notify listeners of error
      this.notifyListeners({
        type: "scan_error",
        data: { error: error.message },
      });

      throw error;
    }
  }

  /**
   * Stop the current scan
   * @returns {Promise<boolean>} - Success status
   */
  async stopScan() {
    if (!this.isScanning) {
      return true;
    }

    try {
      const response = await fetch("/api/discovery/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        console.log("Network scan stopped successfully");
      }

      this.isScanning = false;
      this.cleanupDiscoverySubscription();

      // Notify listeners that scan was stopped
      this.notifyListeners({
        type: "scan_stopped",
        data: { status: "stopped" },
      });

      return true;
    } catch (error) {
      console.error("Error stopping network scan:", error);
      this.isScanning = false;
      this.cleanupDiscoverySubscription();
      return false;
    }
  }

  /**
   * Get current scan status
   * @returns {Promise<Object>} - Current scan status
   */
  async getScanStatus() {
    try {
      const response = await fetch("/api/discovery/status");

      if (response.ok) {
        const status = await response.json();
        this.scanStatus = status;
        return status;
      }

      return { status: "not_started" };
    } catch (error) {
      console.error("Error getting scan status:", error);
      return { status: "error", error: error.message };
    }
  }

  /**
   * Prepare scan configuration with defaults and validation
   * @param {Object} options - Raw scan options
   * @returns {Object} - Validated scan configuration
   */
  prepareScanConfig(options) {
    const config = {
      network: options.network || "192.168.1.0/24",
      ports: options.ports || DEFAULT_SCAN_PORTS,
      timeout: options.timeout || 5,
    };

    // Convert different network formats to the format expected by the API
    if (options.startIp && options.endIp) {
      // Convert IP range to range format
      config.network = `${options.startIp}-${options.endIp}`;
    }

    // Validate network format
    if (!this.isValidNetworkFormat(config.network)) {
      throw new Error(
        "Invalid network format. Use CIDR notation (e.g., 192.168.1.0/24) or IP range (e.g., 192.168.1.1-192.168.1.254)",
      );
    }

    // Validate ports
    if (!Array.isArray(config.ports) || config.ports.length === 0) {
      config.ports = DEFAULT_SCAN_PORTS;
    }

    // Validate timeout
    if (
      typeof config.timeout !== "number" ||
      config.timeout < 1 ||
      config.timeout > 60
    ) {
      config.timeout = 5;
    }

    return config;
  }

  /**
   * Validate network format
   * @param {string} network - Network string to validate
   * @returns {boolean} - Whether the format is valid
   */
  isValidNetworkFormat(network) {
    // Check CIDR format
    const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    if (cidrPattern.test(network)) {
      return true;
    }

    // Check IP range format
    const rangePattern = /^(\d{1,3}\.){3}\d{1,3}-(\d{1,3}\.){3}\d{1,3}$/;
    if (rangePattern.test(network)) {
      return true;
    }

    return false;
  }

  /**
   * Make the discovery API request
   * @param {Object} config - Scan configuration
   * @returns {Promise<Response>} - Fetch response
   */
  async makeDiscoveryRequest(config) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch("/api/discovery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        throw new Error("Discovery request timed out after 30 seconds");
      }
      throw error;
    }
  }

  /**
   * Setup discovery subscription using global WebSocket
   */
  setupDiscoverySubscription() {
    console.log("Setting up discovery subscription");

    // Create message handler for discovery updates
    this.messageHandler = (message) => {
      if (message.type === "discovery_update" && message.data) {
        this.handleDiscoveryUpdate(message.data);
      }
    };

    // Add message handler to global WebSocket
    addMessageHandler(this.messageHandler);

    // Subscribe to discovery topic
    updateSubscriptions({ discovery: true });

    console.log("Discovery subscription setup complete");
  }

  /**
   * Cleanup discovery subscription
   */
  cleanupDiscoverySubscription() {
    console.log("Cleaning up discovery subscription");

    // Remove message handler
    if (this.messageHandler) {
      removeMessageHandler(this.messageHandler);
      this.messageHandler = null;
    }

    // Unsubscribe from discovery topic
    updateSubscriptions({ discovery: false });

    console.log("Discovery subscription cleanup complete");
  }

  /**
   * Handle discovery updates from WebSocket
   * @param {Object} data - Discovery update data
   */
  handleDiscoveryUpdate(data) {
    console.log("Network scan update:", data);

    this.scanStatus = data;

    // Update found miners
    if (data.found_miners && Array.isArray(data.found_miners)) {
      this.foundMiners = data.found_miners.map((miner) => ({
        id: `${miner.type}_${miner.ip_address}_${miner.port}`,
        name:
          miner.device_info?.model ||
          `${this.mapMinerType(miner.type)} (${miner.ip_address})`,
        ip_address: miner.ip_address,
        port: miner.port,
        type: miner.type,
        device_info: miner.device_info,
        status: "online",
      }));
    }

    // Handle scan completion
    if (data.status === "completed") {
      this.isScanning = false;
      this.cleanupDiscoverySubscription();

      console.log(
        `Network scan completed. Found ${this.foundMiners.length} miners.`,
      );
    } else if (data.status === "error") {
      this.isScanning = false;
      this.cleanupDiscoverySubscription();

      console.error("Network scan error:", data.error);
    }

    // Notify all listeners of the update
    this.notifyListeners({
      type: "scan_update",
      data: {
        status: data.status,
        progress: data.total_hosts
          ? (data.scanned_hosts / data.total_hosts) * 100
          : 0,
        currentIp: data.current_ip,
        foundMiners: this.foundMiners,
        totalHosts: data.total_hosts,
        scannedHosts: data.scanned_hosts,
        error: data.error,
      },
    });
  }

  /**
   * Map API miner types to display names
   * @param {string} apiType - API miner type
   * @returns {string} - Display name
   */
  mapMinerType(apiType) {
    const typeMap = {
      bitaxe: "Bitaxe",
      avalon_nano: "Avalon Nano",
      magic_miner: "Magic Miner",
      bitcoin_node: "Bitcoin Node",
    };
    return typeMap[apiType] || apiType;
  }

  /**
   * Get current scan state
   * @returns {Object} - Current state
   */
  getCurrentState() {
    return {
      isScanning: this.isScanning,
      scanStatus: this.scanStatus,
      foundMiners: this.foundMiners,
    };
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this.cleanupDiscoverySubscription();
    this.listeners.clear();
    this.isScanning = false;
    this.scanStatus = null;
    this.foundMiners = [];
  }
}

// Create a singleton instance
export const networkScanService = new NetworkScanService();

// Export default for convenience
export default networkScanService;
