// Minimal safe main.js for testing
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
  },
});

// Create Pinia instance
const pinia = createPinia();

// Create and mount the app
const app = createApp(App);
app.use(vuetify);
app.use(pinia);
app.use(router);

app.mount("#app");
