import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// The Python app serves whatever lands in ../src/bsmm/web, so `npm run build` is all a release needs.
const outDir = fileURLToPath(new URL('../src/bsmm/web', import.meta.url))
const apiTarget = process.env.BSMM_DEV_API ?? 'http://127.0.0.1:8420'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    outDir,
    emptyOutDir: true,
    target: 'es2022',
    sourcemap: false,
    // the charting library (echarts) is one lazy-loaded chunk of ~245 kB gzipped; everything else is small
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender') || id.includes('node_modules/vue-echarts')) return 'charts'
          if (id.includes('node_modules/reka-ui') || id.includes('node_modules/@floating-ui')) return 'ui'
          if (id.includes('node_modules/vue') || id.includes('node_modules/pinia') || id.includes('node_modules/@vueuse')) return 'vue'
          return undefined
        },
      },
    },
  },
  server: {
    port: 5173,
    // dev only: reachable from other machines on the LAN, any Host header
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: false },
      '/metrics': apiTarget,
      '/llms.txt': apiTarget,
      '/mcp': apiTarget,
      '/docs': apiTarget,
      '/openapi.json': apiTarget,
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.test.ts'],
    globals: false,
    css: false,
  },
})
