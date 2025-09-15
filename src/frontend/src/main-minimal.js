// Ultra-minimal Vue app for testing
import { createApp } from "vue";

console.log("✅ Starting minimal Vue app...");

// Minimal app component
const MinimalApp = {
  template: `
    <div>
      <h1>Minimal Vue App Works!</h1>
      <p>If you can see this, Vue.js is working.</p>
      <button @click="test">Test Button</button>
    </div>
  `,
  methods: {
    test() {
      alert("Button works!");
      console.log("Button clicked successfully");
    },
  },
};

console.log("✅ Creating Vue app...");
const app = createApp(MinimalApp);

console.log("✅ About to mount minimal app...");
try {
  app.mount("#app");
  console.log("✅ Minimal app mounted successfully!");
} catch (error) {
  console.error("❌ Minimal app mount failed:", error);
  alert("Minimal app failed: " + error.message);
}
