/**
 * First Run Service
 * Handles detection and management of first-run state for the application
 */

/**
 * Check if this is the first time the application is being run
 * @returns {boolean} True if this is the first run, false otherwise
 */
export const isFirstRun = async () => {
  // Check for URL parameter override (for testing)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("forceSetup") === "true") {
    return true;
  }

  // First check localStorage for web-based completion
  const firstRunComplete = localStorage.getItem("firstRunComplete");

  if (firstRunComplete === "true") {
    return false;
  }

  // Backend API call disabled during Phase 1 testing
  // This prevents browser hanging on backend connections

  // Return true only if first run is not complete
  return true;
};

/**
 * Mark the first run as complete
 */
export const completeFirstRun = () => {
  localStorage.setItem("firstRunComplete", "true");
};

/**
 * Reset the first run state (for testing or when resetting the application)
 */
/**
 * Reset the first run state (for testing or when resetting the application)
 */
export const resetFirstRun = () => {
  localStorage.removeItem("firstRunComplete");
  localStorage.removeItem("wizard-progress");
  localStorage.removeItem("wizard-experience-level");
  localStorage.removeItem("wizard-found-miners");
  localStorage.removeItem("wizard-settings");
  localStorage.removeItem("wizard-preferences");
};

/**
 * Force reset for debugging - can be called from browser console
 * Usage: window.resetFirstRun()
 */
export const forceResetFirstRun = () => {
  resetFirstRun();
  // Also clear other related localStorage items
  localStorage.removeItem("experienceLevel");
  localStorage.removeItem("uiMode");
  localStorage.removeItem("userPreferences");
  localStorage.removeItem("discoveredMiners");
  localStorage.removeItem("theme");
  localStorage.removeItem("appSettings");
  localStorage.removeItem("defaultView");
  return "Reset complete - refresh the page";
};

/**
 * Save the setup data from the first-run wizard
 * @param {Object} setupData - The data collected during the setup wizard
 */
export const saveSetupData = (setupData) => {
  // Save experience level
  localStorage.setItem("experienceLevel", setupData.experienceLevel);

  // Save theme preference - THIS WAS MISSING!
  if (setupData.settings.theme) {
    localStorage.setItem("theme", setupData.settings.theme);
    
    // Apply theme immediately
    if (window.$vuetify) {
      window.$vuetify.theme.global.name.value = setupData.settings.theme;
    }
    document.documentElement.setAttribute('data-theme', setupData.settings.theme);
  }

  // Save UI mode preference
  localStorage.setItem(
    "uiMode",
    setupData.settings.simple_mode ? "simple" : "advanced",
  );

  // Save default view preference
  localStorage.setItem("defaultView", setupData.settings.default_view);

  // Save all settings for later use
  localStorage.setItem("appSettings", JSON.stringify(setupData.settings));

  // Save preferences (including email settings)
  localStorage.setItem(
    "userPreferences",
    JSON.stringify(setupData.preferences),
  );

  // Save discovered miners
  if (setupData.foundMiners && setupData.foundMiners.length > 0) {
    localStorage.setItem(
      "discoveredMiners",
      JSON.stringify(setupData.foundMiners),
    );
  }

  // Mark first run as complete
  completeFirstRun();
};

/**
 * Get the appropriate route based on the user's preferences
 * @returns {string} The route path to redirect to
 */
export const getInitialRoute = () => {
  // First check if user has a specific default view preference
  const defaultView = localStorage.getItem("defaultView");

  if (defaultView) {
    // Map the default view values to actual routes
    const routeMap = {
      dashboard: "/",
      "dashboard-simple": "/dashboard-simple",
      miners: "/miners",
      analytics: "/analytics",
      network: "/network",
    };

    // Return the mapped route if it exists
    if (routeMap[defaultView]) {
      return routeMap[defaultView];
    }
  }

  // Fallback to UI mode preference
  const uiMode = localStorage.getItem("uiMode") || "advanced";
  return uiMode === "simple" ? "/dashboard-simple" : "/";
};

/**
 * Get the user's experience level
 * @returns {string} The user's experience level (beginner, intermediate, advanced)
 */
export const getExperienceLevel = () => {
  return localStorage.getItem("experienceLevel") || "beginner";
};

/**
 * Get the user's preferences
 * @returns {Object} The user's preferences
 */
export const getUserPreferences = () => {
  const preferencesJson = localStorage.getItem("userPreferences");
  return preferencesJson ? JSON.parse(preferencesJson) : {};
};

/**
 * Get the discovered miners from the first-run wizard
 * @returns {Array} The discovered miners
 */
export const getDiscoveredMiners = () => {
  const minersJson = localStorage.getItem("discoveredMiners");
  return minersJson ? JSON.parse(minersJson) : [];
};

/**
 * Import setup data from the Electron installer
 * @param {Object} installerData - Setup data from the installer
 */
const importInstallerSetupData = async (installerData) => {
  // Save experience level
  if (installerData.experienceLevel) {
    localStorage.setItem("experienceLevel", installerData.experienceLevel);
  }

  // Save UI mode preference
  if (
    installerData.settings &&
    typeof installerData.settings.simple_mode === "boolean"
  ) {
    localStorage.setItem(
      "uiMode",
      installerData.settings.simple_mode ? "simple" : "advanced",
    );
  }

  // Save preferences (including email settings)
  if (installerData.preferences) {
    localStorage.setItem(
      "userPreferences",
      JSON.stringify(installerData.preferences),
    );
  }

  // Save discovered miners
  if (installerData.foundMiners && installerData.foundMiners.length > 0) {
    localStorage.setItem(
      "discoveredMiners",
      JSON.stringify(installerData.foundMiners),
    );
  }

  // Mark first run as complete
  completeFirstRun();
};
