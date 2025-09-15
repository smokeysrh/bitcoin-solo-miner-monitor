<template>
  <div class="bitcoin-logo-test-page">
    <BitcoinLogoTest />
  </div>
</template>

<script>
import BitcoinLogoTest from '../components/BitcoinLogoTest.vue'

export default {
  name: 'BitcoinLogoTestPage',
  components: {
    BitcoinLogoTest
  }
}
</script>

<style scoped>
.bitcoin-logo-test-page {
  min-height: 100vh;
  background: #1a1a1a;
  color: #fff;
}
</style>