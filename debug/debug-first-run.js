// Debug script for first run issues
// Run this in the browser console to debug the setup wizard issue

console.log("=== First Run Debug Script ===");

// Check current localStorage state
console.log("Current localStorage state:");
console.log("firstRunComplete:", localStorage.getItem("firstRunComplete"));
console.log("wizard-progress:", localStorage.getItem("wizard-progress"));
console.log("experienceLevel:", localStorage.getItem("experienceLevel"));
console.log("uiMode:", localStorage.getItem("uiMode"));
console.log("userPreferences:", localStorage.getItem("userPreferences"));
console.log("discoveredMiners:", localStorage.getItem("discoveredMiners"));

// Check all localStorage keys
console.log("All localStorage keys:", Object.keys(localStorage));

// Test the isFirstRun function
console.log("\nTesting isFirstRun function...");

// Import the function (this might not work in console, but worth trying)
try {
  // This will only work if the module is already loaded
  if (window.isFirstRun) {
    window.isFirstRun().then(result => {
      console.log("isFirstRun() result:", result);
    });
  } else {
    console.log("isFirstRun function not available in window object");
  }
} catch (error) {
  console.log("Error testing isFirstRun:", error);
}

// Test backend API
console.log("\nTesting backend API...");
fetch("/api/setup-status")
  .then(response => {
    console.log("Backend response status:", response.status);
    return response.json();
  })
  .then(data => {
    console.log("Backend setup status:", data);
  })
  .catch(error => {
    console.log("Backend API error:", error);
  });

// Provide reset function
console.log("\nTo reset first run state, run:");
console.log("window.resetFirstRun()");
console.log("Then refresh the page");

console.log("=== End Debug Script ===");