/**
 * WebSocket Service - Debug Version
 *
 * This service handles WebSocket connections with comprehensive debugging.
 */

import { ref, reactive } from "vue";

// Debug logging system
const debugLogs = ref([]);
const MAX_DEBUG_LOGS = 1000;

function debugLog(message, data = null) {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    message,
    data: data ? JSON.stringify(data) : null,
    readyState: socket ? socket.readyState : "null",
    connectionStatus: connectionStatus.value,
  };

  debugLogs.value.push(logEntry);
  if (debugLogs.value.length > MAX_DEBUG_LOGS) {
    debugLogs.value.shift();
  }

  console.log(`[WS-DEBUG ${timestamp}] ${message}`, data || "");
}

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
const MAX_RECONNECT_ATTEMPTS = 10; // Increased for debugging
const RECONNECT_INTERVAL_BASE = 1000;
const HEARTBEAT_INTERVAL = 30000;

// Subscriptions
const subscriptions = reactive({
  miners: true,
  alerts: false,
  system: false,
});

// Debug state tracking
const debugState = reactive({
  initializationCount: 0,
  connectionAttempts: 0,
  successfulConnections: 0,
  failedConnections: 0,
  unexpectedDisconnects: 0,
  manualDisconnects: 0,
  pageRefreshes: 0,
  lastError: null,
  lastConnectionTime: null,
  lastDisconnectionTime: null,
});

/**
 * Initialize WebSocket connection with debug logging
 */
export function initWebSocket() {
  debugState.initializationCount++;
  debugLog(
    `initWebSocket called (attempt #${debugState.initializationCount})`,
    {
      isInitializing,
      currentReadyState: socket ? socket.readyState : "null",
      connectionStatus: connectionStatus.value,
    },
  );

  // Prevent multiple simultaneous initialization attempts
  if (isInitializing) {
    debugLog("WebSocket initialization already in progress - skipping");
    return;
  }

  // Don't reinitialize if already connected
  if (socket && socket.readyState === WebSocket.OPEN) {
    debugLog("WebSocket already connected - skipping");
    return;
  }

  isInitializing = true;
  debugState.connectionAttempts++;

  const host = window.location.hostname;
  const port = 8000;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${host}:${port}/ws`;

  debugLog("Creating WebSocket connection", { wsUrl, host, port, protocol });

  // Close existing connection if any
  if (socket) {
    debugLog("Closing existing socket", { readyState: socket.readyState });
    socket.close();
    socket = null;
  }

  try {
    // Create new WebSocket connection
    socket = new WebSocket(wsUrl);
    debugLog("WebSocket object created", { readyState: socket.readyState });

    // Set up event handlers
    socket.onopen = handleOpen;
    socket.onmessage = handleMessage;
    socket.onclose = handleClose;
    socket.onerror = handleError;

    connectionStatus.value = "connecting";
    connectionError.value = null;
    debugLog("WebSocket event handlers set, status updated to connecting");
  } catch (error) {
    debugState.failedConnections++;
    debugState.lastError = error.message;
    debugLog("Failed to create WebSocket connection", {
      error: error.message,
      stack: error.stack,
    });
    connectionStatus.value = "error";
    connectionError.value = "Failed to create connection";
    isInitializing = false;
  }
}

/**
 * Handle WebSocket open event
 */
function handleOpen() {
  debugState.successfulConnections++;
  debugState.lastConnectionTime = new Date().toISOString();
  debugLog("WebSocket connection established", {
    successfulConnections: debugState.successfulConnections,
    reconnectAttempts,
  });

  connectionStatus.value = "connected";
  connectionError.value = null;
  reconnectAttempts = 0;
  isInitializing = false;

  // Clear reconnect interval if set
  if (reconnectInterval) {
    clearInterval(reconnectInterval);
    reconnectInterval = null;
    debugLog("Cleared reconnect interval");
  }

  // Start heartbeat
  startHeartbeat();

  // Subscribe to topics
  subscribeToTopics();
}

/**
 * Handle WebSocket message event
 */
function handleMessage(event) {
  try {
    const message = JSON.parse(event.data);
    debugLog("Received WebSocket message", {
      type: message.type,
      size: event.data.length,
    });

    // Handle different message types
    switch (message.type) {
      case "connection_established":
        debugLog("Connection established with server", {
          client_id: message.client_id,
        });
        break;

      case "subscription_update":
        debugLog("Subscription updated", message);
        break;

      case "miners_update":
        debugLog("Miners update received", {
          minerCount: Array.isArray(message.data)
            ? message.data.length
            : "unknown",
        });
        handleMinersUpdate(message.data);
        break;

      case "alerts_update":
        debugLog("Alerts update received");
        handleAlertsUpdate(message.data);
        break;

      case "system_update":
        debugLog("System update received");
        handleSystemUpdate(message.data);
        break;

      case "ping":
        debugLog("Received ping from server");
        sendMessage({ type: "pong", timestamp: new Date().toISOString() });
        break;

      case "pong":
        debugLog("Received pong from server");
        break;

      case "error":
        debugLog("Server error received", message.data || message);
        break;

      case "validation_error":
        debugLog("Validation error received", message.data);
        break;

      case "processing_error":
        debugLog("Processing error received", message.data);
        break;

      default:
        debugLog("Unknown message type received", { type: message.type });
    }
  } catch (error) {
    debugLog("Error parsing WebSocket message", {
      error: error.message,
      rawData: event.data,
    });
  }
}

/**
 * Handle WebSocket close event
 */
function handleClose(event) {
  debugState.lastDisconnectionTime = new Date().toISOString();

  if (isManualDisconnect) {
    debugState.manualDisconnects++;
    debugLog("WebSocket manually closed", {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
    });
  } else {
    debugState.unexpectedDisconnects++;
    debugLog("WebSocket unexpectedly closed", {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
      unexpectedDisconnects: debugState.unexpectedDisconnects,
    });
  }

  connectionStatus.value = "disconnected";
  isInitializing = false;

  // Stop heartbeat
  stopHeartbeat();

  // Always attempt to reconnect unless it's a manual disconnect
  if (!isManualDisconnect) {
    debugLog("Initiating reconnection attempt");
    reconnectAttempts = 0;
    attemptReconnect();
  } else {
    debugLog("Manual disconnect - not attempting to reconnect");
    isManualDisconnect = false; // Reset flag
  }
}

/**
 * Handle WebSocket error event
 */
function handleError(error) {
  debugState.failedConnections++;
  debugState.lastError = error.toString();
  debugLog("WebSocket error occurred", {
    error: error.toString(),
    readyState: socket ? socket.readyState : "null",
  });
  connectionStatus.value = "error";
  connectionError.value = "Connection error";
  isInitializing = false;
}

/**
 * Attempt to reconnect to WebSocket
 */
function attemptReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    debugLog("Maximum reconnect attempts reached", {
      attempts: reconnectAttempts,
      maxAttempts: MAX_RECONNECT_ATTEMPTS,
    });
    connectionError.value = "Connection lost - retrying...";

    setTimeout(() => {
      debugLog("Resetting reconnect attempts after max reached");
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

  debugLog("Scheduling reconnection attempt", {
    attempt: reconnectAttempts + 1,
    maxAttempts: MAX_RECONNECT_ATTEMPTS,
    delay,
  });

  connectionStatus.value = "reconnecting";

  // Set up reconnect interval
  if (reconnectInterval) {
    clearTimeout(reconnectInterval);
  }

  reconnectInterval = setTimeout(() => {
    reconnectAttempts++;
    debugLog("Executing reconnection attempt", { attempt: reconnectAttempts });
    initWebSocket();
  }, delay);
}

/**
 * Subscribe to topics
 */
function subscribeToTopics() {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    debugLog("Cannot subscribe to topics - socket not open", {
      readyState: socket ? socket.readyState : "null",
    });
    return;
  }

  const topics = Object.keys(subscriptions).filter(
    (topic) => subscriptions[topic],
  );
  debugLog("Subscribing to topics", { topics });

  socket.send(
    JSON.stringify({
      type: "subscribe",
      topics,
    }),
  );
}

/**
 * Send message to WebSocket
 */
export function sendMessage(message) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    debugLog("Cannot send message - socket not open", {
      readyState: socket ? socket.readyState : "null",
      messageType: message.type,
    });
    return false;
  }

  try {
    socket.send(JSON.stringify(message));
    debugLog("Message sent successfully", { type: message.type });
    return true;
  } catch (error) {
    debugLog("Error sending message", {
      error: error.message,
      messageType: message.type,
    });
    return false;
  }
}

/**
 * Start heartbeat
 */
function startHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
  }

  debugLog("Starting heartbeat", { interval: HEARTBEAT_INTERVAL });

  heartbeatInterval = setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const success = sendMessage({
        type: "ping",
        timestamp: new Date().toISOString(),
      });
      if (!success) {
        debugLog("Heartbeat ping failed");
      }
    } else {
      debugLog("Heartbeat skipped - socket not open", {
        readyState: socket ? socket.readyState : "null",
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
    debugLog("Heartbeat stopped");
  }
}

/**
 * Handle miners update
 */
function handleMinersUpdate(data) {
  try {
    // Import dynamically to avoid circular dependencies
    import("../stores/miners").then(({ useMinersStore }) => {
      const minersStore = useMinersStore();
      minersStore.updateMiners(data);
      debugLog("Miners store updated", {
        minerCount: Array.isArray(data) ? data.length : "unknown",
      });
    });
  } catch (error) {
    debugLog("Error updating miners store", { error: error.message });
  }
}

/**
 * Handle alerts update
 */
function handleAlertsUpdate(data) {
  debugLog("Alerts update (not implemented)", { dataType: typeof data });
}

/**
 * Handle system update
 */
function handleSystemUpdate(data) {
  debugLog("System update (not implemented)", { dataType: typeof data });
}

/**
 * Close WebSocket connection manually
 */
export function closeConnection() {
  debugLog("Manual close connection requested");
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
 * Force reconnection
 */
export function forceReconnect() {
  debugLog("Force reconnection requested");
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

/**
 * Get debug information
 */
export function getDebugInfo() {
  return {
    debugState: { ...debugState },
    debugLogs: [...debugLogs.value],
    currentStatus: {
      connectionStatus: connectionStatus.value,
      connectionError: connectionError.value,
      socketReadyState: socket ? socket.readyState : null,
      isInitializing,
      isManualDisconnect,
      reconnectAttempts,
    },
    socketStates: {
      CONNECTING: WebSocket.CONNECTING,
      OPEN: WebSocket.OPEN,
      CLOSING: WebSocket.CLOSING,
      CLOSED: WebSocket.CLOSED,
    },
  };
}

/**
 * Clear debug logs
 */
export function clearDebugLogs() {
  debugLogs.value = [];
  debugLog("Debug logs cleared");
}

// Page lifecycle tracking
if (typeof window !== "undefined") {
  debugLog("WebSocket service loaded", {
    readyState: document.readyState,
    location: window.location.href,
  });

  // Track page refresh
  let isPageRefresh = false;
  if (performance.navigation) {
    isPageRefresh =
      performance.navigation.type === performance.navigation.TYPE_RELOAD;
  } else if (performance.getEntriesByType) {
    const navEntries = performance.getEntriesByType("navigation");
    isPageRefresh = navEntries.length > 0 && navEntries[0].type === "reload";
  }

  if (isPageRefresh) {
    debugState.pageRefreshes++;
    debugLog("Page refresh detected", {
      refreshCount: debugState.pageRefreshes,
    });
  }

  // Initialize immediately
  debugLog("Auto-initializing WebSocket connection");
  initWebSocket();

  // Backup initialization
  setTimeout(() => {
    if (
      connectionStatus.value === "disconnected" ||
      connectionStatus.value === "error"
    ) {
      debugLog("Backup initialization triggered");
      initWebSocket();
    }
  }, 200);

  // Page visibility changes
  document.addEventListener("visibilitychange", () => {
    debugLog("Page visibility changed", { hidden: document.hidden });
    if (
      !document.hidden &&
      (connectionStatus.value === "disconnected" ||
        connectionStatus.value === "error")
    ) {
      setTimeout(() => {
        initWebSocket();
      }, 50);
    }
  });

  // Page focus
  window.addEventListener("focus", () => {
    debugLog("Window focused");
    if (
      connectionStatus.value === "disconnected" ||
      connectionStatus.value === "error"
    ) {
      setTimeout(() => {
        initWebSocket();
      }, 50);
    }
  });

  // DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      debugLog("DOM content loaded");
      if (
        connectionStatus.value === "disconnected" ||
        connectionStatus.value === "error"
      ) {
        setTimeout(() => {
          initWebSocket();
        }, 25);
      }
    });
  } else {
    debugLog("DOM already loaded");
    setTimeout(() => {
      if (
        connectionStatus.value === "disconnected" ||
        connectionStatus.value === "error"
      ) {
        initWebSocket();
      }
    }, 25);
  }

  // Page load
  window.addEventListener("load", () => {
    debugLog("Page fully loaded");
    if (
      connectionStatus.value === "disconnected" ||
      connectionStatus.value === "error"
    ) {
      setTimeout(() => {
        initWebSocket();
      }, 25);
    }
  });

  // Before unload
  window.addEventListener("beforeunload", () => {
    debugLog("Page unloading");
    if (socket) {
      socket.close();
    }
  });

  // Unhandled errors
  window.addEventListener("error", (event) => {
    debugLog("Unhandled error", {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
    });
  });

  // Unhandled promise rejections
  window.addEventListener("unhandledrejection", (event) => {
    debugLog("Unhandled promise rejection", {
      reason: event.reason?.toString() || "unknown",
    });
  });
}

// Export debug functions for console access
if (typeof window !== "undefined") {
  window.wsDebug = {
    getDebugInfo,
    clearDebugLogs,
    forceReconnect,
    getConnectionStatus,
    initWebSocket,
  };
}

export { debugLogs, debugState };
