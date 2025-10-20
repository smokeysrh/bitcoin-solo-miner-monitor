/**
 * Polling Manager Composable
 *
 * Provides centralized polling management with reactive settings support.
 * Automatically updates polling intervals when settings change and handles
 * cleanup on component unmount.
 *
 * Features:
 * - Reactive settings watcher that updates intervals automatically
 * - Polling state tracking (isPolling, lastPollTime, pollCount)
 * - Automatic cleanup on component unmount
 * - Minimum interval enforcement (5 seconds) for safety
 * - Duplicate request detection within 5-second window
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
 */

import { ref, watch, onUnmounted } from "vue";
import { useSettingsStore } from "../stores/settings";

// Global tracking for duplicate request detection
const activePollers = new Map();

export function usePollingManager(options) {
  // Validate and extract options
  const {
    fetchFunction, // Function to call for polling
    intervalKey = "refresh_interval", // Settings key (e.g., 'refresh_interval')
    componentName = "Unknown", // For logging/debugging
    enabled = true, // Whether polling is enabled
    minInterval = 5000, // Minimum interval (5 seconds safety)
  } = options;

  if (!fetchFunction || typeof fetchFunction !== "function") {
    throw new Error(
      "usePollingManager: fetchFunction is required and must be a function",
    );
  }

  // Get settings store
  const settingsStore = useSettingsStore();

  // Reactive state
  const isPolling = ref(false);
  const lastPollTime = ref(null);
  const pollCount = ref(0);
  const currentIntervalId = ref(null);
  const currentInterval = ref(null);

  /**
   * Get the current interval value from settings
   * @returns {number} Interval in milliseconds
   */
  const getIntervalFromSettings = () => {
    const settingValue = settingsStore.settings[intervalKey];
    const intervalMs = (settingValue || 10) * 1000; // Convert seconds to ms, default 10s

    // Enforce minimum interval for safety
    const safeInterval = Math.max(intervalMs, minInterval);

    if (intervalMs < minInterval) {
      console.warn(
        `[PollingManager:${componentName}] Interval ${intervalMs}ms is below minimum ${minInterval}ms. Using ${safeInterval}ms instead.`,
      );
    }

    return safeInterval;
  };

  /**
   * Check if another component is already polling within the duplicate detection window
   * @returns {boolean} True if duplicate polling detected
   */
  const checkDuplicatePolling = () => {
    const now = Date.now();
    const duplicateWindow = 5000; // 5 second window

    for (const [key, lastPoll] of activePollers.entries()) {
      if (key !== componentName && now - lastPoll < duplicateWindow) {
        console.warn(
          `[PollingManager:${componentName}] Duplicate polling detected! Component "${key}" polled ${now - lastPoll}ms ago.`,
        );
        return true;
      }
    }

    return false;
  };

  /**
   * Execute a single poll
   */
  const pollNow = async () => {
    if (!enabled) {
      console.log(
        `[PollingManager:${componentName}] Polling disabled, skipping poll`,
      );
      return;
    }

    try {
      // Check for duplicate polling
      checkDuplicatePolling();

      // Update tracking
      const now = Date.now();
      activePollers.set(componentName, now);
      lastPollTime.value = now;
      pollCount.value++;

      console.log(
        `[PollingManager:${componentName}] Poll #${pollCount.value} at ${new Date(now).toLocaleTimeString()}`,
      );

      // Execute the fetch function
      await fetchFunction();
    } catch (error) {
      console.error(`[PollingManager:${componentName}] Poll error:`, error);
      // Don't stop polling on single failure - continue polling
    }
  };

  /**
   * Start polling with current interval
   */
  const startPolling = () => {
    if (!enabled) {
      console.log(
        `[PollingManager:${componentName}] Polling disabled, not starting`,
      );
      return;
    }

    // Stop any existing polling first
    stopPolling();

    // Get current interval from settings
    const interval = getIntervalFromSettings();
    currentInterval.value = interval;

    console.log(
      `[PollingManager:${componentName}] Starting polling with interval ${interval}ms (${interval / 1000}s)`,
    );

    // Execute first poll immediately
    pollNow();

    // Set up interval for subsequent polls
    currentIntervalId.value = setInterval(() => {
      pollNow();
    }, interval);

    isPolling.value = true;
  };

  /**
   * Stop polling
   */
  const stopPolling = () => {
    if (currentIntervalId.value) {
      clearInterval(currentIntervalId.value);
      currentIntervalId.value = null;
      console.log(`[PollingManager:${componentName}] Polling stopped`);
    }

    isPolling.value = false;

    // Remove from active pollers
    activePollers.delete(componentName);
  };

  /**
   * Restart polling with new interval
   */
  const restartPolling = () => {
    const newInterval = getIntervalFromSettings();

    // Only restart if interval actually changed
    if (newInterval !== currentInterval.value) {
      console.log(
        `[PollingManager:${componentName}] Interval changed from ${currentInterval.value}ms to ${newInterval}ms, restarting polling`,
      );

      if (isPolling.value) {
        startPolling();
      }
    }
  };

  // Watch for settings changes
  watch(
    () => settingsStore.settings[intervalKey],
    (newValue, oldValue) => {
      if (newValue !== oldValue) {
        console.log(
          `[PollingManager:${componentName}] Settings changed: ${intervalKey} = ${newValue}s (was ${oldValue}s)`,
        );
        restartPolling();
      }
    },
  );

  // Auto-cleanup on component unmount
  onUnmounted(() => {
    console.log(
      `[PollingManager:${componentName}] Component unmounting, cleaning up polling`,
    );
    stopPolling();
  });

  // Return public API
  return {
    // Reactive state
    isPolling,
    lastPollTime,
    pollCount,
    currentInterval,

    // Methods
    startPolling,
    stopPolling,
    pollNow,

    // Computed values
    getIntervalFromSettings,
  };
}

export default usePollingManager;
