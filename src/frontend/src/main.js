// Removed debug console.log statements that might cause browser crashes
import { createApp } from "vue";
import { createPinia } from "pinia";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import { aliases, mdi } from "vuetify/iconsets/mdi";

// Import Vuetify styles
import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";

// Import our custom CSS system
import "./assets/css/main.css";

import App from "./App.vue";
import router from "./router";
import { initWebSocket as _initWebSocket } from "./services/websocket";
import { forceResetFirstRun } from "./services/firstRunService";

// Import accessibility and performance utilities - temporarily disabled for debugging
// import { initializeFocusManagement } from "./utils/focus-management";
// import { initializeCriticalCSSLoader } from "./utils/critical-css-loader";
// import { initializeAccessibilityTesting } from "./utils/accessibility-testing";
// import { initializeWCAGValidation } from "./utils/wcag-validator";

// Create Vuetify instance
const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: "dark",
    themes: {
      light: {
        dark: false,
        colors: {
          primary: "#F7931A", // Bitcoin Orange
          "primary-darken-1": "#E58E19",
          "primary-lighten-1": "#FF9F2E",
          secondary: "#424242",
          accent: "#FF9F2E",
          error: "#FF5252",
          "error-darken-1": "#D32F2F",
          info: "#2196F3",
          "info-darken-1": "#1976D2",
          success: "#4CAF50",
          "success-darken-1": "#388E3C",
          warning: "#FB8C00",
          "warning-darken-1": "#F57C00",
          background: "#FAFAFA",
          surface: "#FFFFFF",
          "surface-variant": "#F5F5F5",
          "on-surface": "#212121",
          "on-surface-variant": "#757575",
          "on-primary": "#FFFFFF",
        },
      },
      dark: {
        dark: true,
        colors: {
          // Primary Bitcoin Orange colors
          primary: "#F7931A", // Bitcoin Orange
          "primary-darken-1": "#E58E19", // Bitcoin Orange Hover
          "primary-lighten-1": "#FF9F2E", // Bitcoin Orange Light

          // Secondary colors
          secondary: "#424242",
          accent: "#FF9F2E",

          // Status colors matching design specification
          error: "#FF5252",
          "error-darken-1": "#D32F2F",
          "error-lighten-1": "#FF7961",
          info: "#2196F3",
          "info-darken-1": "#1976D2",
          "info-lighten-1": "#64B5F6",
          success: "#4CAF50",
          "success-darken-1": "#388E3C",
          "success-lighten-1": "#66BB6A",
          warning: "#FB8C00",
          "warning-darken-1": "#F57C00",
          "warning-lighten-1": "#FFB74D",

          // Background colors from design specification
          background: "#121212", // Primary Background
          surface: "#1E1E1E", // Surface Background
          "surface-variant": "#2A2A2A", // Secondary Surface
          "surface-bright": "#2C2C2C", // Elevated Surface

          // Text colors from design specification
          "on-surface": "#FFFFFF", // Primary Text
          "on-surface-variant": "#CCCCCC", // Secondary Text
          "on-primary": "#FFFFFF",
          "on-secondary": "#FFFFFF",
          "on-background": "#FFFFFF",
          "on-error": "#FFFFFF",
          "on-warning": "#FFFFFF",
          "on-info": "#FFFFFF",
          "on-success": "#FFFFFF",

          // Border and outline colors from design specification
          outline: "#555555", // Primary Border
          "outline-variant": "#333333", // Subtle Border

          // Additional surface variations for better component styling
          "surface-container": "#1E1E1E",
          "surface-container-high": "#2A2A2A",
          "surface-container-highest": "#2C2C2C",
          "surface-container-low": "#1A1A1A",
          "surface-container-lowest": "#0F0F0F",

          // Inverse colors for special cases
          "inverse-surface": "#E6E1E5",
          "inverse-on-surface": "#313033",
          "inverse-primary": "#6750A4",

          // Disabled and hint text colors
          "on-surface-disabled": "#666666", // Disabled Text
          "on-surface-hint": "#999999", // Hint Text
        },
      },
    },
  },
});

// Create Pinia instance
const pinia = createPinia();

// Initialize accessibility and performance systems - temporarily disabled for debugging
// const { modalManager } = initializeFocusManagement();
// const { loader: _loader, optimizer } = initializeCriticalCSSLoader();
// const accessibilityTester = initializeAccessibilityTesting();
// const wcagValidator = initializeWCAGValidation();

// Create and mount the app
const app = createApp(App);
app.use(vuetify);
app.use(pinia);
app.use(router);

// Make Vuetify instance globally available for theme switching
if (typeof window !== "undefined") {
  window.$vuetify = vuetify;
}

// Set theme to dark (theme switching removed)
vuetify.theme.global.name.value = 'dark';
document.documentElement.setAttribute('data-theme', 'dark');

// Simple app mount without debug logging
app.mount("#app");

// Make utilities available globally for debugging and development
if (typeof window !== "undefined") {
  window.resetFirstRun = forceResetFirstRun;

  // Add debug function to check localStorage state
  window.debugFirstRun = () => {
    return {
      firstRunComplete: localStorage.getItem("firstRunComplete"),
      wizardProgress: localStorage.getItem("wizard-progress"),
      experienceLevel: localStorage.getItem("experienceLevel"),
      uiMode: localStorage.getItem("uiMode"),
      userPreferences: localStorage.getItem("userPreferences"),
      discoveredMiners: localStorage.getItem("discoveredMiners"),
      allKeys: Object.keys(localStorage),
    };
  };

  // Add function to manually test first run
  window.testFirstRun = async () => {
    try {
      const { isFirstRun } = await import("./services/firstRunService.js");
      const result = await isFirstRun();
      return result;
    } catch (error) {
      return { error: error.message };
    }
  };

  // Add function to manually navigate to setup
  window.goToSetup = () => {
    window.location.href = "/setup";
  };

  // Force setup wizard function removed - was causing state persistence issues
  // window.forceSetupWizard = () => {
  //   window.resetFirstRun();
  //   setTimeout(() => {
  //     window.location.reload();
  //   }, 100);
  // };

  // Debug functions available (logging removed to prevent browser crashes)
  // Available: window.resetFirstRun(), window.debugFirstRun(), window.testFirstRun(), window.goToSetup()
  // Note: forceSetupWizard() removed to fix state persistence issues

  // Development reset button removed - was causing issues with wizard state persistence
}
