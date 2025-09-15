<template>
  <div class="bitcoin-logo-test">
    <h2>BitcoinLogo Component Test</h2>
    
    <div class="test-section">
      <h3>Size Variants (String Presets)</h3>
      <div class="logo-grid">
        <div class="logo-item">
          <BitcoinLogo size="xs" />
          <span>xs (16px) - SVG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="sm" />
          <span>sm (24px) - SVG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="md" />
          <span>md (32px) - SVG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="lg" />
          <span>lg (48px) - PNG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="xl" />
          <span>xl (64px) - PNG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="hero" />
          <span>hero (96px) - PNG</span>
        </div>
      </div>
    </div>

    <div class="test-section">
      <h3>Custom Numeric Sizes</h3>
      <div class="logo-grid">
        <div class="logo-item">
          <BitcoinLogo :size="20" />
          <span>20px - SVG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo :size="32" />
          <span>32px - SVG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo :size="40" />
          <span>40px - PNG</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo :size="80" />
          <span>80px - PNG</span>
        </div>
      </div>
    </div>

    <div class="test-section">
      <h3>Visual Variants</h3>
      <div class="logo-grid">
        <div class="logo-item">
          <BitcoinLogo size="lg" variant="default" />
          <span>Default</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="lg" variant="glow" />
          <span>Glow</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="lg" variant="subtle" />
          <span>Subtle</span>
        </div>
      </div>
    </div>

    <div class="test-section">
      <h3>Animation Test</h3>
      <div class="logo-grid">
        <div class="logo-item">
          <BitcoinLogo size="lg" :animated="false" />
          <span>Static</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="lg" :animated="true" />
          <span>Animated</span>
        </div>
        <div class="logo-item">
          <BitcoinLogo size="lg" variant="glow" :animated="true" />
          <span>Glow + Animated</span>
        </div>
      </div>
    </div>

    <div class="test-section">
      <h3>Event Testing</h3>
      <div class="logo-grid">
        <div class="logo-item">
          <BitcoinLogo 
            size="lg" 
            @logo-loaded="onLogoLoaded"
            @logo-error="onLogoError"
          />
          <span>Check console for events</span>
        </div>
      </div>
      <div class="event-log">
        <h4>Event Log:</h4>
        <div v-for="event in eventLog" :key="event.id" class="event-item">
          {{ event.message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import BitcoinLogo from './BitcoinLogo.vue'

export default {
  name: 'BitcoinLogoTest',
  components: {
    BitcoinLogo
  },
  setup() {
    const eventLog = ref([])
    let eventId = 0

    const addEvent = (message) => {
      eventLog.value.unshift({
        id: ++eventId,
        message: `${new Date().toLocaleTimeString()}: ${message}`
      })
      // Keep only last 10 events
      if (eventLog.value.length > 10) {
        eventLog.value.pop()
      }
    }

    const onLogoLoaded = (event) => {
      console.log('Logo loaded:', event)
      addEvent(`Logo loaded: ${event.src} (${event.size}px)`)
    }

    const onLogoError = (event) => {
      console.error('Logo error:', event)
      addEvent(`Logo error: ${event.src} (${event.size}px)`)
    }

    return {
      eventLog,
      onLogoLoaded,
      onLogoError
    }
  }
}
</script>

<style scoped>
.bitcoin-logo-test {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.test-section {
  margin-bottom: 40px;
  padding: 20px;
  border: 1px solid #333;
  border-radius: 8px;
  background: #1a1a1a;
}

.test-section h3 {
  color: #F7931A;
  margin-bottom: 20px;
}

.logo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
  align-items: center;
}

.logo-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 15px;
  border: 1px solid #444;
  border-radius: 4px;
  background: #2a2a2a;
}

.logo-item span {
  font-size: 12px;
  color: #ccc;
  text-align: center;
}

.event-log {
  margin-top: 20px;
  padding: 15px;
  background: #0a0a0a;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.event-log h4 {
  color: #F7931A;
  margin-bottom: 10px;
}

.event-item {
  font-family: monospace;
  font-size: 12px;
  color: #ccc;
  padding: 2px 0;
  border-bottom: 1px solid #333;
}

.event-item:last-child {
  border-bottom: none;
}
</style>