import { createRouter, createWebHistory } from "vue-router";

// Import views
import Dashboard from "../views/Dashboard.vue";
import SimpleDashboard from "../views/SimpleDashboard.vue";

// Define routes
const routes = [
  {
    path: "/",
    name: "Dashboard",
    component: Dashboard,
  },
  {
    path: "/dashboard-simple",
    name: "SimpleDashboard",
    component: SimpleDashboard,
  },
  {
    path: "/setup",
    name: "FirstRunSetup",
    component: () => import("../views/FirstRunSetup.vue"),
  },
  {
    path: "/miners",
    name: "Miners",
    component: () => import("../views/Miners.vue"),
  },
  {
    path: "/miners/:id",
    name: "MinerDetail",
    component: () => import("../views/MinerDetail.vue"),
    props: true,
  },
  {
    path: "/analytics",
    name: "Analytics",
    component: () => import("../views/Analytics.vue"),
  },
  {
    path: "/network",
    name: "Network",
    component: () => import("../views/Network.vue"),
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("../views/Settings.vue"),
  },
  {
    path: "/about",
    name: "About",
    component: () => import("../views/About.vue"),
  },
  {
    path: "/enhanced-components-test",
    name: "EnhancedComponentsTest",
    component: () => import("../views/EnhancedComponentsTest.vue"),
  },
  {
    path: "/card-layout-test",
    name: "CardLayoutTest",
    component: () => import("../views/CardLayoutTest.vue"),
  },
  {
    path: "/accessibility-animations-test",
    name: "AccessibilityAnimationsTest",
    component: () => import("../views/AccessibilityAnimationsTest.vue"),
  },
  {
    path: "/bitcoin-logo-test",
    name: "BitcoinLogoTest",
    component: () => import("../views/BitcoinLogoTest.vue"),
  },
  {
    path: "/easter-egg-test",
    name: "EasterEggTest",
    component: () => import("../components/EasterEggTest.vue"),
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("../views/NotFound.vue"),
  },
];

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
