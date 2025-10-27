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

// Debug mode flag - only enable verbose logging in development
const DEBUG_MODE =
  import.meta.env.DEV || localStorage.getItem("debug") === "true";

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

// Message priority queue
const messagePriorityQueue = {
  high: [], // Heartbeat responses (pong)
  normal: [], // Regular messages (subscribe, status requests)
  low: [], // Broadcast updates
};

// Queue processing state
let isProcessingQueue = false;

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
    if (DEBUG_MODE) {
      console.log("WebSocket initialization already in progress");
    }
    return;
  }

  if (socket && socket.readyState === WebSocket.OPEN) {
    if (DEBUG_MODE) {
      console.log("WebSocket already connected");
    }
    return;
  }

  isInitializing = true;

  const host = window.location.hostname;
  const port = 8000;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${host}:${port}/ws`;

  if (DEBUG_MODE) {
    console.log("Connecting to WebSocket:", wsUrl);
  }

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
  // Log connection at info level (important event)
  console.info("WebSocket connection established");
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

  // Automatically restore subscriptions after reconnection
  // This ensures that active scans and other subscriptions continue working
  subscribeToTopics();
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
        if (DEBUG_MODE) {
          console.log("Connection established with ID:", message.client_id);
        }
        break;

      case "subscription_update":
        if (DEBUG_MODE) {
          console.log("Subscription updated:", message);
        }
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

      case "ping": {
        // Respond to server ping with pong - HIGH PRIORITY to prevent timeout
        const pongStartTime = performance.now();
        sendMessage(
          { type: "pong", timestamp: new Date().toISOString() },
          "high",
        );
        const pongEndTime = performance.now();
        const pongLatency = pongEndTime - pongStartTime;

        // Log if response took longer than 100ms
        if (pongLatency > 100 && DEBUG_MODE) {
          console.warn(
            `Pong response took ${pongLatency.toFixed(2)}ms (target: <100ms)`,
          );
        }
        break;
      }

      case "pong":
        // Server responded to our ping
        if (DEBUG_MODE) {
          console.log("Received pong from server");
        }
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
        if (DEBUG_MODE) {
          console.log("Status response:", message.data);
        }
        break;

      case "topics_response":
        if (DEBUG_MODE) {
          console.log("Available topics:", message.data);
        }
        break;

      case "discovery_update":
        // Handle discovery updates - notify custom handlers
        if (DEBUG_MODE) {
          console.log("Discovery update received:", message.data);
        }
        notifyCustomHandlers(message);
        break;

      default:
        if (DEBUG_MODE) {
          console.log("Unknown message type:", message.type);
        }
        // Notify custom handlers for unknown message types too
        notifyCustomHandlers(message);
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
  // Log connection close at info level (important event)
  console.info("WebSocket connection closed:", event.code, event.reason);
  connectionStatus.value = "disconnected";
  isInitializing = false;

  // Stop heartbeat
  stopHeartbeat();

  // Always attempt to reconnect unless it's a manual disconnect
  // This handles page refreshes, network issues, and server restarts
  if (!isManualDisconnect) {
    if (DEBUG_MODE) {
      console.log("Connection lost, attempting to reconnect...");
    }
    // For page refreshes and unexpected disconnects, start fresh
    reconnectAttempts = 0;
    attemptReconnect();
  } else {
    if (DEBUG_MODE) {
      console.log("Manual disconnect, not attempting to reconnect");
    }
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
    console.error(
      "Maximum reconnect attempts reached, will retry in 10 seconds",
    );
    connectionError.value = "Connection lost - retrying...";
    setTimeout(() => {
      reconnectAttempts = 0;
      attemptReconnect();
    }, 10000);
    return;
  }

  const delay =
    reconnectAttempts === 0
      ? 25
      : reconnectAttempts === 1
        ? 50
        : reconnectAttempts === 2
          ? 100
          : Math.min(
              RECONNECT_INTERVAL_BASE * Math.pow(1.5, reconnectAttempts - 3),
              5000,
            );

  if (DEBUG_MODE) {
    console.log(
      `Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`,
    );
  }
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
    if (DEBUG_MODE) {
      console.log("Cannot subscribe to topics: WebSocket not open");
    }
    return;
  }

  // Get topics to subscribe to - use toRaw to access the actual object
  const rawSubscriptions = { ...subscriptions };
  const topics = Object.keys(rawSubscriptions).filter(
    (topic) => rawSubscriptions[topic] === true,
  );

  if (DEBUG_MODE) {
    console.log("Subscribing to topics:", topics);
    console.log("Raw subscriptions:", rawSubscriptions);
  }

  if (topics.length === 0) {
    if (DEBUG_MODE) {
      console.warn("No topics to subscribe to");
    }
    return;
  }

  // Send subscribe message
  const message = {
    type: "subscribe",
    topics,
  };

  if (DEBUG_MODE) {
    console.log("Sending subscription message:", message);
  }
  socket.send(JSON.stringify(message));
}

/**
 * Update subscriptions
 * @param {Object} newSubscriptions - New subscriptions
 */
export function updateSubscriptions(newSubscriptions) {
  // Update subscriptions - set each property individually to maintain reactivity
  Object.keys(newSubscriptions).forEach((key) => {
    subscriptions[key] = newSubscriptions[key];
  });

  if (DEBUG_MODE) {
    console.log("Updated subscriptions:", JSON.stringify(subscriptions));
  }

  // Subscribe to topics - use a small delay to batch multiple updates
  if (updateSubscriptions.timeout) {
    clearTimeout(updateSubscriptions.timeout);
  }

  updateSubscriptions.timeout = setTimeout(() => {
    subscribeToTopics();
    updateSubscriptions.timeout = null;
  }, 100);
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
  if (DEBUG_MODE) {
    console.log("Alerts update:", data);
  }
}

/**
 * Handle system update
 * @param {Object} data - System data
 */
function handleSystemUpdate(data) {
  // TODO: Implement system store
  if (DEBUG_MODE) {
    console.log("System update:", data);
  }
}

/**
 * Process message priority queue
 * Processes high-priority messages first, then normal, then low
 */
function processMessageQueue() {
  // Prevent concurrent queue processing
  if (isProcessingQueue) {
    return;
  }

  isProcessingQueue = true;

  try {
    // Process all high-priority messages first (heartbeat responses)
    while (messagePriorityQueue.high.length > 0) {
      const message = messagePriorityQueue.high.shift();
      sendMessageImmediate(message);
    }

    // Process normal priority messages
    while (messagePriorityQueue.normal.length > 0) {
      const message = messagePriorityQueue.normal.shift();
      sendMessageImmediate(message);
    }

    // Process low priority messages
    while (messagePriorityQueue.low.length > 0) {
      const message = messagePriorityQueue.low.shift();
      sendMessageImmediate(message);
    }
  } finally {
    isProcessingQueue = false;
  }
}

/**
 * Send message immediately without queueing
 * @param {Object} message - Message to send
 */
function sendMessageImmediate(message) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error("WebSocket not connected");
    return;
  }

  try {
    socket.send(JSON.stringify(message));
  } catch (error) {
    console.error("Error sending WebSocket message:", error);
  }
}

/**
 * Send message to WebSocket with priority
 * @param {Object} message - Message to send
 * @param {string} priority - Priority level: 'high', 'normal', or 'low' (default: 'normal')
 */
export function sendMessage(message, priority = "normal") {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error("WebSocket not connected");
    return;
  }

  // Validate priority
  if (!["high", "normal", "low"].includes(priority)) {
    console.warn(`Invalid priority "${priority}", using "normal"`);
    priority = "normal";
  }

  // Add message to appropriate queue
  messagePriorityQueue[priority].push(message);

  // Process queue immediately
  processMessageQueue();
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
  if (DEBUG_MODE) {
    console.log("Manually closing WebSocket connection");
  }
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
  if (DEBUG_MODE) {
    console.log("Forcing WebSocket reconnection...");
  }
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
      if (DEBUG_MODE) {
        console.log(
          "Backup initialization: WebSocket still not connected, retrying...",
        );
      }
      initWebSocket();
    }
  }, 200);

  // Handle page visibility changes to reconnect when page becomes visible
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && connectionStatus.value === "disconnected") {
      if (DEBUG_MODE) {
        console.log("Page became visible, attempting to reconnect WebSocket");
      }
      initWebSocket();
    }
  });

  // Handle window focus to reconnect
  window.addEventListener("focus", () => {
    if (connectionStatus.value === "disconnected") {
      if (DEBUG_MODE) {
        console.log("Window focused, attempting to reconnect WebSocket");
      }
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

// Custom message handlers
const customMessageHandlers = new Set();

/**
 * Add a custom message handler
 * @param {Function} handler - Handler function that receives the message
 */
export function addMessageHandler(handler) {
  customMessageHandlers.add(handler);
  if (DEBUG_MODE) {
    console.log(
      `Added custom message handler. Total handlers: ${customMessageHandlers.size}`,
    );
  }
}

/**
 * Remove a custom message handler
 * @param {Function} handler - Handler function to remove
 */
export function removeMessageHandler(handler) {
  customMessageHandlers.delete(handler);
  if (DEBUG_MODE) {
    console.log(
      `Removed custom message handler. Total handlers: ${customMessageHandlers.size}`,
    );
  }
}

/**
 * Notify all custom message handlers
 * @param {Object} message - Message to send to handlers
 */
function notifyCustomHandlers(message) {
  customMessageHandlers.forEach((handler) => {
    try {
      handler(message);
    } catch (error) {
      console.error("Error in custom message handler:", error);
    }
  });
}
