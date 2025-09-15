/**
 * WebSocket Service
 *
 * This service handles WebSocket connections for real-time updates.
 *
 * PHASE 1 TESTING MODE:
 * - WebSocket connections are DISABLED to prevent browser unresponsiveness
 * - Aggressive reconnection attempts are DISABLED
 * - Event listeners for auto-reconnection are DISABLED
 * - This allows stable testing of the setup wizard and UI components
 *
 * FOR PHASE 2 (Desktop App Testing):
 * - Uncomment the disabled code sections
 * - Re-enable initWebSocket() calls in App.vue
 * - Test with real miners and live data
 */

import { ref, reactive } from "vue";
import { useMinersStore } from "../stores/miners";
import { useSettingsStore as _useSettingsStore } from "../stores/settings";

// Connection status
export const connectionStatus = ref("disconnected");
export const connectionError = ref(null);

// WebSocket instance
let socket = null;
let reconnectInterval = null;
let heartbeatInterval = null;
let reconnectAttempts = 0;
let isInitializing = false;
let isManualDisconnect = false;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_INTERVAL_BASE = 1000; // 1 second
const HEARTBEAT_INTERVAL = 30000; // 30 seconds

// Subscriptions
const subscriptions = reactive({
  miners: true,
  alerts: false,
  system: false,
});

/**
 * Initialize WebSocket connection
 */
export function initWebSocket() {
  if (isInitializing) {
    console.log("WebSocket initialization already in progress");
    return;
  }

  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log("WebSocket already connected");
    return;
  }

  isInitializing = true;

  const host = window.location.hostname;
  const port = 8000;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${host}:${port}/ws`;
  
  console.log("Connecting to WebSocket:", wsUrl);

  if (socket) {
    socket.close();
    socket = null;
  }

  try {
    socket = new WebSocket(wsUrl);
    socket.onopen = handleOpen;
    socket.onmessage = handleMessage;
    socket.onclose = handleClose;
    socket.onerror = handleError;
    connectionStatus.value = "connecting";
    connectionError.value = null;
  } catch (error) {
    console.error("Failed to create WebSocket connection:", error);
    connectionStatus.value = "error";
    connectionError.value = "Failed to create connection";
    isInitializing = false;
  }
}

/**
 * Handle WebSocket open event
 */
function handleOpen() {
  console.log("WebSocket connection established");
  connectionStatus.value = "connected";
  connectionError.value = null;
  reconnectAttempts = 0;
  isInitializing = false;

  // Clear reconnect interval if set
  if (reconnectInterval) {
    clearInterval(reconnectInterval);
    reconnectInterval = null;
  }

  // Start heartbeat
  startHeartbeat();

  // Don't automatically subscribe - let the stores handle their own subscriptions
  // subscribeToTopics();
}

/**
 * Handle WebSocket message event
 * @param {MessageEvent} event - WebSocket message event
 */
function handleMessage(event) {
  try {
    const message = JSON.parse(event.data);

    // Handle different message types
    switch (message.type) {
      case "connection_established":
        console.log("Connection established with ID:", message.client_id);
        break;

      case "subscription_update":
        console.log("Subscription updated:", message);
        break;

      case "miners_update":
        handleMinersUpdate(message.data);
        break;

      case "alerts_update":
        handleAlertsUpdate(message.data);
        break;

      case "system_update":
        handleSystemUpdate(message.data);
        break;

      case "ping":
        // Respond to server ping with pong
        sendMessage({ type: "pong", timestamp: new Date().toISOString() });
        break;

      case "pong":
        // Server responded to our ping
        console.log("Received pong from server");
        break;

      case "error":
        console.error("Server error:", message.data || message);
        break;

      case "validation_error":
        console.error("Validation error:", message.data);
        break;

      case "processing_error":
        console.error("Processing error:", message.data);
        break;

      case "status_response":
        console.log("Status response:", message.data);
        break;

      case "topics_response":
        console.log("Available topics:", message.data);
        break;

      default:
        console.log("Unknown message type:", message.type);
    }
  } catch (error) {
    console.error("Error parsing WebSocket message:", error);
  }
}

/**
 * Handle WebSocket close event
 * @param {CloseEvent} event - WebSocket close event
 */
function handleClose(event) {
  console.log("WebSocket connection closed:", event.code, event.reason);
  connectionStatus.value = "disconnected";
  isInitializing = false;

  // Stop heartbeat
  stopHeartbeat();

  // Always attempt to reconnect unless it's a manual disconnect
  // This handles page refreshes, network issues, and server restarts
  if (!isManualDisconnect) {
    console.log("Connection lost, attempting to reconnect...");
    // For page refreshes and unexpected disconnects, start fresh
    reconnectAttempts = 0;
    attemptReconnect();
  } else {
    console.log("Manual disconnect, not attempting to reconnect");
    isManualDisconnect = false; // Reset flag
  }
}

/**
 * Handle WebSocket error event
 * @param {Event} error - WebSocket error event
 */
function handleError(error) {
  console.error("WebSocket error:", error);
  connectionStatus.value = "error";
  connectionError.value = "Connection error";
  isInitializing = false;
}

/**
 * Attempt to reconnect to WebSocket
 */
function attemptReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error("Maximum reconnect attempts reached, will retry in 10 seconds");
    connectionError.value = "Connection lost - retrying...";
    setTimeout(() => {
      reconnectAttempts = 0;
      attemptReconnect();
    }, 10000);
    return;
  }

  const delay = reconnectAttempts === 0 ? 25 : reconnectAttempts === 1 ? 50 : 
    reconnectAttempts === 2 ? 100 : Math.min(RECONNECT_INTERVAL_BASE * Math.pow(1.5, reconnectAttempts - 3), 5000);

  console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
  connectionStatus.value = "reconnecting";

  if (reconnectInterval) {
    clearTimeout(reconnectInterval);
  }

  reconnectInterval = setTimeout(() => {
    reconnectAttempts++;
    initWebSocket();
  }, delay);
}

/**
 * Subscribe to topics
 */
function subscribeToTopics() {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.log("Cannot subscribe to topics: WebSocket not open");
    return;
  }

  // Get topics to subscribe to
  const topics = Object.keys(subscriptions).filter(
    (topic) => subscriptions[topic],
  );

  console.log("Subscribing to topics:", topics);
  console.log("Subscriptions object:", subscriptions);

  // Send subscribe message
  const message = {
    type: "subscribe",
    topics,
  };

  console.log("Sending subscription message:", message);
  socket.send(JSON.stringify(message));
}

/**
 * Update subscriptions
 * @param {Object} newSubscriptions - New subscriptions
 */
export function updateSubscriptions(newSubscriptions) {
  // Update subscriptions
  Object.assign(subscriptions, newSubscriptions);

  // Subscribe to topics
  subscribeToTopics();
}

/**
 * Handle miners update
 * @param {Array} data - Miners data
 */
function handleMinersUpdate(data) {
  const minersStore = useMinersStore();
  minersStore.updateMiners(data);
}

/**
 * Handle alerts update
 * @param {Array} data - Alerts data
 */
function handleAlertsUpdate(data) {
  // TODO: Implement alerts store
  console.log("Alerts update:", data);
}

/**
 * Handle system update
 * @param {Object} data - System data
 */
function handleSystemUpdate(data) {
  // TODO: Implement system store
  console.log("System update:", data);
}

/**
 * Send message to WebSocket
 * @param {Object} message - Message to send
 */
export function sendMessage(message) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error("WebSocket not connected");
    return;
  }

  socket.send(JSON.stringify(message));
}

/**
 * Start heartbeat to keep connection alive
 */
function startHeartbeat() {
  // Clear existing heartbeat
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
  }

  // Send ping every 30 seconds
  heartbeatInterval = setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      sendMessage({
        type: "ping",
        timestamp: new Date().toISOString(),
      });
    }
  }, HEARTBEAT_INTERVAL);
}

/**
 * Stop heartbeat
 */
function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
}

/**
 * Close WebSocket connection manually
 */
export function closeConnection() {
  console.log("Manually closing WebSocket connection");
  isManualDisconnect = true;
  stopHeartbeat();

  if (socket) {
    socket.close(1000, "User initiated disconnect");
  }

  if (reconnectInterval) {
    clearInterval(reconnectInterval);
    reconnectInterval = null;
  }

  connectionStatus.value = "disconnected";
}

/**
 * Force reconnection (useful for manual retry)
 */
export function forceReconnect() {
  console.log("Forcing WebSocket reconnection...");
  isManualDisconnect = false;
  reconnectAttempts = 0;

  if (socket) {
    socket.close();
  }

  if (reconnectInterval) {
    clearTimeout(reconnectInterval);
    reconnectInterval = null;
  }

  setTimeout(() => {
    initWebSocket();
  }, 100);
}

/**
 * Get current connection status
 */
export function getConnectionStatus() {
  return {
    status: connectionStatus.value,
    error: connectionError.value,
    isConnected: connectionStatus.value === "connected",
    isConnecting:
      connectionStatus.value === "connecting" ||
      connectionStatus.value === "reconnecting",
  };
}

// Auto-initialize WebSocket connection when service is imported
// This ensures connection is established as soon as the app loads
if (typeof window !== "undefined") {
  // Initialize WebSocket connection
  initWebSocket();

  // Backup initialization to ensure connection
  setTimeout(() => {
    if (
      connectionStatus.value === "disconnected" ||
      connectionStatus.value === "error"
    ) {
      console.log(
        "Backup initialization: WebSocket still not connected, retrying...",
      );
      initWebSocket();
    }
  }, 200);

  // Handle page visibility changes to reconnect when page becomes visible
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && connectionStatus.value === "disconnected") {
      console.log("Page became visible, attempting to reconnect WebSocket");
      initWebSocket();
    }
  });

  // Handle window focus to reconnect
  window.addEventListener("focus", () => {
    if (connectionStatus.value === "disconnected") {
      console.log("Window focused, attempting to reconnect WebSocket");
      initWebSocket();
    }
  });

  // Handle beforeunload to clean up connection
  window.addEventListener("beforeunload", () => {
    // Don't set isManualDisconnect for page refreshes/navigation
    // The connection will be re-established when the page loads
    if (socket) {
      socket.close();
    }
  });
}
